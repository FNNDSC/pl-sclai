"""
SCLAI Plugin Main Module.

This module serves as the main entry point for the SCLAI plugin, a ChRIS plugin
integrating LangChain for AI-driven text generation.

Features:
- Initializes plugin configuration, including MongoDB and local fallback
- Provides a command-line interface (CLI) for managing LLM settings
- Supports multiple input modes: stdin, direct query, and interactive REPL
- Handles graceful termination on user interruption

Usage:
    Run this module as a standalone script to start the plugin and REPL.

Examples:
    Start interactive REPL:
        $ ./sclai.py

    Configure LLM settings:
        $ ./sclai.py --use OpenAI --key <API_KEY>

    Single query mode:
        $ ./sclai.py --ask "What is the capital of France?"
        $ echo "Complex multi-line query" | ./sclai.py
        $ ./sclai.py < query.txt

    Specify chat session:
        $ ./sclai.py --session abc123 --ask "Continue from previous chat"
        $ cat complex_prompt.txt | ./sclai.py --session abc123

Note:
    Input priority order:
    1. stdin (if available)
    2. --ask argument (if provided)
    3. interactive REPL (default)
"""

from pathlib import Path
from argparse import Namespace, ArgumentParser, ArgumentDefaultsHelpFormatter
from chris_plugin import chris_plugin
from app.config.settings import (
    config_initialize,
    config_update,
    databaseCollection_initialize,
)
from app.lib.repl import repl_do
from app.lib.input import mode_detect, input_readStdin, input_handle, InputMode
from app.models.dataModel import InitializationResult, DatabaseCollectionModel
import asyncio
import signal
from rich.console import Console
from app.lib.log import LOG
import sys
from typing import Final, Optional
from types import FrameType
import pudb

__version__: Final[str] = "0.1.0"

DISPLAY_TITLE: Final[
    str
] = """
█▀ █▀▀ █   ▄▀█ █ 
▄█ █▄▄ █▄▄ █▀█ █ 
"""

console: Final[Console] = Console()

# Define the argument parser for the plugin
parser: Final[ArgumentParser] = ArgumentParser(
    description="A ChRIS plugin integrating LangChain for AI text generation.",
    formatter_class=ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--use", type=str, help="Specify the LLM to use (e.g., OpenAI, Claude)"
)
parser.add_argument("--key", type=str, help="Specify the API key for the LLM")
parser.add_argument("--session", type=str, help="Specify chat session ID")
parser.add_argument("--ask", type=str, help="Direct query (alternative to stdin)")
parser.add_argument(
    "-V", "--version", action="version", version=f"%(prog)s {__version__}"
)


async def config_setup(options: Namespace) -> bool:
    """Initialize and update configuration.

    Args:
        options: Parsed command-line arguments

    Returns:
        bool: True if configuration successful

    Note:
        Initializes databases and handles config updates
    """
    try:
        # Initialize configuration
        result: InitializationResult = await config_initialize()

        result = await databaseCollection_initialize(
            DatabaseCollectionModel(database="claimm", collection="vars"),
        )
        result = await databaseCollection_initialize(
            DatabaseCollectionModel(database="claimm", collection="crawl"),
        )

        if not result.status:
            console.print(
                f"[bold red]Configuration initialization failed: {result.message}[/bold red]"
            )
            return False

        # Update configuration if options provided
        if options.use or options.key:
            try:
                if await config_update(options.use, options.key):
                    console.print(
                        "[bold green]Configuration updated successfully.[/bold green]"
                    )
                else:
                    console.print(
                        "[bold red]Failed to update configuration.[/bold red]"
                    )
                    return False
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                return False

        return True

    except Exception as e:
        LOG(f"Configuration setup failed: {e}")
        return False


async def async_main(options: Namespace) -> None:
    """Asynchronous main function handling all input modes.

    Args:
        options: Parsed command-line arguments

    Note:
        Handles three input modes in priority order:
        1. stdin content
        2. --ask argument
        3. interactive REPL
    """
    try:
        if not await config_setup(options):
            return

        # Detect input mode
        mode: InputMode = await mode_detect(options.ask)

        # Process based on mode
        if mode.has_stdin:
            input_text: str = await input_readStdin()
            await input_handle(input_text, non_interactive=True)

        elif mode.ask_string:
            # pudb.set_trace()
            await input_handle(mode.ask_string, non_interactive=True)

        else:
            console.print(DISPLAY_TITLE)
            await repl_do()

    except Exception as e:
        LOG(f"Unhandled exception in async_main: {e}")
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        sys.exit(1)


def signal_handle(sig: int, frame: Optional[FrameType]) -> None:
    """Signal handler for graceful interruption.

    Args:
        sig: Signal number
        frame: Current stack frame

    Note:
        Prevents asyncio.run from intercepting SIGINT
        Allows for graceful shutdown on Ctrl-C
    """
    console.print(
        """
        [bold red]Interrupt received. 
        [bold cyan]Hit [bold yellow]Enter[/bold yellow][bold cyan] to gracefully exit.[/bold cyan]
        """
    )
    sys.exit(0)


@chris_plugin(
    parser=parser,
    title="pl-sclai",
    category="",
    min_memory_limit="200Mi",
    min_cpu_limit="1000m",
    min_gpu_limit=0,
)
def main(options: Namespace, inputdir: Path, outputdir: Path) -> None:
    """Main entry point for the ChRIS plugin.

    Args:
        options: Parsed command-line options
        inputdir: Directory containing input files
        outputdir: Directory for output files

    Note:
        Initializes plugin, processes args, and handles input modes
        Manages async operation and signal handling
    """

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handle)

    try:
        asyncio.run(async_main(options))
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Program interrupted by user. Exiting.[/bold cyan]")
