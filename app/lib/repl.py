"""
Defines the REPL for the SCLAI application.

This module provides an interactive REPL (Read-Eval-Print Loop) that processes
user input through a series of token parsers before passing to the LLM.
It handles:
- Command processing (prefixed with '/')
- Variable substitution (prefixed with '$')
- File inclusion (prefixed with '%')
- LLM interaction

The module supports both interactive and non-interactive modes through
separable input processing functions.
"""

from rich.console import Console
import click
import asyncio
import sys
from app.commands.app import cli
from app.models.dataModel import CommandGroup, ParseResult
from app.lib.parser import BaseTokenParser, VariableResolver, FileResolver
import shlex
from pfmongo.models import fsModel
from pfmongo.config import settings
from pfmongo.commands import smash
from pfmongo import pfmongo
from pydantic import BaseModel


class InputResult(BaseModel):
    """Result of input collection operation.

    Attributes:
        text: The collected input text
        continue_loop: Whether to continue the REPL loop
        error: Optional error message if input collection failed
    """

    text: str
    continue_loop: bool
    error: str | None = None


console: Console = Console()
dynamic_commands: CommandGroup = CommandGroup(commands={})

# Initialize parsers
variable_parser: BaseTokenParser | None = None
file_parser: BaseTokenParser | None = None


async def parsers_init() -> None:
    """Initialize token parsers for variable substitution and file inclusion.

    This function ensures that parsers are initialized only once and
    remain available throughout the session. Creates:
    - Variable parser for $-prefixed substitutions
    - File parser for %-prefixed file inclusions

    Global Variables:
        variable_parser: Parser for handling variable substitutions
        file_parser: Parser for handling file inclusions
    """
    global variable_parser, file_parser

    if variable_parser is None:
        variable_parser = BaseTokenParser(token="$", resolver=VariableResolver())
    if file_parser is None:
        file_parser = BaseTokenParser(token="%", resolver=FileResolver())


async def input_get() -> InputResult:
    """Get user input with prompt.

    Returns:
        InputResult containing:
            - text: The user input text
            - continue_loop: Whether to continue REPL
            - error: Any error message if input failed

    Note:
        Handles prompt generation and empty input validation
    """
    try:
        prompt: str = await smash.prompt_get(pfmongo.options_initialize(), "sclai")
        user_input: str = await asyncio.to_thread(input, f"{prompt} ")
        user_input = user_input.strip()

        if not user_input:
            return InputResult(text="", continue_loop=True)

        return InputResult(text=user_input, continue_loop=True)

    except KeyboardInterrupt:
        return InputResult(text="", continue_loop=False, error="Interrupt received")


async def input_process(text: str) -> ParseResult:
    """Process user input through parsers.

    Args:
        text: Raw input text to process

    Returns:
        ParseResult containing processed text or error

    Note:
        Processes both variables and file inclusions in sequence:
        1. Variable substitution
        2. File inclusion
    """
    try:
        await parsers_init()

        # Process variables first
        var_result: ParseResult = await variable_parser.parse(text)
        if not var_result.success:
            return var_result

        # Then process file inclusions
        file_result: ParseResult = await file_parser.parse(var_result.text)
        return file_result

    except Exception as e:
        return ParseResult(text="", error=str(e), success=False)


async def command_process(user_input: str) -> bool:
    """Handle commands starting with '/' in an async-safe manner.

    Args:
        user_input: The user's command input string starting with '/'

    Returns:
        bool: True to continue REPL, False to exit

    Note:
        Handles special commands:
        - /exit: Terminates REPL
        - /help: Shows command help
        Other commands are passed to Click CLI
    """
    try:
        parts: list[str] = shlex.split(user_input[1:])
    except ValueError as e:
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
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        return True


async def repl_do() -> None:
    """Start the REPL loop.

    Main REPL function that:
    1. Initializes parsers
    2. Processes user input
    3. Handles commands
    4. Manages variable/file substitutions
    5. Interacts with LLM
    6. Handles graceful shutdown

    The loop continues until:
    - User enters '/exit'
    - KeyboardInterrupt received
    - Critical error occurs

    Note:
        Commands are processed before token substitution
        Empty inputs are ignored
    """
    console.print(
        """
        [cyan]Welcome to the SCLAI REPL! 
        [green]Type [white]/exit[green] to quit.
        """
    )

    while True:
        input_result: InputResult = await input_get()
        if not input_result.continue_loop:
            if input_result.error:
                console.print(
                    f"\n[bold cyan]{input_result.error}. Type '/exit' to quit gracefully or hit <Enter> to confirm exit.[/bold cyan]"
                )
            break

        if not input_result.text:
            continue

        if input_result.text.startswith("/"):
            if not await command_process(input_result.text):
                console.print("[bold cyan]Exiting REPL. Goodbye![/bold cyan]")
                return
            continue

        # Parse variables and file includes
        parse_result: ParseResult = await input_process(input_result.text)
        if not parse_result.success:
            console.print(f"[bold red]Parsing error: {parse_result.error}[/bold red]")
            continue

        # Pass parsed text to LLM
        console.print(f"[bold yellow]LLM:[/bold yellow] {parse_result.text}")

    console.print("[bold cyan]REPL terminated. Goodbye![/bold cyan]")
