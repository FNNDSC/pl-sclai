"""
REPL implementation for SCLAI.

This module provides the REPL (Read-Eval-Print Loop) interface, managing:
- User interaction loop
- Input processing
- Command execution
- Output display
- Error handling
"""

from rich.console import Console
from typing import Final, Optional
from app.lib.input import input_get, input_handle
from app.lib.log import LOG
from app.models.dataModel import InputResult

console: Final[Console] = Console()


async def repl_do() -> None:
    """Main REPL entry point with robust session management.

    Features:
    - Interactive input prompting
    - Command/output separation
    - Graceful error recovery
    - Session persistence until explicit exit

    Flow:
    1. Print welcome banner
    2. Initialize REPL state
    3. Process inputs until exit condition
    4. Clean up resources
    5. Print exit message

    Exits on:
    - /exit command
    - KeyboardInterrupt (Ctrl-C)
    - Critical system errors
    """
    console.print(
        """
        [cyan]Welcome to the SCLAI REPL! 
        [green]Type [white]/exit[green] to quit.
        [green]Use [white]/help[green] for command list.
        """
    )

    continue_repl: bool = True
    while continue_repl:
        try:
            input_result: InputResult = await input_get()

            if not input_result.continue_loop:
                break  # Handle termination signals

            cleaned_input: str = input_result.text.strip()
            if not cleaned_input:
                continue  # Skip empty inputs

            continue_repl = await input_handle(
                text=cleaned_input, non_interactive=False
            )

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Use '/exit' to quit properly[/bold yellow]")
        except Exception as e:
            LOG(f"REPL critical error: {e}")
            console.print(f"[bold red]Fatal error: {e}[/bold red]")
            continue_repl = False

    console.print("[bold cyan]REPL session terminated[/bold cyan]")
