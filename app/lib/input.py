"""
Input handling and processing for SCLAI.

This module provides functionality for collecting and processing user input,
including command execution, variable substitution, and file inclusion.

The module handles:
- Interactive and non-interactive input
- Variable substitution
- File inclusion
- Input mode detection
- Error handling

Processing order:
1. Escape sequences
2. Variable substitution
3. File inclusion
4. Command processing
"""

import asyncio
import os
import sys
from typing import Final, Optional
from rich.console import Console
from app.lib.parser import BaseTokenParser, VariableResolver, FileResolver
from app.models.dataModel import ParseResult, ProcessResult, InputResult, InputMode
from app.lib.command import command_process
from pfmongo.commands import smash
from pfmongo import pfmongo
from app.lib.log import LOG
import pudb
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import ANSI
from pathlib import Path
import readline


console: Final[Console] = Console()

# Initialize parsers
variable_parser: BaseTokenParser | None = None
file_parser: BaseTokenParser | None = None

HISTORY_FILE: Final[str] = str(Path.home() / ".sclai_history")
HISTORY_LENGTH: Final[int] = 1000


class REPLSession:
    """Manages REPL input session with history support."""

    def __init__(self) -> None:
        try:
            self.history: list[str] = []
            self.session: Optional[PromptSession] = None
            self._setup_readline()
            self._setup_prompt_session()
        except Exception as e:
            print(f"Session init failed: {e}")
            raise

    def _setup_readline(self) -> None:
        """Configure readline with history and key bindings."""
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)

        readline.set_history_length(HISTORY_LENGTH)
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind('"\x1b[A": previous-history')
        readline.parse_and_bind('"\x1b[B": next-history')

    def _setup_prompt_session(self) -> None:
        """Initialize prompt toolkit session."""
        self.session = PromptSession(
            history=FileHistory(HISTORY_FILE),
            enable_history_search=True,
            complete_while_typing=True,
        )

    def save_history(self) -> None:
        """Save current history to file."""
        readline.write_history_file(HISTORY_FILE)


# Global session instance
repl_session: Optional[REPLSession] = None


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
            - continue_loop: Whether to continue processing
            - error: Any error message if input failed
    Note:
        Handles prompt generation and empty input validation
        Uses REPLSession for command history and editing
        Supports:
        - Up/down arrow navigation
        - Command history persistence
        - Empty input handling
        - Interrupt signal handling
    Raises:
        RuntimeError: If session is not initialized
        KeyboardInterrupt: On Ctrl-C
    """
    global repl_session
    try:
        if not repl_session:
            repl_session = REPLSession()

        prompt: str = await smash.prompt_get(pfmongo.options_initialize(), "sclai")
        user_input: str = await repl_session.session.prompt_async(ANSI(f"{prompt} "))
        user_input = user_input.strip()

        if not user_input:
            return InputResult(text="", continue_loop=True)

        repl_session.save_history()
        return InputResult(text=user_input, continue_loop=True)

    except KeyboardInterrupt:
        return InputResult(text="", continue_loop=False, error="Interrupt received")
    except Exception as e:
        return InputResult(text="", continue_loop=False, error=f"Input error: {e}")


# async def input_get() -> InputResult:
#     """Get user input with prompt and history support.
#
#     Returns:
#         InputResult containing:
#             - text: The user input text
#             - continue_loop: Whether to continue processing
#             - error: Any error message if input failed
#
#     Features:
#     - Command history persistence
#     - Arrow key navigation
#     - Empty input handling
#     - Interrupt signal handling
#     """
#     try:
#         prompt: str = await smash.prompt_get(pfmongo.options_initialize(), "sclai")
#         user_input: str = await asyncio.to_thread(input, f"{prompt} ")
#         user_input = user_input.strip()
#
#         if not user_input:
#             return InputResult(text="", continue_loop=True)
#
#         readline.add_history(user_input)
#         readline.write_history_file(HISTORY_FILE)
#
#         return InputResult(text=user_input, continue_loop=True)
#     except KeyboardInterrupt:
#         return InputResult(text="", continue_loop=False, error="Interrupt received")


async def mode_detect(ask_string: str | None = None) -> InputMode:
    """Detect the appropriate input mode.

    Args:
        ask_string: Optional direct query string

    Returns:
        InputMode indicating how to handle input

    Note:
        Priority order:
        1. Stdin content
        2. Ask string
        3. REPL mode
    """
    try:
        if not sys.stdin.isatty():
            return InputMode(has_stdin=True, ask_string=None, use_repl=False)
        if ask_string:
            return InputMode(has_stdin=False, ask_string=ask_string, use_repl=False)
        return InputMode(has_stdin=False, ask_string=None, use_repl=True)

    except Exception as e:
        LOG(f"Error detecting input mode: {e}")
        return InputMode(has_stdin=False, ask_string=None, use_repl=True)


async def input_readStdin() -> str:
    """Read content from stdin.

    Returns:
        Content read from stdin

    Raises:
        IOError: If stdin read fails

    Note:
        Handles both piped and redirected input
    """
    try:
        content: str = sys.stdin.read().strip()
        if not content:
            raise IOError("Empty input from stdin")
        return content
    except Exception as e:
        LOG(f"Error reading from stdin: {e}")
        raise IOError(f"Failed to read from stdin: {e}")


async def input_process(text: str) -> ProcessResult:
    """Process any type of input (commands or content).

    Args:
        text: Raw input text to process

    Returns:
        ProcessResult containing processed result or command status

    Note:
        Processing order:
        1. Initialize parsers
        2. Handle escaped sequences
        3. Process variables/files if not a command
        4. Handle commands if present
    """
    try:
        await parsers_init()

        # Handle escaped sequences first
        if text.startswith("\\"):
            return ProcessResult(text=text[1:], is_command=False, should_exit=False)

        # Process variables and files first
        processed_text: str = text
        if "$" in text or "%" in text:
            # Process variables first
            var_result: ParseResult = await variable_parser.parse(text)
            if not var_result.success:
                return ProcessResult(
                    text="",
                    is_command=False,
                    should_exit=False,
                    error=var_result.error,
                    success=False,
                    exit_code=1,
                )

            processed_text = var_result.text

            # Then process file inclusions
            if "%" in processed_text:
                file_result: ParseResult = await file_parser.parse(processed_text)
                if not file_result.success:
                    return ProcessResult(
                        text="",
                        is_command=False,
                        should_exit=False,
                        error=file_result.error,
                        success=False,
                        exit_code=1,
                    )
                processed_text = file_result.text

        # Check for commands in processed text
        if processed_text.startswith("/"):
            try:
                continue_processing = await command_process(processed_text)
                return ProcessResult(
                    text=processed_text,  # Return processed command text
                    is_command=True,
                    should_exit=not continue_processing,
                    success=True,
                    exit_code=0,
                )
            except Exception as e:
                LOG(f"Command processing error: {e}")
                return ProcessResult(
                    text="",
                    is_command=True,
                    should_exit=True,
                    error=str(e),
                    success=False,
                    exit_code=1,
                )

        # Return processed text for non-command input
        return ProcessResult(
            text=processed_text,
            is_command=False,
            should_exit=False,
            success=True,
            exit_code=0,
        )

    except Exception as e:
        LOG(f"Error processing input: {e}")
        return ProcessResult(
            text="",
            is_command=False,
            should_exit=True,
            error=str(e),
            success=False,
            exit_code=1,
        )


async def input_handle(text: str, non_interactive: bool = False) -> bool:
    """Handle input processing and return whether to continue REPL loop.

    Returns:
        bool: True if REPL should continue, False if should exit
    """
    # pudb.set_trace()
    process_result: ProcessResult = await input_process(text)
    if not process_result.success:
        console.print(f"[bold red]Error: {process_result.error}[/bold red]")
        if non_interactive:
            sys.exit(process_result.exit_code)
        return True  # Continue loop despite errors in interactive mode

    # Handle command output display in non-interactive mode
    if non_interactive and not process_result.is_command and process_result.text:
        console.print(process_result.text)

    should_exit: bool = False
    if process_result.is_command:
        if process_result.should_exit:
            if non_interactive:
                sys.exit(process_result.exit_code)
            console.print("[bold cyan]Exiting.[/bold cyan]")
            should_exit = True
    else:
        if process_result.text:
            console.print(f"[bold yellow]LLM:[/bold yellow] {process_result.text}")

    if non_interactive:
        sys.exit(process_result.exit_code)

    return not should_exit
