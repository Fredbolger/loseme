"""
Client-side preview proxy.

The shared server cannot read files that live on a client device.
This module runs inside the *web client* container and handles:

  GET /preview/{document_part_id}

Workflow:
  1. Fetch document-part metadata from the remote API server
     (source_path, source_type, content_type, extractor_name).
  2. Read the file from the *local* filesystem of this client device.
  3. Extract / render a preview and return it to the browser.

This means file content never travels to the server — only metadata does.
"""
import os
import json
import email
import mailbox
from email.header import decode_header, make_header
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from client.cli.config import API_URL, _build_headers

router = APIRouter(prefix="/preview", tags=["preview"])

# ── Helpers ───────────────────────────────────────────────────

def _get_part_meta(document_part_id: str) -> dict:
    """Fetch document-part record from the remote server."""
    with httpx.Client(base_url=API_URL, headers=_build_headers(), timeout=10.0) as client:
        r = client.get(f"/documents/{document_part_id}")
        r.raise_for_status()
    data = r.json()
    return data.get("document_part") or data


def _decode_header_str(val: Optional[str]) -> str:
    if not val:
        return ""
    return str(make_header(decode_header(val)))


# ── Route ─────────────────────────────────────────────────────

@router.get("/{document_part_id}")
def client_preview(document_part_id: str):
    """
    Client-side preview: read the local file and return a preview payload
    identical in shape to the server's /documents/preview/{id} endpoint.
    """
    meta = _get_part_meta(document_part_id)
    source_type: str = meta.get("source_type", "filesystem")
    source_path: str = meta.get("source_path", "")
    content_type: str = meta.get("content_type", "text/plain")

    # ── Thunderbird ───────────────────────────────────────────
    if source_type == "thunderbird":
        parts = source_path.split("::Message-ID:")
        if len(parts) != 2:
            raise HTTPException(400, f"Cannot parse thunderbird source_path: {source_path}")
        mbox_path, message_id = parts

        if not Path(mbox_path).exists():
            raise HTTPException(
                404,
                f"Mbox file not found on this device: {mbox_path}. "
                "Make sure you are running the web client on the device that owns this file.",
            )

        mbox = mailbox.mbox(mbox_path)
        target = next((m for m in mbox if m.get("Message-ID") == message_id), None)
        if target is None:
            raise HTTPException(404, "Email message not found in local mbox")

        body_html = body_text = None
        if target.is_multipart():
            for part in target.walk():
                ct = part.get_content_type()
                if ct == "text/html" and body_html is None:
                    body_html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                elif ct == "text/plain" and body_text is None:
                    body_text = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
        else:
            payload = target.get_payload(decode=True)
            if payload:
                text = payload.decode(target.get_content_charset() or "utf-8", errors="replace")
                if target.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_text = text

        return {
            "source_type": "thunderbird",
            "preview_type": "email",
            "subject": _decode_header_str(target.get("Subject")),
            "from_": _decode_header_str(target.get("From")),
            "to": _decode_header_str(target.get("To")),
            "date": target.get("Date", ""),
            "body_html": body_html,
            "body_text": body_text,
        }

    # ── Filesystem ────────────────────────────────────────────
    path = Path(source_path)
    if not path.exists():
        raise HTTPException(
            404,
            f"File not found on this device: {source_path}. "
            "Make sure the web client is running on the device that owns this file.",
        )

    suffix = path.suffix.lower()

    # PDF — serve the raw bytes; browser renders inline
    if suffix == ".pdf":
        return FileResponse(str(path), media_type="application/pdf")

    # EML
    if suffix == ".eml":
        raw = path.read_text(encoding="utf-8", errors="ignore")
        msg = email.message_from_string(raw)
        body_html = body_text = None
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html" and body_html is None:
                    body_html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                elif ct == "text/plain" and body_text is None:
                    body_text = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                if msg.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_text = text
        return {
            "source_type": "filesystem",
            "preview_type": "email",
            "subject": _decode_header_str(msg.get("Subject")),
            "from_": _decode_header_str(msg.get("From")),
            "to": _decode_header_str(msg.get("To")),
            "date": msg.get("Date", ""),
            "body_html": body_html,
            "body_text": body_text,
        }

    # Plaintext / code / markdown
    _SUFFIX_TO_LANGUAGE = {
        ".md": "markdown", ".rst": "restructuredtext", ".txt": "plaintext",
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".css": "css", ".html": "html",
    }
    if suffix in _SUFFIX_TO_LANGUAGE:
        return {
            "source_type": "filesystem",
            "preview_type": "plaintext",
            "text": path.read_text(encoding="utf-8", errors="replace"),
            "language": _SUFFIX_TO_LANGUAGE[suffix],
        }

    raise HTTPException(400, f"Preview not supported for {suffix} files on this client.")


# ── Serve raw file (for PDF inline viewer) ────────────────────
@router.get("/serve/{document_part_id}")
def client_serve(document_part_id: str):
    """Serve the raw file bytes — used by the PDF preview iframe."""
    meta = _get_part_meta(document_part_id)
    path = Path(meta.get("source_path", ""))
    if not path.exists():
        raise HTTPException(404, f"File not found on this device: {path}")
    return FileResponse(str(path))
