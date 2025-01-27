"""
sclai.py

This module serves as the main entry point for the SCLAI plugin, a ChRIS plugin
integrating LangChain for AI-driven text generation.

Features:
- Initializes plugin configuration, including MongoDB and local fallback.
- Provides a command-line interface (CLI) for managing LLM settings.
- Starts an interactive REPL for executing commands and simulating responses.
- Handles graceful termination on user interruption (e.g., <Ctrl-C>).

Usage:
Run this module as a standalone script to start the plugin and REPL.

Example:
    $ ./sclai.py --use OpenAI --key <API_KEY>
"""

from pathlib import Path
from argparse import Namespace, ArgumentParser, ArgumentDefaultsHelpFormatter
from chris_plugin import chris_plugin
from app.config.settings import (
    config_initialize,
    config_update,
    databaseCollection_initialize,
)
from app.lib.repl import repl_start
import asyncio
import signal
from rich.console import Console
from app.lib.log import LOG, app_logger
import sys
from typing import Optional
from types import FrameType
from app.models.dataModel import InitializationResult, DatabaseCollectionModel

__version__: str = "0.1.0"

DISPLAY_TITLE: str = r"""
       _                 _       _
      | |               | |     (_)
 _ __ | |______ ___  ___| | __ _ _
| '_ \| |______/ __|/ __| |/ _` | |
| |_) | |      \__ \ (__| | (_| | |
| .__/|_|      |___/\___|_|\__,_|_|
| |
|_|
"""

console: Console = Console()

# Define the argument parser for the plugin
parser: ArgumentParser = ArgumentParser(
    description="A ChRIS plugin integrating LangChain for AI text generation.",
    formatter_class=ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--use", type=str, help="Specify the LLM to use (e.g., OpenAI, Claude)"
)
parser.add_argument("--key", type=str, help="Specify the API key for the LLM")
parser.add_argument(
    "-V", "--version", action="version", version=f"%(prog)s {__version__}"
)


@chris_plugin(  # type: ignore
    parser=parser,
    title="pl-sclai",
    category="",
    min_memory_limit="200Mi",
    min_cpu_limit="1000m",
    min_gpu_limit=0,
)
def main(options: Namespace, inputdir: Path, outputdir: Path) -> None:
    """
    Main entry point for the ChRIS plugin.

    This function initializes the plugin, processes command-line arguments, and starts the REPL loop.
    It handles configuration updates and ensures graceful termination when interrupted.

    :param options: Parsed command-line options.
    :param inputdir: Directory containing (read-only) input files.
    :param outputdir: Directory where to write output files.
    """
    console.print(DISPLAY_TITLE)

    async def async_main() -> None:
        """
        Asynchronous main function to initialize the REPL and handle configuration updates.

        This function manages plugin setup, processes input arguments, and starts the REPL loop
        if no configuration updates are specified.
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
                return

            # Update configuration if options are provided
            if options.use or options.key:
                try:
                    update_success: bool = await config_update(options.use, options.key)
                    if update_success:
                        console.print(
                            "[bold green]Configuration updated successfully.[/bold green]"
                        )
                    else:
                        console.print(
                            "[bold red]Failed to update configuration.[/bold red]"
                        )
                except ValueError as e:
                    console.print(f"[bold red]Error:[/bold red] {e}")
            else:
                # Start the asynchronous REPL
                await repl_start()

        except Exception as e:
            LOG(f"Unhandled exception in async_main: {e}")
            console.print(
                f"[bold red]An unexpected error occurred: {e}. Exiting.[/bold red]"
            )

    def handle_interrupt(sig: int, frame: Optional[FrameType]) -> None:
        """
        Signal handler for <Ctrl-C>.
        Prevents asyncio.run from intercepting SIGINT and allows the REPL to handle it.

        :param sig: The signal number.
        :param frame: The current stack frame (optional).
        """
        console.print(
            """
            [bold red]Interrupt received. 
            [bold cyan]Hit [bold yellow]Enter[/bold yellow][bold cyan] to gracefully exit.[/bold cyan]
            """
        )
        sys.exit(0)

    # Register the custom signal handler for SIGINT
    signal.signal(signal.SIGINT, handle_interrupt)

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        # Fallback in case an interrupt bypasses the REPL
        console.print("\n[bold cyan]Program interrupted by user. Exiting.[/bold cyan]")
