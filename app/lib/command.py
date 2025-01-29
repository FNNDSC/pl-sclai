"""
Command processing for SCLAI.

Provides command handling functionality for both interactive and
non-interactive modes. Handles:
- Command parsing
- Command execution
- Help system integration
- Error handling
"""

import shlex
import click
from typing import Final
from rich.console import Console
from app.commands.app import cli
from app.lib.log import LOG

console: Final[Console] = Console()


async def command_process(user_input: str) -> bool:
    """Handle commands starting with '/' in an async-safe manner.

    Args:
        user_input: The user's command input string starting with '/'

    Returns:
        bool: True to continue processing, False to exit

    Raises:
        ValueError: If command parsing fails

    Note:
        Handles special commands:
        - /exit: Terminates processing
        - /help: Shows command help
        Other commands are passed to Click CLI
    """
    try:
        parts: list[str] = shlex.split(user_input[1:])
    except ValueError as e:
        LOG(f"Error parsing command: {e}")
        console.print(f"[bold red]Error parsing input: {e}[/bold red]")
        return True

    if not parts:
        console.print("[bold red]Error: No command provided.[/bold red]")
        return True

    command: str = parts[0]
    args: list[str] = parts[1:]

    try:
        if command == "exit":
            return False

        if command == "help" or "--help" in args:
            full_command: list[str] = [command] + args
            cli.main(
                args=full_command if command != "help" else ["--help"],
                prog_name="/",
                standalone_mode=False,
            )
            return True

        await cli.main(args=[command] + args, prog_name="/", standalone_mode=False)
        return True

    except click.exceptions.UsageError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return True
    except SystemExit:
        return True
    except Exception as e:
        LOG(f"Command processing error: {e}")
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        return True
