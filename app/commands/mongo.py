"""
MongoDB-related commands for SCLAI.

This module defines CLI commands for managing MongoDB connections.

Features:
- Commands to attach to local MongoDB instances.
- Future extensibility for additional MongoDB-related operations.
"""

from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand

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


# Explicitly annotate `mongo` as `click.Group` for type checking
mongo: click.Group = mongo


@mongo.command(
    cls=RichCommand,
    short_help="Attach to MongoDB.",
    help="""
    Attach to MongoDB.

    This command establishes a connection to a MongoDB instance,
    allowing you to interact with the database.
    """,
)
def attach() -> None:
    """
    Attach to a local MongoDB instance.

    This command simulates a connection to MongoDB and displays a success message.
    """
    console.print("[bold green]Attaching to MongoDB...[/bold green]")
