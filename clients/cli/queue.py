import asyncio
import typer 
from datetime import datetime, timezone
import asyncio
from pathlib import Path
import httpx
import json
from typing import List
from src.sources.base.models import DocumentPart, IndexingScope
from src.sources.filesystem import FilesystemIngestionSource, FilesystemIndexingScope
from src.sources.thunderbird import ThunderbirdIngestionSource, ThunderbirdIndexingScope
import logging
logger = logging.getLogger(__name__)

from clients.cli.config import API_URL, BATCH_SIZE


queue_app = typer.Typer(no_args_is_help=True)

@queue_app.command("show_all")
def show_all_queues():
    try:
        response = httpx.get(f"{API_URL}/queue/show_all_queues")
        response.raise_for_status()
        logger.info("Document parts in queue across all run_ids:")
        number_of_parts = response.json().get("total_parts")
        if number_of_parts == 0:
            typer.echo("No document parts in queue across all run_ids")
        else:
            typer.echo(f"{number_of_parts} document parts in queue across all run_ids")
    except Exception as e:
        logger.error(f"Error fetching all queues: {str(e)}")

@queue_app.command("show")
def show_queue(run_id: str):
    try:
        response = httpx.get(f"{API_URL}/queue/show_all/{run_id}")
        response.raise_for_status()
        logger.info(f"Document parts in queue for run_id {run_id}:")
        number_of_parts = response.json().get("total_parts")
        if number_of_parts == 0:
            typer.echo("No document parts in queue for this run_id")
        else:
            typer.echo(f"{number_of_parts} document parts in queue for this run_id")
    except Exception as e:
        logger.error(f"Error fetching queue for run_id {run_id}: {str(e)}")  


@queue_app.command("clear")
def clear_queue(run_id: str):
    try:
        response = httpx.delete(f"{API_URL}/queue/clear/{run_id}")
        response.raise_for_status()
        logger.info(f"Cleared document parts queue for run_id {run_id}")
    except Exception as e:
        logger.error(f"Error clearing queue for run_id {run_id}: {str(e)}")

@queue_app.command("clear_all")
def clear_all_queues():
    try:
        # Ask confirmation before clearing all queues
        confirm = typer.confirm("Are you sure you want to clear all queues for all run_ids? This action cannot be undone.")
        if not confirm:
            logger.info("Aborted clearing all queues")
            return
        response = httpx.delete(f"{API_URL}/queue/clear_all")
        response.raise_for_status()
        logger.info("Cleared document parts queue for all run_ids")
    except Exception as e:
        logger.error(f"Error clearing all queues: {str(e)}")

