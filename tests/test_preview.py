"""
test_preview.py — Preview registry and generator unit tests.

No filesystem reads beyond tmp_path.  No Thunderbird mbox dependency
(Thunderbird generator is tested with a mock).
"""
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# PreviewResult model
# ===========================================================================

class TestPreviewResultModel:

    def test_to_dict_excludes_none(self):
        from server.preview.models import PreviewResult  # server-side model
        result = PreviewResult(
            source_type="filesystem",
            preview_type="plaintext",
            text="hello",
        )
        d = result.to_dict()
        assert "text" in d
        assert "subject" not in d
        assert "body_html" not in d

    def test_to_dict_includes_set_fields(self):
        from server.preview.models import PreviewResult
        result = PreviewResult(
            source_type="thunderbird",
            preview_type="email",
            subject="Test Subject",
            from_="alice@example.com",
            body_text="hello",
        )
        d = result.to_dict()
        assert d["subject"] == "Test Subject"
        assert d["from_"] == "alice@example.com"

    def test_meta_default_empty_dict(self):
        from server.preview.models import PreviewResult
        result = PreviewResult(source_type="fs", preview_type="pt")
        assert result.meta == {}

    def test_client_model_identical_contract(self):
        """Client and server PreviewResult must be structurally identical."""
        from client.preview.models import PreviewResult as ClientResult
        from server.preview.models import PreviewResult as ServerResult
        # Same fields
        client_fields = set(ClientResult.__dataclass_fields__)
        server_fields = set(ServerResult.__dataclass_fields__)
        assert client_fields == server_fields


# ===========================================================================
# PreviewRegistry (server-side)
# ===========================================================================

class TestPreviewRegistry:

    @pytest.fixture
    def registry(self):
        from server.preview.registry import PreviewRegistry
        return PreviewRegistry()

    def test_empty_registry_returns_none(self, registry):
        assert registry.get_generator("filesystem", {}) is None

    def test_register_and_retrieve_generator(self, registry):
        from server.preview.registry import PreviewGenerator

        class DummyGenerator(PreviewGenerator):
            name = "dummy"
            priority = 5

            def can_handle(self, source_type, doc_part):
                return source_type == "dummy_type"

            def generate(self, doc_part):
                pass

        registry.register(DummyGenerator())
        gen = registry.get_generator("dummy_type", {})
        assert gen is not None
        assert gen.name == "dummy"

    def test_higher_priority_wins(self, registry):
        from server.preview.registry import PreviewGenerator

        class LowGen(PreviewGenerator):
            name = "low"
            priority = 1

            def can_handle(self, source_type, doc_part):
                return source_type == "both"

            def generate(self, doc_part):
                pass

        class HighGen(PreviewGenerator):
            name = "high"
            priority = 10

            def can_handle(self, source_type, doc_part):
                return source_type == "both"

            def generate(self, doc_part):
                pass

        registry.register(LowGen())
        registry.register(HighGen())
        gen = registry.get_generator("both", {})
        assert gen.name == "high"

    def test_list_generators(self, registry):
        from server.preview.registry import PreviewGenerator

        class G(PreviewGenerator):
            name = "g_test"
            priority = 0

            def can_handle(self, st, dp):
                return False

            def generate(self, dp):
                pass

        registry.register(G())
        assert "g_test" in registry.list_generators()


# ===========================================================================
# PlaintextPreviewGenerator (server-side)
# ===========================================================================

class TestServerPlaintextPreviewGenerator:

    @pytest.fixture
    def generator(self):
        from server.preview.generators.plaintext import PlaintextPreviewGenerator
        return PlaintextPreviewGenerator()

    def test_can_handle_filesystem_txt(self, generator):
        assert generator.can_handle("filesystem", {"source_path": "/tmp/file.txt"})

    def test_can_handle_filesystem_md(self, generator):
        assert generator.can_handle("filesystem", {"source_path": "/home/user/notes.md"})

    def test_cannot_handle_thunderbird(self, generator):
        assert not generator.can_handle("thunderbird", {"source_path": "/tmp/Inbox"})

    def test_cannot_handle_unsupported_extension(self, generator):
        assert not generator.can_handle("filesystem", {"source_path": "/tmp/file.xyz"})

    def test_generate_reads_file(self, generator, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("preview content")

        with patch(
            "server.preview.generators.plaintext.host_path_to_container",
            return_value=str(f),
        ):
            result = generator.generate({"source_path": str(f)})

        assert result.text == "preview content"
        assert result.preview_type == "plaintext"
        assert result.source_type == "filesystem"

    def test_generate_sets_language(self, generator, tmp_path):
        f = tmp_path / "script.py"
        f.write_text("print('hello')")

        with patch(
            "server.preview.generators.plaintext.host_path_to_container",
            return_value=str(f),
        ):
            result = generator.generate({"source_path": str(f)})

        assert result.language == "python"


# ===========================================================================
# EmlFilePreviewGenerator (server-side)
# ===========================================================================

SIMPLE_EML = textwrap.dedent("""\
    From: alice@example.com
    To: bob@example.com
    Subject: Test email
    Date: Mon, 1 Jan 2024 12:00:00 +0000
    Content-Type: text/plain; charset=utf-8

    Email body text here.
""")


class TestServerEmlPreviewGenerator:

    @pytest.fixture
    def generator(self):
        from server.preview.generators.eml import EmlFilePreviewGenerator
        return EmlFilePreviewGenerator()

    def test_can_handle_eml(self, generator):
        assert generator.can_handle("filesystem", {"source_path": "/tmp/msg.eml"})

    def test_cannot_handle_txt(self, generator):
        assert not generator.can_handle("filesystem", {"source_path": "/tmp/msg.txt"})

    def test_cannot_handle_thunderbird(self, generator):
        assert not generator.can_handle("thunderbird", {"source_path": "/tmp/Inbox"})

    def test_generate_parses_eml(self, generator, tmp_path):
        f = tmp_path / "msg.eml"
        f.write_text(SIMPLE_EML)

        with patch(
            "server.preview.generators.eml.host_path_to_container",
            return_value=str(f),
        ):
            result = generator.generate({"source_path": str(f)})

        assert result.subject == "Test email"
        assert result.from_ == "alice@example.com"
        assert result.to == "bob@example.com"
        assert "Email body text" in (result.body_text or "")

    def test_generate_preview_type_is_email(self, generator, tmp_path):
        f = tmp_path / "msg.eml"
        f.write_text(SIMPLE_EML)

        with patch(
            "server.preview.generators.eml.host_path_to_container",
            return_value=str(f),
        ):
            result = generator.generate({"source_path": str(f)})

        assert result.preview_type == "email"


# ===========================================================================
# Client-side PlaintextPreviewGenerator
# ===========================================================================

class TestClientPlaintextPreviewGenerator:

    @pytest.fixture
    def generator(self):
        from client.preview.generators.plaintext import PlaintextPreviewGenerator
        return PlaintextPreviewGenerator()

    def test_can_handle_txt(self, generator):
        assert generator.can_handle("filesystem", {"source_path": "/tmp/f.txt"})

    def test_cannot_handle_thunderbird(self, generator):
        assert not generator.can_handle("thunderbird", {"source_path": "/tmp/Inbox"})

    def test_generate_reads_file(self, generator, tmp_path):
        f = tmp_path / "note.md"
        f.write_text("# My note\nContent here.")

        with patch(
            "client.preview.generators.plaintext.host_path_to_container",
            return_value=str(f),
        ):
            result = generator.generate({"source_path": str(f)})

        assert "Content here" in result.text
        assert result.language == "markdown"
