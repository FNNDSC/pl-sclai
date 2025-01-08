#!/usr/bin/env python

from pathlib import Path
from argparse import Namespace, ArgumentParser, ArgumentDefaultsHelpFormatter
from chris_plugin import chris_plugin
from app.config.settings import config_initialize, config_update
from app.lib.repl import repl_start

__version__: str = '1.1.0'

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

parser: ArgumentParser = ArgumentParser(
    description='A ChRIS plugin integrating LangChain for AI text generation.',
    formatter_class=ArgumentDefaultsHelpFormatter
)
parser.add_argument('--use', type=str, help='Specify the LLM to use (e.g., OpenAI, Claude)')
parser.add_argument('--key', type=str, help='Specify the API key for the LLM')
parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')


@chris_plugin(
    parser=parser,
    title='pl-sclai',
    category='',
    min_memory_limit='200Mi',
    min_cpu_limit='1000m',
    min_gpu_limit=0
)
def main(options: Namespace, inputdir: Path, outputdir: Path) -> None:
    """
    Main entry point for the ChRIS plugin.

    :param options: Parsed command-line options.
    :param inputdir: Directory containing (read-only) input files.
    :param outputdir: Directory where to write output files.
    """
    print(DISPLAY_TITLE)
    config_initialize()

    if options.use or options.key:
        try:
            config_update(options.use, options.key)
            print("Configuration updated successfully.")
        except ValueError as e:
            print(f"Error: {e}")
    else:
        repl_start()  # Call the REPL


if __name__ == "__main__":
    # Avoid interference with the @chris_plugin decorator
    pass

