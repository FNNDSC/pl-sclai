"""
Base classes for Rich-enhanced Click commands and groups.

This module defines:
- `RichGroup`: A custom Click group with Rich-enhanced help rendering.
- `RichCommand`: A custom Click command with Rich-enhanced help rendering.

These classes provide enhanced formatting and colorized output for CLI commands.
"""

from typing import Optional
from rich.console import Console
import click

console: Console = Console()


class RichGroup(click.Group):
    """
    A Click Group that uses Rich for rendering help messages with enhanced colorization.

    Methods:
        format_help(ctx, formatter): Renders the group-level help message with Rich formatting.
    """

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Render the help message for the group using Rich with enhanced colorization.

        :param ctx: The Click context for the command group.
        :param formatter: The Click help formatter.
        """
        info_name: str = ctx.info_name.lstrip("/") if ctx.info_name else ""
        usage: str = (
            f"[bold yellow]Usage:[/bold yellow] [cyan]/{info_name}[/cyan] [magenta][OPTIONS] COMMAND [ARGS]...[/magenta]\n"
        )
        console.print(usage)

        if self.help:
            console.print(f"[bold cyan]{self.help.strip()}[/bold cyan]\n")

        if self.commands:
            console.print("[bold green]Available Commands:[/bold green]")
            for name, command in self.commands.items():
                console.print(
                    f"- [cyan]{name}[/cyan]: [white]{command.short_help or 'No description available.'}[/white]"
                )
            console.print()

        params = self.get_params(ctx)
        if params:
            console.print("[bold yellow]Options:[/bold yellow]")
            for param in params:
                console.print(
                    f"- [cyan]{param.opts[0]}[/cyan]: {param.help or 'No description'}"
                )


class RichCommand(click.Command):
    """
    A Click Command that uses Rich for rendering help messages with enhanced colorization.

    Methods:
        format_help(ctx, formatter): Renders the command-level help message with Rich formatting.
    """

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Render the help message for the command using Rich with enhanced colorization.

        :param ctx: The Click context for the command.
        :param formatter: The Click help formatter.
        """
        info_name: str = ctx.info_name.lstrip("/") if ctx.info_name else ""
        usage: str = (
            f"[bold yellow]Usage:[/bold yellow] [cyan]/{info_name}[/cyan] [magenta][OPTIONS][/magenta]\n"
        )
        console.print(usage)

        if self.help:
            console.print(f"[bold cyan]{self.help.strip()}[/bold cyan]\n")

        params = self.get_params(ctx)
        if params:
            console.print("[bold yellow]Options:[/bold yellow]")
            for param in params:
                console.print(
                    f"- [cyan]{param.opts[0]}[/cyan]: {param.help or 'No description'}"
                )
