"""
Base classes for Rich-enhanced Click commands and groups.

This module defines:
- `RichGroup`: A custom Click group with Rich-enhanced help rendering.
- `RichCommand`: A custom Click command with Rich-enhanced help rendering.

These classes provide enhanced formatting and colorized output for CLI commands,
offering an improved user experience in terminal environments.

Features:
- Displays usage information with colorized output.
- Differentiates between command groups and individual commands.
- Handles exceptions during help rendering gracefully with logging.
"""

from typing import Optional
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
import click
from app.lib.log import LOG

console: Console = Console()


def rich_help(command: str, description: str, usage: str, args: dict) -> str:
    """
    Generate Rich-enhanced help text for commands.

    :param command: The command name.
    :param description: Description of the command.
    :param usage: Usage syntax for the command.
    :param args: Dictionary of arguments and their descriptions.
    :return: Formatted Rich help string.
    """
    help_text = f"[bold cyan]{description}[/bold cyan]\n\n"
    help_text += f"[bold yellow]Usage:[/bold yellow]\n    [green]{usage}[/green]\n\n"
    help_text += "[bold yellow]Arguments:[/bold yellow]\n"
    for arg, desc in args.items():
        help_text += f"    [green]{arg}[/green]: {desc}\n"
    return help_text


class RichGroup(click.Group):
    """
    A Click Group that uses Rich for rendering help messages with enhanced colorization.

    Attributes:
        commands (dict): A dictionary of registered commands within the group.

    Methods:
        format_help(ctx, formatter): Renders the group-level help message with Rich formatting.
    """

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Render the help message for the group using Rich with enhanced colorization.

        :param ctx: The Click context for the command group.
        :param formatter: The Click help formatter.
        """
        try:
            if ctx.invoked_subcommand:
                # Forward to the subcommand if one is invoked
                subcommand = self.get_command(ctx, ctx.invoked_subcommand)
                if subcommand:
                    subcommand.format_help(ctx, formatter)
                    return

            # Render the group-level help
            info_name: str = ctx.info_name.lstrip("/") if ctx.info_name else ""
            usage: str = (
                f"[bold yellow]Usage:[/bold yellow] [cyan]/{info_name}[/cyan] "
                f"[magenta][OPTIONS] COMMAND [ARGS]...[/magenta]\n"
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
        except Exception as e:
            # Log and notify the user of any help rendering errors
            LOG(f"Help rendering error: {e}")
            console.print(f"[bold red]Help rendering error:[/bold red] {e}")


class RichCommand(click.Command):
    """
    A Click Command that uses Rich for rendering help messages.

    Attributes:
        params (list): A list of parameters for the command.

    Methods:
        format_help(ctx, formatter): Renders the command-level help message with Rich formatting.
    """

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Render the help message for the command using Rich.

        :param ctx: The Click context for the command.
        :param formatter: The Click help formatter.
        """
        try:
            help_text = self.help or "No help text available."
            panel_width = max(len(line) for line in help_text.splitlines()) + 10
            panel_width = min(panel_width, 80)  # Cap the width to avoid excessive size
            panel = Panel(
                help_text, expand=False, width=panel_width, border_style="cyan"
            )
            console.print(panel)

            # if self.params:
            #     console.print("\n[bold yellow]Options and Arguments:[/bold yellow]")
            #     for param in self.params:
            #         if isinstance(param, click.Argument):
            #             console.print(
            #                 f"- [cyan]{param.name}[/cyan] ({type(param).__name__}): "
            #                 f"(Argument; no description available)"
            #             )
            #         elif isinstance(param, click.Option):
            #             console.print(
            #                 f"- [cyan]{param.opts[0]}[/cyan] ({type(param).__name__}): "
            #                 f"{param.help or 'No description available.'}"
            #             )
        except Exception as e:
            # Log and notify the user of any help rendering errors
            LOG(f"Help rendering error: {e}")
            console.print(f"[bold red]Help rendering error:[/bold red] {e}")
