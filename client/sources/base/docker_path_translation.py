import os
from pathlib import Path


def is_running_in_docker():
    return os.path.exists("/.dockerenv")


def host_path_to_container(host_path: str) -> Path:
    """Translate a host absolute path to its container equivalent."""
    host_root_env = os.environ.get("LOSEME_HOST_ROOT")
    container_root_env = os.environ.get("LOSEME_CONTAINER_ROOT")
    if not host_root_env or not container_root_env:
        raise ValueError("LOSEME_HOST_ROOT and LOSEME_CONTAINER_ROOT environment variables must be set")

    host_root = Path(host_root_env).resolve()
    container_root = Path(container_root_env).resolve()

    host_path = Path(host_path).resolve()

    if not host_path.is_absolute():
        raise ValueError(f"Host path must be absolute: {host_path}")

    try:
        relative_path = host_path.relative_to(host_root)
    except ValueError:
        raise ValueError(f"Host path {host_path} is not under the configured host root {host_root}")

    return container_root / relative_path


def container_path_to_host(container_path: str) -> Path:
    """Translate a container absolute path to its host equivalent."""
    host_root_env = os.environ.get("LOSEME_HOST_ROOT")
    container_root_env = os.environ.get("LOSEME_CONTAINER_ROOT")
    if not host_root_env or not container_root_env:
        raise ValueError("LOSEME_HOST_ROOT and LOSEME_CONTAINER_ROOT environment variables must be set")

    host_root = Path(host_root_env).resolve()
    container_root = Path(container_root_env).resolve()

    container_path = Path(container_path).resolve()

    if not container_path.is_absolute():
        raise ValueError(f"Container path must be absolute: {container_path}")

    try:
        relative_path = container_path.relative_to(container_root)
    except ValueError:
        raise ValueError(f"Container path {container_path} is not under the configured container root {container_root}")

    return host_root / relative_path
