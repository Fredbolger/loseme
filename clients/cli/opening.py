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

def open_path(path: str, os_command: str = None):
    if running_in_docker():
        raise RuntimeError(
            "Cannot open files from Docker. "
            "Run the CLI directly on the host to open documents."
        )
    p = Path(path)

    if not p.exists() and not path.startswith(("http://", "https://")):
        raise FileNotFoundError(path)

    if sys.platform.startswith("linux"):
        subprocess.run([os_command, str(p)], check=False)
        raise SystemExit(0)
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

def open_descriptor(desc: dict):
    source_type = desc["source_type"]

    if source_type == "filesystem":
        target = Path(desc["target"])
        logger.debug(f"Opening filesystem path: {target}")
        open_path(target, os_command=desc.get("os_command"))

    elif source_type == "url":
        open_path(desc["target"], os_command=desc.get("os_command"))

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
        raise SystemExit(0)

    else:
        raise RuntimeError(f"Unknown open descriptor: {source_type}")
