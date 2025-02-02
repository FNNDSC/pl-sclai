"""Tests for main SCLAI functionality."""

import pytest
import click
from click.testing import CliRunner
from app.sclai import async_main, main, __version__
from unittest.mock import patch, AsyncMock
from pathlib import Path
from argparse import Namespace
from app.models.dataModel import InputMode
import asyncio


# Define a mock chris_plugin decorator for testing
def mock_chris_plugin(**kwargs):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Replace the actual chris_plugin decorator with the mock during testing
patch("chris_plugin.chris_plugin", mock_chris_plugin).start()


# Create a Click command for testing
@click.command()
@click.option("--use", type=str, help="Specify the LLM to use (e.g., OpenAI, Claude)")
@click.option("--key", type=str, help="Specify the API key for the LLM")
@click.option("--session", type=str, help="Specify chat session ID")
@click.option("--ask", type=str, help="Direct query (alternative to stdin)")
@click.option("-V", "--version", is_flag=True, help="Show version")
def cli(use, key, session, ask, version):
    if version:
        print(f"sclai {__version__}")
        return
    options = Namespace(use=use, key=key, session=session, ask=ask, version=version)
    asyncio.run(async_main(options))


@pytest.fixture
def runner():
    return CliRunner()


def test_version_output(runner):
    result = runner.invoke(cli, ["-V"])
    assert result.exit_code == 0
    assert "sclai" in result.output.lower()  # Check for plugin name
    assert __version__ in result.output  # Check for version number


def test_llm_config(runner):
    with (
        patch("app.sclai.config_setup", new_callable=AsyncMock) as mock_config_setup,
        patch("app.sclai.mode_detect", new_callable=AsyncMock),
        patch("app.sclai.input_handle", new_callable=AsyncMock),
        patch("app.sclai.repl_do", new_callable=AsyncMock),
    ):
        # Mock config_setup to return True
        mock_config_setup.return_value = True
        result = runner.invoke(cli, ["--use", "test_llm", "--key", "test_key"])

        assert result.exit_code == 1
        mock_config_setup.assert_awaited_once()
        assert "Error" not in result.output


@pytest.mark.asyncio
async def test_ask_mode():
    with (
        patch("app.sclai.config_setup", new_callable=AsyncMock) as mock_config_setup,
        patch("app.sclai.mode_detect", new_callable=AsyncMock) as mock_mode_detect,
        patch("app.sclai.input_handle", new_callable=AsyncMock) as mock_input_handle,
    ):
        # Mock config_setup to return True
        mock_config_setup.return_value = True

        # Mock mode_detect to return an InputMode indicating ask_string is present
        mock_mode_detect.return_value = InputMode(
            has_stdin=False, ask_string="test query", use_repl=False
        )

        # Call async_main with appropriate options
        options = Namespace(ask="test query", use=None, key=None, session=None)
        await async_main(options)

        # Assert that input_handle was called correctly
        mock_input_handle.assert_awaited_once_with("test query", non_interactive=True)


def test_invalid_args(runner):
    result = runner.invoke(cli, ["--invalid"])
    assert result.exit_code != 0
    assert "Error" in result.output
