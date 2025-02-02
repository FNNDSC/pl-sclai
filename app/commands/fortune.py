"""
Fortune Teller CLI Commands

This module provides a CLI command for retrieving random fortunes using
the Unix `fortune` command functionality through a Python interface.

Command:
- /fortune tell: Display a random fortune from the system's fortune database
"""

from fortune import fortune as fate
from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand, rich_help
from app.lib.log import LOG

console: Console = Console()


@click.group(
    cls=RichGroup,
    short_help="fortune teller",
    help="""
    fortune 

    Yes. A fortune teller.
    """,
)
def fortune() -> None:
    """
    Root group for variable-related commands.
    """
    pass


fortune: click.Group = fortune


@fortune.command(
    cls=RichCommand,
    help=rich_help(
        command="tell",
        description="Tell a fortune",
        usage="/fortune tell",
        args={"<None>": "no arguments"},
    ),
)
async def tell() -> None:
    """
    Just tell a fortune!
    """
    try:
        tell: str = fate()
        console.print(tell)

    except Exception as e:
        LOG(f"error calling fortune {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")
