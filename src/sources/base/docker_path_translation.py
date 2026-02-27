import os 
from pathlib import Path

LOSEME_HOST_ROOT = os.getenv("LOSEME_HOST_ROOT")
LOSEME_CONTAINER_ROOT = os.getenv("LOSEME_CONTAINER_ROOT")

def host_path_to_container(host_path: str) -> Path:
    """Translate a host absolute path to its container equivalent."""
    if not LOSEME_HOST_ROOT or not LOSEME_CONTAINER_ROOT:
        raise ValueError("LOSEME_HOST_ROOT and LOSEME_CONTAINER_ROOT environment variables must be set")
    
    host_root = Path(LOSEME_HOST_ROOT).resolve()
    container_root = Path(LOSEME_CONTAINER_ROOT).resolve()
    
    host_path = Path(host_path).resolve()
    
    if not host_path.is_absolute():
        raise ValueError(f"Host path must be absolute: {host_path}")
    
    try:
        relative_path = host_path.relative_to(host_root)
    except ValueError:
        raise ValueError(f"Host path {host_path} is not under the configured host root {host_root}")
    
    container_path = container_root / relative_path
    return container_path


def container_path_to_host(container_path: str) -> Path:
    """Translate a container absolute path to its host equivalent."""
    if not LOSEME_HOST_ROOT or not LOSEME_CONTAINER_ROOT:
        raise ValueError("LOSEME_HOST_ROOT and LOSEME_CONTAINER_ROOT environment variables must be set")
    
    host_root = Path(LOSEME_HOST_ROOT).resolve()
    container_root = Path(LOSEME_CONTAINER_ROOT).resolve()
    
    container_path = Path(container_path).resolve()
    
    if not container_path.is_absolute():
        raise ValueError(f"Container path must be absolute: {container_path}")
    
    try:
        relative_path = container_path.relative_to(container_root)
    except ValueError:
        raise ValueError(f"Container path {container_path} is not under the configured container root {container_root}")
    
    host_path = host_root / relative_path
    return host_path
