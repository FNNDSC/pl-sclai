from typing import Any
from rich.console import Console
import click

console = Console()


class RichGroup(click.Group):
    """A Click Group that uses Rich for rendering help messages."""

    def format_help(self, ctx, formatter):
        console.print("[bold yellow]SCLAI Command Palette[/bold yellow]\n")
        console.print("[cyan]Manage backend operations with subcommands.[/cyan]\n")

        # List available commands with Rich styling
        if self.commands:
            console.print("\n[bold yellow]Available Commands:[/bold yellow]")
            for name, command in self.commands.items():
                console.print(
                    f"- [cyan]{name}[/cyan]: {command.short_help or 'No description'}"
                )


class RichCommand(click.Command):
    """A Click Command that uses Rich for rendering help messages."""

    def format_help(self, ctx, formatter):
        console.print(self.help)


# Define `cli` using the @click.group decorator
@click.group(
    cls=RichGroup,
    help="""
    SCLAI Command Palette

    Manage backend operations with subcommands.
    """,
)
def cli() -> None:
    pass


# Cast `cli` to Any to resolve linting issues
cli: Any = cli


@cli.group(
    cls=RichGroup,
    help="""
    MongoDB Management

    Commands to manage MongoDB connections.
    """,
)
def mongo() -> None:
    pass


@mongo.command(
    cls=RichCommand,
    short_help="Connect to MongoDB.",
    help="""
    Connect to MongoDB.

    This command establishes a connection to a MongoDB instance, 
    allowing you to interact with the database.
    """,
)
def connect() -> None:
    console.print("[bold green]Connecting to MongoDB...[/bold green]")


def command_handle(user_input: str) -> bool:
    """
    Handle commands starting with '/' using Click and Rich.

    :param user_input: The user input string.
    :return: True if the input was a valid command, False otherwise.
    """
    if not user_input.startswith("/"):
        return False

    parts = user_input[1:].split()  # Split user input into command and arguments
    command = parts[0]  # First part is the command
    args = parts[1:]  # Remaining parts are arguments

    try:
        # Handle `/help` for top-level help
        if command == "help":
            cli.main(args=["--help"], prog_name="REPL", standalone_mode=False)
            return True

        # Pass command and arguments directly to Click
        cli.main(args=[command] + args, prog_name="REPL", standalone_mode=False)
        return True
    except click.exceptions.ClickException as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return True  # Still treat as handled
    except SystemExit:
        return True  # Suppress SystemExit from Click
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        return True


def repl_start() -> None:
    """
    Start the REPL loop, presenting the user with a prompt, accepting input,
    and routing commands or simulating responses from an LLM.
    """
    console.print(
        "[bold cyan]Welcome to the SCLAI REPL. Type 'exit' to quit.[/bold cyan]\n"
    )
    while True:
        try:
            user_input: str = input("$> ").strip()

            # Exit the REPL on 'exit'
            if user_input.lower() == "exit":
                console.print("[bold cyan]Exiting REPL. Goodbye![/bold cyan]")
                break

            # Handle commands starting with '/'
            if user_input.startswith("/") and command_handle(user_input):
                continue

            # Simulate LLM response
            console.print(
                "[bold yellow]LLM:[/bold yellow] Simulated response (placeholder)."
            )
        except KeyboardInterrupt:
            console.print(
                "\n[bold cyan]REPL interrupted. Exiting gracefully. Goodbye![/bold cyan]"
            )
            break
