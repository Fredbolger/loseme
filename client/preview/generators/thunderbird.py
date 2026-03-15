from fastapi import HTTPException
from preview.registry import PreviewGenerator, preview_registry
from preview.models import PreviewResult


class ThunderbirdEmailPreviewGenerator(PreviewGenerator):
    name = "thunderbird_email"
    priority = 20

    def can_handle(self, source_type: str, doc_part: dict) -> bool:
        return source_type == "thunderbird"

    def generate(self, doc_part: dict) -> PreviewResult:
        source_path_parts = doc_part["source_path"].split("::Message-ID:")
        mbox_path  = source_path_parts[0]
        message_id = source_path_parts[1]

        from src.sources.base.docker_path_translation import host_path_to_container
        import mailbox
        from email.header import decode_header, make_header

        container_mbox_path = host_path_to_container(mbox_path)
        mbox = mailbox.mbox(str(container_mbox_path))
        mbox._generate_toc()

        target_message = next(
            (msg for msg in mbox if msg.get("Message-ID") == message_id),
            None
        )
        if target_message is None:
            raise HTTPException(404, "Email message not found in mbox")

        def decode_str(val):
            return str(make_header(decode_header(val or "")))

        body_html = body_text = None
        if target_message.is_multipart():
            for part in target_message.walk():
                ct = part.get_content_type()
                if ct == "text/html" and body_html is None:
                    body_html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                elif ct == "text/plain" and body_text is None:
                    body_text = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
        else:
            payload = target_message.get_payload(decode=True)
            if payload:
                text = payload.decode(
                    target_message.get_content_charset() or "utf-8", errors="replace")
                if target_message.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_text = text

        return PreviewResult(
            source_type="thunderbird",
            preview_type="email",
            subject=decode_str(target_message.get("Subject")),
            from_=decode_str(target_message.get("From")),
            to=decode_str(target_message.get("To")),
            date=target_message.get("Date", ""),
            body_html=body_html,
            body_text=body_text,
        )


preview_registry.register(ThunderbirdEmailPreviewGenerator())
