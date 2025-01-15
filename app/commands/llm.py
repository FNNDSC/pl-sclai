"""
LLM-related commands for SCLAI.

This module defines CLI commands for managing connections to locally managed
LLM (Large Language Model) session databases.

Features:
- Commands to connect to specific LLM databases.
- Future extensibility for additional LLM-related operations.
"""

from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand

console: Console = Console()


@click.group(
    cls=RichGroup,
    short_help="Manage local LLM interface",
    help="""
    LLM Database Management

    Commands to manage LLM-specific MongoDB connections.
    """,
)
def llm() -> None:
    """
    The root group for LLM-related commands.
    """
    pass


# Explicitly annotate `llm` as `click.Group` for type checking
llm: click.Group = llm


@llm.command(
    cls=RichCommand,
    short_help="Connect to a locally managed LLM session database.",
    help="""
    Connect to an LLM MongoDB database.

    Usage:
        /llm connect <database_name>
    """,
)
@click.argument("database_name", type=str)
def connect(database_name: str) -> None:
    """
    Connect to a MongoDB database for managing LLM sessions.

    :param database_name: The name of the MongoDB database to connect to.
    """
    console.print(
        f"[bold green]Connecting to database '{database_name}'...[/bold green]"
    )
