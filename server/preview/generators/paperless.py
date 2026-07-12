"""
Paperless-ngx preview generator for Loseme server.

This module provides preview generation for Paperless-ngx documents.
It displays metadata and OCR text content in a structured format.
"""

from preview.registry import PreviewGenerator, preview_registry
from preview.models import PreviewResult


class PaperlessDocumentPreviewGenerator(PreviewGenerator):
    """
    Preview generator for Paperless-ngx documents.
    
    This generates previews that display document metadata and OCR text content.
    """
    name = "paperless_document"
    priority = 25  # Higher priority since paperless is very specific

    def can_handle(self, source_type: str, doc_part: dict) -> bool:
        return source_type == "paperless"

    def generate(self, doc_part: dict) -> PreviewResult:
        """
        Generate a preview for a Paperless document.
        
        The preview includes:
        - Document title and metadata
        - Tags, correspondent, and document type information
        - Full OCR text content
        - URLs for accessing the original document via proxy
        """
        # Extract metadata from the document part
        metadata = doc_part.get("metadata_json", {})
        
        # If metadata is a string (from database), try to parse it
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Extract key fields from metadata
        title = metadata.get("title", "Unknown Document")
        original_filename = metadata.get("original_filename", "")
        paperless_document_id = metadata.get("paperless_document_id", "")
        
        # Fallback: extract paperless_document_id from source_path if not in metadata
        # source_path format is "paperless:{paperless_doc_id}:{title}"
        if not paperless_document_id and doc_part.get("source_path"):
            source_path_parts = doc_part["source_path"].split(":")
            if len(source_path_parts) >= 2:
                paperless_document_id = source_path_parts[1]
        
        # Extract connection_id from scope_json
        connection_id = None
        scope_json = doc_part.get("scope_json")
        if scope_json:
            try:
                import json
                scope = json.loads(scope_json) if isinstance(scope_json, str) else scope_json
                connection_id = scope.get("connection_id")
            except:
                pass
        
        # Extract tags
        tags = metadata.get("tags", [])
        
        # Extract correspondent information
        correspondent = metadata.get("correspondent", "")
        
        # Extract document type information
        document_type = metadata.get("document_type", "")
        
        # Extract timestamps
        created = metadata.get("created", "")
        modified = metadata.get("modified", "")
        added = metadata.get("added", "")
        
        # Extract other metadata
        page_count = metadata.get("page_count", 1)
        content_type = metadata.get("mime_type", "application/octet-stream")
        file_size = metadata.get("file_size", 0)
        
        # Fallback: if content_type is generic, try to detect from file extension
        if content_type == "application/octet-stream" and original_filename:
            import os
            file_ext = os.path.splitext(original_filename)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
                content_type = f"image/{file_ext[1:]}"  # Remove the dot, e.g., '.jpg' -> 'jpg'
            elif file_ext == '.pdf':
                content_type = "application/pdf"
        
        # Get the text content
        text = doc_part.get("text", "")
        
        # Create a structured metadata blob
        meta = {
            "paperless_document_id": paperless_document_id,
            "original_filename": original_filename,
            "title": title,
            "tags": tags,
            "correspondent": correspondent,
            "document_type": document_type,
            "created": created,
            "modified": modified,
            "added": added,
            "page_count": page_count,
            "content_type": content_type,
            "file_size": file_size,
            "source_path": doc_part.get("source_path", ""),
            "document_part_id": doc_part.get("document_part_id", ""),
            "connection_id": connection_id,
        }
        
        # Determine preview type based on content
        if content_type.startswith("image/"):
            preview_type = "paperless_image"
        elif content_type.startswith("application/pdf"):
            preview_type = "paperless_pdf"
        else:
            preview_type = "paperless_document"
        
        return PreviewResult(
            source_type="paperless",
            preview_type=preview_type,
            text=text,
            meta=meta,
            paperless_document_id=paperless_document_id,
            connection_id=connection_id,
        )


# Register the generator
preview_registry.register(PaperlessDocumentPreviewGenerator())