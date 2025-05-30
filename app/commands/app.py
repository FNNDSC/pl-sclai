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
from app.commands.var import var
from app.commands.fortune import fortune
from app.commands.user import user
from app.commands.context import context

console: Console = Console()


@click.group(
    cls=RichGroup,
    help="""
   SCLAI Command Palette
   Manage backend operations with subcommands.
   """,
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """The root Click command group for SCLAI.

    Args:
        ctx: Click context object for sharing state between commands.
            Initialized with cli group reference for dynamic registration.

    Note:
        Initializes command context and registers core subcommands:
        - mongo: Database operations
        - llm: Language model management
        - var: Variable operations
        - fortune: System information
    """
    ctx.obj = {"cli": cli}


# Explicitly annotate `cli` as `click.Group` for static type checking
cli: click.Group = cli

# Register subcommands
cli.add_command(mongo)
cli.add_command(llm)
cli.add_command(var)
cli.add_command(fortune)
cli.add_command(user)
cli.add_command(context)

# Export the `cli` group for use in other modules
cli_group: click.Group = cli
