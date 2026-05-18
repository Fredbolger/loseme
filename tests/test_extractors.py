"""
test_extractors.py — Document extractor unit tests.

Tests run on CPU using temporary files.  No network, no GPU.
Covers: PlainTextExtractor, HTMLExtractor, PDFExtractor (bytes only),
        EMLExtractor, PythonExtractor, ExtractorRegistry.
"""
import textwrap
from pathlib import Path

import pytest


# ===========================================================================
# PlainTextExtractor
# ===========================================================================

class TestPlainTextExtractor:

    @pytest.fixture
    def extractor(self):
        from extractors.plaintext_extractor import PlainTextExtractor
        return PlainTextExtractor()

    def test_can_extract_txt(self, extractor, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world")
        assert extractor.can_extract(f)

    def test_can_extract_md(self, extractor, tmp_path):
        f = tmp_path / "readme.md"
        f.write_text("# title")
        assert extractor.can_extract(f)

    def test_cannot_extract_pdf(self, extractor, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")
        assert not extractor.can_extract(f)

    def test_extract_returns_text(self, extractor, tmp_path):
        f = tmp_path / "test.txt"
        content = "The quick brown fox"
        f.write_text(content)
        result = extractor.extract(f)
        assert content in result.text()

    def test_extract_sets_unit_locator(self, extractor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("some text")
        result = extractor.extract(f)
        assert len(result.unit_locators) == 1
        assert "filesystem:" in result.unit_locators[0]

    def test_extract_content_type_plaintext(self, extractor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        result = extractor.extract(f)
        assert result.content_type() == "text/plain"

    def test_extract_from_bytes(self, extractor):
        result = extractor.extract_from_bytes(b"bytes content")
        assert "bytes content" in result.texts[0]

    def test_can_extract_bytes_valid_utf8(self, extractor):
        assert extractor.can_extract_bytes(b"hello world")

    def test_can_extract_bytes_invalid_utf8(self, extractor):
        assert not extractor.can_extract_bytes(b"\xff\xfe invalid")

    def test_metadata_contains_filename(self, extractor, tmp_path):
        f = tmp_path / "myfile.txt"
        f.write_text("text")
        result = extractor.extract(f)
        assert result.metadata[0]["filename"] == "myfile.txt"

    def test_extractor_name_and_version(self, extractor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("text")
        result = extractor.extract(f)
        assert result.extractor_names[0] == "plaintext"
        assert result.extractor_versions[0] == "0.1"

    def test_is_not_multipart(self, extractor, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("text")
        result = extractor.extract(f)
        assert not result.is_multipart


# ===========================================================================
# HTMLExtractor
# ===========================================================================

class TestHTMLExtractor:

    @pytest.fixture
    def extractor(self):
        from extractors.html_extractor import HTMLExtractor
        return HTMLExtractor()

    def test_can_extract_html(self, extractor, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body>hello</body></html>")
        assert extractor.can_extract(f)

    def test_cannot_extract_txt(self, extractor, tmp_path):
        f = tmp_path / "page.txt"
        f.write_text("plain text")
        assert not extractor.can_extract(f)

    def test_strips_html_tags(self, extractor, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body><h1>Title</h1><p>Body text</p></body></html>")
        result = extractor.extract(f)
        assert "<h1>" not in result.text()
        assert "Title" in result.text()
        assert "Body text" in result.text()

    def test_extract_from_bytes(self, extractor):
        html = b"<html><body><p>Hello bytes</p></body></html>"
        result = extractor.extract_from_bytes(html)
        assert "Hello bytes" in result.texts[0]

    def test_can_extract_bytes_valid_html(self, extractor):
        assert extractor.can_extract_bytes(b"<html>content</html>")

    def test_cannot_extract_bytes_non_html(self, extractor):
        assert not extractor.can_extract_bytes(b"plain text without tags")

    def test_content_type(self, extractor, tmp_path):
        f = tmp_path / "p.html"
        f.write_text("<html><body>hi</body></html>")
        result = extractor.extract(f)
        assert result.content_type() == "text/html"


# ===========================================================================
# PythonExtractor
# ===========================================================================

class TestPythonExtractor:

    @pytest.fixture
    def extractor(self):
        from extractors.python_extractor import PythonExtractor
        return PythonExtractor()

    def test_can_extract_py(self, extractor, tmp_path):
        f = tmp_path / "module.py"
        f.write_text("def hello(): pass")
        assert extractor.can_extract(f)

    def test_cannot_extract_txt(self, extractor, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("text")
        assert not extractor.can_extract(f)

    def test_extracts_source_code(self, extractor, tmp_path):
        code = "def greet(name):\n    return f'Hello {name}'\n"
        f = tmp_path / "greet.py"
        f.write_text(code)
        result = extractor.extract(f)
        assert "def greet" in result.text()

    def test_metadata_num_lines(self, extractor, tmp_path):
        code = "line1\nline2\nline3\n"
        f = tmp_path / "lines.py"
        f.write_text(code)
        result = extractor.extract(f)
        assert result.metadata[0]["num_lines"] == 3

    def test_content_type(self, extractor, tmp_path):
        f = tmp_path / "m.py"
        f.write_text("pass")
        result = extractor.extract(f)
        assert result.content_type() == "text/x-python"


# ===========================================================================
# PDFExtractor (bytes only — avoids needing a real PDF file via pypdf)
# ===========================================================================

class TestPDFExtractorBytes:

    @pytest.fixture
    def extractor(self):
        from extractors.pdf_extractor import PDFExtractor
        return PDFExtractor()

    def test_can_extract_pdf_by_extension(self, extractor, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")
        assert extractor.can_extract(f)

    def test_cannot_extract_txt_by_extension(self, extractor, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("text")
        assert not extractor.can_extract(f)

    def test_can_extract_bytes_pdf_magic(self, extractor):
        assert extractor.can_extract_bytes(b"%PDF-1.4 content here")

    def test_cannot_extract_bytes_non_pdf(self, extractor):
        assert not extractor.can_extract_bytes(b"not a PDF")

    def test_encrypted_pdf_bytes_returns_empty_text(self, extractor):
        """Encrypted PDFs that can't be parsed should return gracefully."""
        # Minimal invalid PDF bytes that will fail parsing → graceful return
        result = extractor.extract_from_bytes(b"%PDF-1.4\n% minimal invalid")
        assert isinstance(result.texts[0], str)


# ===========================================================================
# EMLExtractor
# ===========================================================================

SIMPLE_EML = textwrap.dedent("""\
    From: alice@example.com
    To: bob@example.com
    Subject: Hello
    Date: Mon, 1 Jan 2024 12:00:00 +0000
    Content-Type: text/plain; charset=utf-8

    This is the email body.
""").encode()

MULTIPART_EML = textwrap.dedent("""\
    From: alice@example.com
    To: bob@example.com
    Subject: Multipart
    MIME-Version: 1.0
    Content-Type: multipart/alternative; boundary="bound"

    --bound
    Content-Type: text/plain; charset=utf-8

    Plain text part.
    --bound
    Content-Type: text/html; charset=utf-8

    <html><body><p>HTML part.</p></body></html>
    --bound--
""").encode()


class TestEMLExtractor:

    @pytest.fixture
    def extractor(self):
        # Register dependencies first
        import extractors  # triggers __init__ which registers all extractors
        from extractors.eml_extractor import EMLExtractor
        inst = EMLExtractor()
        from extractors.registry import extractor_registry
        inst.registry = extractor_registry
        return inst

    def test_can_extract_eml(self, extractor, tmp_path):
        f = tmp_path / "msg.eml"
        f.write_bytes(SIMPLE_EML)
        assert extractor.can_extract(f)

    def test_cannot_extract_txt(self, extractor, tmp_path):
        f = tmp_path / "msg.txt"
        f.write_text("text")
        assert not extractor.can_extract(f)

    def test_extract_from_bytes_plain(self, extractor):
        result = extractor.extract_from_bytes(SIMPLE_EML)
        assert any("email body" in t for t in result.texts)

    def test_extract_from_bytes_multipart(self, extractor):
        result = extractor.extract_from_bytes(MULTIPART_EML)
        all_text = " ".join(result.texts)
        assert "Plain text part" in all_text or "HTML part" in all_text

    def test_metadata_has_subject(self, extractor):
        result = extractor.extract_from_bytes(SIMPLE_EML)
        assert any(m.get("subject") == "Hello" for m in result.metadata)

    def test_metadata_has_from(self, extractor):
        result = extractor.extract_from_bytes(SIMPLE_EML)
        assert any("alice@example.com" in (m.get("from") or "") for m in result.metadata)

    def test_unit_locators_set(self, extractor):
        result = extractor.extract_from_bytes(SIMPLE_EML)
        assert len(result.unit_locators) > 0

    def test_file_extract_sets_filesystem_locator(self, extractor, tmp_path):
        f = tmp_path / "msg.eml"
        f.write_bytes(SIMPLE_EML)
        result = extractor.extract(f)
        assert any("filesystem:" in loc for loc in result.unit_locators)


# ===========================================================================
# ExtractorRegistry
# ===========================================================================

class TestExtractorRegistry:

    @pytest.fixture
    def registry(self):
        import extractors  # registers all extractors
        from extractors.registry import extractor_registry
        return extractor_registry

    def test_registry_has_extractors(self, registry):
        assert len(registry.extractors) > 0

    def test_get_extractor_by_name(self, registry):
        ext = registry.get_extractor("plaintext")
        assert ext is not None
        assert ext.name == "plaintext"

    def test_get_unknown_extractor_returns_none(self, registry):
        assert registry.get_extractor("nonexistent") is None

    def test_extract_txt_file(self, registry, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello")
        result = registry.extract(f)
        assert result is not None
        assert "hello" in result.texts[0]

    def test_extract_html_file(self, registry, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body>world</body></html>")
        result = registry.extract(f)
        assert result is not None
        assert "world" in result.texts[0]

    def test_extract_unknown_extension_returns_none(self, registry, tmp_path):
        f = tmp_path / "file.xyz_unknown"
        f.write_bytes(b"binary data")
        result = registry.extract(f)
        assert result is None

    def test_list_extractors(self, registry):
        names = registry.list_extractors()
        assert "plaintext" in names
        assert "html" in names

    def test_priority_order(self, registry):
        """Higher priority extractors come first."""
        priorities = [e.priority for e in registry.extractors]
        assert priorities == sorted(priorities, reverse=True)
