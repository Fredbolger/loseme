"""
test_docker_path_translation.py — Docker path translation utilities.

Tests the host↔container path conversion logic without actually running Docker.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest


# ===========================================================================
# host_path_to_container
# ===========================================================================

class TestHostPathToContainer:

    @pytest.fixture(autouse=True)
    def env(self, monkeypatch):
        monkeypatch.setenv("LOSEME_HOST_ROOT", "/host/data")
        monkeypatch.setenv("LOSEME_CONTAINER_ROOT", "/mnt/data")

    def test_basic_translation(self):
        from sources.base.docker_path_translation import host_path_to_container
        result = host_path_to_container("/host/data/docs/file.txt")
        assert str(result) == "/mnt/data/docs/file.txt"

    def test_nested_path_translated(self):
        from sources.base.docker_path_translation import host_path_to_container
        result = host_path_to_container("/host/data/a/b/c/d.pdf")
        assert str(result) == "/mnt/data/a/b/c/d.pdf"

    def test_root_path_translated(self):
        from sources.base.docker_path_translation import host_path_to_container
        result = host_path_to_container("/host/data")
        assert str(result) == "/mnt/data"

    def test_path_outside_host_root_raises(self):
        from sources.base.docker_path_translation import host_path_to_container
        with pytest.raises(ValueError):
            host_path_to_container("/other/path/file.txt")

    def test_missing_env_vars_raises(self, monkeypatch):
        monkeypatch.delenv("LOSEME_HOST_ROOT", raising=False)
        monkeypatch.delenv("LOSEME_CONTAINER_ROOT", raising=False)
        from importlib import reload
        import sources.base.docker_path_translation as mod
        # Reimport to pick up cleared env
        with pytest.raises(ValueError):
            mod.host_path_to_container("/host/data/file.txt")


# ===========================================================================
# container_path_to_host
# ===========================================================================

class TestContainerPathToHost:

    @pytest.fixture(autouse=True)
    def env(self, monkeypatch):
        monkeypatch.setenv("LOSEME_HOST_ROOT", "/host/data")
        monkeypatch.setenv("LOSEME_CONTAINER_ROOT", "/mnt/data")

    def test_basic_reverse_translation(self):
        from sources.base.docker_path_translation import container_path_to_host
        result = container_path_to_host("/mnt/data/docs/file.txt")
        assert str(result) == "/host/data/docs/file.txt"

    def test_nested_reverse(self):
        from sources.base.docker_path_translation import container_path_to_host
        result = container_path_to_host("/mnt/data/a/b/c.txt")
        assert str(result) == "/host/data/a/b/c.txt"

    def test_path_outside_container_root_raises(self):
        from sources.base.docker_path_translation import container_path_to_host
        with pytest.raises(ValueError):
            container_path_to_host("/other/container/path")

    def test_missing_env_vars_raises(self, monkeypatch):
        monkeypatch.delenv("LOSEME_HOST_ROOT", raising=False)
        monkeypatch.delenv("LOSEME_CONTAINER_ROOT", raising=False)
        from sources.base.docker_path_translation import container_path_to_host
        with pytest.raises(ValueError):
            container_path_to_host("/mnt/data/file.txt")


# ===========================================================================
# Round-trip symmetry
# ===========================================================================

class TestRoundTrip:

    @pytest.fixture(autouse=True)
    def env(self, monkeypatch):
        monkeypatch.setenv("LOSEME_HOST_ROOT", "/host/data")
        monkeypatch.setenv("LOSEME_CONTAINER_ROOT", "/mnt/data")

    def test_host_to_container_to_host(self):
        from sources.base.docker_path_translation import (
            host_path_to_container,
            container_path_to_host,
        )
        original = "/host/data/docs/report.pdf"
        container = host_path_to_container(original)
        restored = container_path_to_host(str(container))
        assert str(restored) == original

    def test_container_to_host_to_container(self):
        from sources.base.docker_path_translation import (
            host_path_to_container,
            container_path_to_host,
        )
        original = "/mnt/data/reports/annual.pdf"
        host = container_path_to_host(original)
        restored = host_path_to_container(str(host))
        assert str(restored) == original


# ===========================================================================
# is_running_in_docker
# ===========================================================================

class TestIsRunningInDocker:

    def test_returns_true_when_dockerenv_exists(self, tmp_path):
        dockerenv = tmp_path / ".dockerenv"
        dockerenv.touch()
        with patch("os.path.exists", lambda p: p == "/.dockerenv"):
            from sources.base.docker_path_translation import is_running_in_docker
            assert is_running_in_docker()

    def test_returns_false_when_dockerenv_missing(self):
        with patch("os.path.exists", return_value=False):
            from sources.base.docker_path_translation import is_running_in_docker
            assert not is_running_in_docker()
