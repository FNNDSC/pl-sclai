"""
Tests for input processing functionality.

Tests cover:
- Variable substitution
- File inclusion
- Command processing
- Mode detection
- Input handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from app.lib.input import (
    mode_detect,
    input_process,
    input_handle,
    InputMode,
    ProcessResult,
)
from app.models.dataModel import ParseResult


# Fixtures
@pytest.fixture
def mock_variable_parser():
    parser = AsyncMock()
    parser.parse = AsyncMock()
    return parser


@pytest.fixture
def mock_file_parser():
    parser = AsyncMock()
    parser.parse = AsyncMock()
    return parser


@pytest.fixture
def mock_command_process():
    return AsyncMock()


# Mode Detection Tests
@pytest.mark.asyncio
async def test_mode_detect_stdin(monkeypatch):
    """Test stdin mode detection."""
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: False))
    mode = await mode_detect()
    assert isinstance(mode, InputMode)
    assert mode.has_stdin
    assert not mode.use_repl


@pytest.mark.asyncio
async def test_mode_detect_ask():
    """Test --ask mode detection."""
    mode = await mode_detect(ask_string="test query")
    assert isinstance(mode, InputMode)
    assert not mode.has_stdin
    assert not mode.use_repl
    assert mode.ask_string == "test query"


@pytest.mark.asyncio
async def test_mode_detect_repl():
    """Test REPL mode detection."""
    mode = await mode_detect()
    assert isinstance(mode, InputMode)
    assert not mode.has_stdin
    assert mode.use_repl


# Input Processing Tests
@pytest.mark.asyncio
@patch("app.lib.input.variable_parser")
@patch("app.lib.input.file_parser")
async def test_variable_substitution(mock_var_parser, mock_file_parser):
    """Test variable substitution processing."""
    mock_var_parser.parse.return_value = ParseResult(
        text="Hello World", error=None, success=True
    )

    result = await input_process("Hello $name")
    assert result.success
    assert result.text == "Hello World"
    assert not result.is_command
    mock_var_parser.parse.assert_called_once_with("Hello $name")


@pytest.mark.asyncio
@patch("app.lib.input.variable_parser")
@patch("app.lib.input.file_parser")
async def test_file_inclusion(mock_var_parser, mock_file_parser):
    """Test file inclusion processing."""
    mock_var_parser.parse.return_value = ParseResult(
        text="Read %file.txt", error=None, success=True
    )
    mock_file_parser.parse.return_value = ParseResult(
        text="Read file contents", error=None, success=True
    )

    result = await input_process("Read %file.txt")
    assert result.success
    assert result.text == "Read file contents"
    assert not result.is_command


@pytest.mark.asyncio
@patch("app.lib.input.command_process")
async def test_command_processing(mock_cmd_process):
    """Test command processing."""
    mock_cmd_process.return_value = True  # continue processing

    result = await input_process("/var show test")
    assert result.success
    assert result.is_command
    assert not result.should_exit
    mock_cmd_process.assert_called_once_with("/var show test")


@pytest.mark.asyncio
async def test_escaped_sequence():
    """Test escaped sequence handling."""
    result = await input_process(r"\$not_a_variable")
    assert result.success
    assert result.text == "$not_a_variable"
    assert not result.is_command


@pytest.mark.asyncio
@patch("app.lib.input.variable_parser")
@patch("app.lib.input.file_parser")
async def test_complex_input(mock_var_parser, mock_file_parser):
    """Test complex input with variables and files."""
    mock_var_parser.parse.return_value = ParseResult(
        text="Hello World from %file.txt", error=None, success=True
    )
    mock_file_parser.parse.return_value = ParseResult(
        text="Hello World from file contents", error=None, success=True
    )

    result = await input_process("Hello $name from %file.txt")
    assert result.success
    assert result.text == "Hello World from file contents"
    assert not result.is_command


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in input processing."""
    with patch("app.lib.input.variable_parser") as mock_var_parser:
        mock_var_parser.parse.side_effect = Exception("Test error")

        result = await input_process("$variable")
        assert not result.success
        assert result.error == "Test error"
        assert result.exit_code == 1


# Input Handler Tests
@pytest.mark.asyncio
async def test_input_handle_noninteractive(capsys):
    """Test non-interactive input handling."""
    with patch("app.lib.input.input_process") as mock_process:
        mock_process.return_value = ProcessResult(
            text="Test output",
            is_command=False,
            should_exit=False,
            success=True,
            exit_code=0,
        )

        with pytest.raises(SystemExit) as exit_info:
            await input_handle("test input", non_interactive=True)

        assert exit_info.value.code == 0
        captured = capsys.readouterr()
        assert "Test output" in captured.out
