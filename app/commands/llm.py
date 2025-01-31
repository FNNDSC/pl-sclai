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
from app.commands.base import RichGroup, RichCommand, rich_help  # Added rich_help

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


llm: click.Group = llm


@llm.command(
    cls=RichCommand,
    help=rich_help(
        command="connect",
        description="Connect to a locally managed LLM session database",
        usage="/llm connect <database_name>",
        args={"<database_name>": "Name of MongoDB database containing LLM sessions"},
    ),
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
