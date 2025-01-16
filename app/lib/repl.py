"""
Defines the REPL for the SCLAI application.

This module provides an interactive REPL (Read-Eval-Print Loop) for managing
commands and simulating LLM responses. Commands are registered using the
Click framework with Rich-enhanced help messages.
"""

from rich.console import Console
import click
import asyncio
import sys
from app.commands.app import cli
from app.models.dataModel import CommandGroup
import shlex
import inspect
import pudb

console: Console = Console()

# Initialize the dynamic command group
dynamic_commands: CommandGroup = CommandGroup(commands={})


async def repl_start() -> None:
    """
    Start the REPL loop, presenting the user with a prompt, accepting input,
    and routing commands or simulating responses from an LLM.

    This function handles user commands and gracefully terminates on <Ctrl-C> or '/exit'.
    """
    console.print(
        "[bold cyan]Welcome to the SCLAI REPL. Type '/exit' to quit.[/bold cyan]\n"
    )

    while True:
        try:
            # Use asyncio.to_thread to handle input asynchronously
            user_input: str = await asyncio.to_thread(input, "$> ")
            user_input = user_input.strip()

            # Handle commands starting with '/'
            if user_input.startswith("/"):
                if not await asyncio.create_task(handle_async_command(user_input)):
                    console.print("[bold cyan]Exiting REPL. Goodbye![/bold cyan]")
                    return
                continue  # Skip the simulated LLM response for valid commands

            # Simulate LLM response
            console.print(
                "[bold yellow]LLM:[/bold yellow] Simulated response (placeholder)."
            )

        except KeyboardInterrupt:
            # Notify the user and terminate the program immediately
            console.print(
                "\n[bold cyan]Interrupt received. Type '/exit' to quit gracefully or hit <Enter> to confirm exit.[/bold cyan]"
            )
            break  # Exit the loop to allow graceful termination

    console.print("[bold cyan]REPL terminated. Goodbye![/bold cyan]")


async def handle_async_command(user_input: str) -> bool:
    """
    Handle commands starting with '/' in an async-safe manner.

    :param user_input: The user input string.
    :return: True if the input was a valid command, False otherwise.
    """
    # Parse user input using shlex to handle quoted strings properly
    try:
        parts = shlex.split(user_input[1:])  # Remove the leading '/' and split input
    except ValueError as e:
        console.print(f"[bold red]Error parsing input: {e}[/bold red]")
        return True

    if not parts:
        console.print("[bold red]Error: No command provided.[/bold red]")
        return True

    command = parts[0]  # First part is the command
    args = parts[1:]  # Remaining parts are arguments

    try:
        if command == "exit":
            return False  # Exit the REPL loop

        if command == "help" or "--help" in args:
            # Handle help commands synchronously
            cli.main(
                args=["--help"] if command == "help" else [command, "--help"],
                prog_name="/",
                standalone_mode=False,
            )
            return True

        # Execute the command asynchronously and wait for completion
        await cli.main(args=[command] + args, prog_name="/", standalone_mode=False)
        return True
    except click.exceptions.UsageError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return True
    except SystemExit:
        return True  # Suppress SystemExit from Click
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        return True
