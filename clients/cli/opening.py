import os
import sys
import subprocess
from pathlib import Path
import os
import re

import logging

logger = logging.getLogger(__name__)
docker_internal_root = Path("/app/data")

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

def open_descriptor(desc: dict):
    source_type = desc["source_type"]

    if source_type == "filesystem":
        target = Path(desc["target"])
        root = desc["extra"]["docker_root_host"]
        relative = target.relative_to(docker_internal_root)
        path = Path(root) / relative
        logger.debug(f"Opening filesystem path: {path}")
        open_path(path)

    elif source_type == "url":
        open_path(desc["target"])

    elif source_type == "thunderbird":
        # extract contents of email message by ID <...> from "INBOX/<...>"
        message_id = re.search(r"<(.*?)>", desc["target"])
        if not message_id:
            raise RuntimeError(f"Invalid Thunderbird message ID: {desc['target']}")

        message_id = message_id.group(1)
        subprocess.run(
                [f"thunderbird" , f"mid:{message_id}"],
                check=False,
        )

    else:
        raise RuntimeError(f"Unknown open descriptor: {source_type}")
