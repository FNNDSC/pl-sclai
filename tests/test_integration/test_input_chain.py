"""Integration tests for SCLAI functionality."""

import pytest
from unittest.mock import patch, mock_open, AsyncMock
import json
from app.lib.input import input_process, mode_detect, InputMode
from app.lib.parser.resolvers import VariableResolver, FileResolver
from app.models.dataModel import ParseResult, InputMode
from pfmongo.models.responseModel import mongodbResponse


@pytest.mark.asyncio
async def test_variable_substitution_chain():
    with patch(
        "app.lib.parser.resolvers.VariableResolver.resolve", new_callable=AsyncMock
    ) as mock_resolve:
        mock_resolve.return_value = ParseResult(
            text="Hello test_value", error=None, success=True
        )
        result = await input_process("Hello $var")
        assert result.success
        assert "test_value" in result.text
        assert "Hello" in result.text


@pytest.mark.asyncio
async def test_command_processing_chain():
    with patch("app.lib.input.command_process") as mock_cmd:
        mock_cmd.return_value = True
        result = await input_process("/var show test")
        assert result.success
        assert result.is_command


@pytest.mark.asyncio
async def test_complex_input_chain():
    with (
        patch(
            "app.lib.parser.resolvers.VariableResolver.resolve", new_callable=AsyncMock
        ) as mock_variable_resolve,
        patch(
            "app.lib.parser.resolvers.FileResolver.resolve", new_callable=AsyncMock
        ) as mock_file_resolve,
        patch("builtins.open", mock_open(read_data="file content")),
        patch("os.path.exists", return_value=True),
    ):
        mock_variable_resolve.return_value = ParseResult(
            text="value from %file.txt", error=None, success=True
        )
        mock_file_resolve.return_value = ParseResult(
            text="file content", error=None, success=True
        )
        result = await input_process("Test $var")
        assert result.success
        assert "file content" in result.text
        assert "value from" in result.text


@pytest.mark.parametrize(
    "stdin, ask_arg, expected_mode",
    [
        (
            False,
            None,
            InputMode(has_stdin=False, ask_string=None, use_repl=True),
        ),  # REPL mode
        (
            False,
            "test query",
            InputMode(has_stdin=False, ask_string="test query", use_repl=False),
        ),  # Ask string mode
        (
            True,
            None,
            InputMode(has_stdin=True, ask_string=None, use_repl=False),
        ),  # Stdin mode
        (
            True,
            "test query",
            InputMode(has_stdin=True, ask_string=None, use_repl=False),
        ),  # Stdin mode (ask_string ignored)
    ],
)
@pytest.mark.asyncio
async def test_input_mode_detection(stdin, ask_arg, expected_mode):
    with patch("sys.stdin.isatty", return_value=not stdin):
        mode = await mode_detect(ask_arg)
        assert mode == expected_mode
