"""
MongoDB-related commands for SCLAI.

This module defines CLI commands for managing MongoDB connections.

Features:
- Commands to attach to local MongoDB instances.
- Future extensibility for additional MongoDB-related operations.
"""

from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand, rich_help

console: Console = Console()


@click.group(
    cls=RichGroup,
    short_help="Manage local MongoDB interface",
    help="""
    MongoDB Management

    Commands to manage MongoDB connections.
    """,
)
def mongo() -> None:
    """
    The root group for MongoDB-related commands.
    """
    pass


mongo: click.Group = mongo


@mongo.command(
    cls=RichCommand,
    help=rich_help(
        command="attach",
        description="Establish connection to MongoDB instance",
        usage="/mongo attach",
        args={},
    ),
)
def attach() -> None:
    """
    Attach to a local MongoDB instance.

    Simulates connection establishment and displays status.
    """
    console.print("[bold green]Attaching to MongoDB...[/bold green]")
