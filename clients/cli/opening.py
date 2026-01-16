import os
import sys
import subprocess
from pathlib import Path
import os

def running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")

def open_path(path: str):
    if running_in_docker():
        raise RuntimeError(
            "Cannot open files from Docker. "
            "Run the CLI directly on the host to open documents."
        )
    p = Path(path)

    if not p.exists() and not path.startswith(("http://", "https://")):
        raise FileNotFoundError(path)

    if sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", path], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform.startswith("win"):
        os.startfile(path)
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

