import asyncio
import os
from pathlib import Path
from typing import List
import httpx
import typer
from src.sources.base.models import IndexingScope
from src.sources.filesystem import FilesystemIndexingScope
from src.sources.thunderbird import ThunderbirdIndexingScope
from clients.cli.config import API_URL
import logging
logger = logging.getLogger(__name__)

sources_app = typer.Typer(no_args_is_help=True, help="Manage monitored sources.")
sources_add_app = typer.Typer(no_args_is_help=True, help="Add monitored sources.")
sources_app.add_typer(sources_add_app, name="add")

def is_mbox_file(path: Path) -> bool:
    """
    Simple heuristic to check if a file is an mbox file.
    Checks if the file starts with "From " which is common for mbox files.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
            return first_line.startswith("From ")
    except Exception as e:
        logger.error(f"Error checking if file {path} is an mbox file: {e}")
        return False

@sources_add_app.command("thunderbird")
def add_thunderbird_source(
    mbox: str = typer.Argument(..., help="Path to Thunderbird mailbox"),
    ignore_from: List[str] = typer.Option([], "--ignore-from"),
):
    """
    Add a Thunderbird mailbox as a monitored source.
    """

    # if the provided path is a directory, look for mbox files inside it and recursively add them as sources
    if Path(mbox).is_dir():
        logger.info(f"Provided path {mbox} is a directory, looking for mbox files inside it.")
        for root, dirs, files in os.walk(mbox):
            for file in files:
                file_path = Path(root) / file
                if is_mbox_file(file_path):
                    logger.info(f"Found mbox file: {file_path}, adding as monitored source.")
                    add_thunderbird_source(mbox=str(file_path), ignore_from=ignore_from)
        return

    mbox = str(mbox)
    logger.info(f"Adding Thunderbird monitored source for {mbox}")

    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=mbox,
        ignore_patterns=[{"field": "from", "value": v} for v in ignore_from],
    )

    response = httpx.post(
        f"{API_URL}/sources/add",
        json={
            "source_type": "thunderbird",
            "scope": scope.serialize(),
        },
    )
    response.raise_for_status()

    source_id = response.json().get("source_id")
    typer.echo(f"Added Thunderbird monitored source with ID: {source_id}")

@sources_add_app.command("filesystem")
def add_filesystem_source(
    path: Path = typer.Argument(..., exists=True, file_okay=False),
    recursive: bool = True,
):
    """
    Add a local filesystem directory as a monitored source.
    """

    logger.info(f"Adding Filesystem monitored source for {path}")

    scope = FilesystemIndexingScope(
        directories=[path],
        recursive=recursive,
        include_patterns=[],
        exclude_patterns=[],
    )

    response = httpx.post(
        f"{API_URL}/sources/add",
        json={
            "source_type": "filesystem",
            "scope": scope.serialize(),
        },
    )
    response.raise_for_status()

    source_id = response.json().get("source_id")
    typer.echo(f"Added Filesystem monitored source with ID: {source_id}")

@sources_app.command("list")
def list_monitored_sources():
    r = httpx.get(f"{API_URL}/sources/get_all_sources")
    r.raise_for_status()

    pretty_text = ""
    for source in r.json()["sources"]:
        pretty_text += "-" * 40 + "\n"
        pretty_text += f"ID: {source['id']}\n"
        pretty_text += f"Type: {source['source_type']}\n"
        pretty_text += f"Locator: {source['locator']}\n"
        for key, value in source['scope'].items():
            pretty_text += f"  {key}: {value}\n"
        pretty_text += f"Enabled: {source['enabled']}\n"
        pretty_text += f"Created At: {source['created_at']}\n"
        pretty_text += "-" * 40 + "\n"

    typer.echo(pretty_text)

@sources_app.command("scan")
def scan_sources():
    asyncio.run(scan_monitored_sources())

async def scan_monitored_sources():
    from clients.cli.ingest import ingest_filesystem, ingest_thunderbird
    sources = httpx.get(f"{API_URL}/sources/get_all_sources") 
    sources.raise_for_status()

    logger.info("Starting scan of monitored sources.")
    for source in sources.json().get("sources", []):
        source_id = source.get("id")
        scope = IndexingScope.deserialize(source.get("scope"))
        
        if source.get("source_type") == "filesystem":
            for directory in scope.directories:
                logger.info(f"Scanning filesystem source ID {source_id} at {directory}")
                await ingest_filesystem(path=Path(directory), recursive=True)
        elif source.get("source_type") == "thunderbird":
            logger.info(f"Scanning Thunderbird source ID {source_id} at {scope.mbox_path}")
            await ingest_thunderbird(mbox=scope.mbox_path, ignore_from=[p["value"] for p in scope.ignore_patterns if p["field"] == "from"])
        else:
            logger.warning(f"Unknown source type {source.get('source_type')} for source ID {source_id}, skipping.")


