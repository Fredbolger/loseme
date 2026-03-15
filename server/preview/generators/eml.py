import email as emaillib
from pathlib import Path
from email.header import decode_header, make_header
from src.sources.base.docker_path_translation import host_path_to_container
from preview.registry import PreviewGenerator, preview_registry
from preview.models import PreviewResult


class EmlFilePreviewGenerator(PreviewGenerator):
    name = "eml_file"
    priority = 15   # above plaintext, below thunderbird

    def can_handle(self, source_type: str, doc_part: dict) -> bool:
        if source_type != "filesystem":
            return False
        return Path(doc_part.get("source_path", "")).suffix.lower() == ".eml"

    def generate(self, doc_part: dict) -> PreviewResult:
        path = Path(host_path_to_container(doc_part["source_path"]))
        msg = emaillib.message_from_bytes(path.read_bytes())

        def decode_str(val):
            return str(make_header(decode_header(val or "")))

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

        return PreviewResult(
            source_type="filesystem",
            preview_type="email",
            subject=decode_str(msg.get("Subject")),
            from_=decode_str(msg.get("From")),
            to=decode_str(msg.get("To")),
            date=msg.get("Date", ""),
            body_html=body_html,
            body_text=body_text,
        )


preview_registry.register(EmlFilePreviewGenerator())
