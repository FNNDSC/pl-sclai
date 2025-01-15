"""
Defines the main Click command group for the SCLAI application.

This module provides:
- The root `cli` command group for the application.
- Integration with Rich-enhanced Click classes (`RichGroup`).
- Registration of subcommands from other modules.

Usage:
Import `cli` to initialize and run the command-line interface.
"""

from rich.console import Console
import click
from app.commands.base import RichGroup
from app.commands.mongo import mongo
from app.commands.llm import llm

console: Console = Console()


@click.group(
    cls=RichGroup,
    help="""
    SCLAI Command Palette

    Manage backend operations with subcommands.
    """,
)
def cli() -> None:
    """
    The root Click command group for SCLAI.
    """
    pass


# Explicitly annotate `cli` as `click.Group` for static type checking
cli: click.Group = cli

# Register subcommands
cli.add_command(mongo)
cli.add_command(llm)

# Export the `cli` group for use in other modules
cli_group: click.Group = cli
