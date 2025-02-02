"""
Tests for variable management commands.
"""

from typing import Generator, Any, Final
import pytest
import click
from unittest.mock import patch, Mock, AsyncMock
import json
from click.testing import CliRunner
from app.commands import var
from app.models.dataModel import DbInitResult
from pfmongo.models.responseModel import mongodbResponse
from rich.console import Console
import io
import re

ERROR_DB_CONN: Final[str] = "Failed to initialize MongoDB"
ERROR_NOT_FOUND: Final[str] = "Variable '{0}' not found"
SUCCESS_SET: Final[str] = "Variable '{0}' set successfully"
SUCCESS_DELETE: Final[str] = "Variable '{0}' deleted successfully"


@pytest.fixture
def runner() -> CliRunner:
    """Provides a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_db_init() -> Generator[Mock, None, None]:
    """Provides mocked database initialization."""
    with patch("app.commands.var.db_init") as mock:
        mock.return_value = DbInitResult(
            db_response=mongodbResponse(status=True, message="Database initialized"),
            col_response=mongodbResponse(status=True, message="Collection ready"),
        )
        yield mock


@pytest.fixture
def mock_db_response() -> mongodbResponse:
    """Creates a standard success response."""
    return mongodbResponse(
        status=True, message="Operation successful", response={}, exitCode=0
    )


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@pytest.fixture
def captured_output() -> Generator[io.StringIO, None, None]:
    """Captures console output."""
    output = io.StringIO()
    console = Console(file=output)
    with patch("app.commands.var.console", console):
        yield output


def test_var_command_group(runner: CliRunner) -> None:
    """Test the variable command group structure."""
    assert isinstance(var.var, click.Group)
    for cmd in ["set", "show", "showall", "delete"]:
        assert cmd in var.var.commands

    result = runner.invoke(var.var, ["--help"])
    assert result.exit_code == 0
    assert "Variable Management" in result.output


@pytest.mark.parametrize(
    "command,args,error_message",
    [
        ("set", [], "Missing argument"),
        ("set", ["name", "value", "extra"], "Got unexpected extra argument"),
        ("show", [], "Missing argument"),
        ("delete", [], "Missing argument"),
    ],
)
def test_var_argument_validation(
    runner: CliRunner, command: str, args: list[str], error_message: str
) -> None:
    """Test command argument validation."""
    result = runner.invoke(getattr(var, command), args)
    assert result.exit_code != 0
    assert error_message in result.output


@pytest.mark.asyncio
async def test_var_set_success(
    mock_db_init: Mock, mock_db_response: mongodbResponse, captured_output: io.StringIO
) -> None:
    """Test successful variable setting."""
    with patch("app.commands.var.db_docAdd") as mock_add:
        mock_add.return_value = mock_db_response
        await var.set.callback("test_var", "42")
        output = strip_ansi(captured_output.getvalue())
        assert "Variable 'test_var' set successfully" in output
        mock_add.assert_called_once()


@pytest.mark.asyncio
async def test_var_show_success(
    mock_db_init: Mock, captured_output: io.StringIO
) -> None:
    """Test successful variable retrieval."""
    test_var, test_value = "test_var", "42"
    with patch("app.commands.var.db_contains") as mock_contains:
        mock_contains.return_value = mongodbResponse(
            status=True,
            message=json.dumps({"name": test_var, "value": test_value}),
        )
        await var.show.callback(test_var)
        output = strip_ansi(captured_output.getvalue())
        assert f"{test_var}:" in output
        assert test_value in output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        "Variable not found",
        "Database error",
        "Network timeout",
    ],
)
async def test_var_show_errors(
    mock_db_init: Mock, captured_output: io.StringIO, error_message: str
) -> None:
    """Test error conditions during variable retrieval."""
    with patch("app.commands.var.db_contains") as mock_contains:
        mock_contains.return_value = mongodbResponse(
            status=False, message=error_message, exitCode=1
        )
        result = await var.show.callback("nonexistent")
        assert error_message in strip_ansi(captured_output.getvalue())


@pytest.mark.asyncio
async def test_var_showall_success(
    mock_db_init: Mock, captured_output: io.StringIO
) -> None:
    """Test successful variable listing."""
    test_vars = ["var1", "var2", "var3"]
    with patch("app.commands.var.db_showAll") as mock_showall:
        mock_showall.return_value = mongodbResponse(
            status=True,
            message=json.dumps(test_vars),
        )
        await var.showall.callback()
        output = strip_ansi(captured_output.getvalue())
        assert "All variables:" in output
        for var_name in test_vars:
            assert var_name in output


@pytest.mark.asyncio
async def test_var_delete_success(
    mock_db_init: Mock, mock_db_response: mongodbResponse, captured_output: io.StringIO
) -> None:
    """Test successful variable deletion."""
    with patch("app.commands.var.db_docDel") as mock_delete:
        mock_delete.return_value = mock_db_response
        await var.delete.callback("test_var")
        output = strip_ansi(captured_output.getvalue())
        assert "Variable 'test_var' deleted successfully" in output
        mock_delete.assert_called_once()


@pytest.mark.asyncio
async def test_var_connection_failure(captured_output: io.StringIO) -> None:
    """Test database connection failure."""
    with patch("app.commands.var.db_init") as mock_init:
        mock_init.return_value = DbInitResult(
            db_response=mongodbResponse(status=False, message="Connection failed"),
            col_response=mongodbResponse(status=False, message="Collection error"),
        )
        result = await var.set.callback("test_var", "42")
        output = strip_ansi(captured_output.getvalue())
        assert "Failed to initialize" in output


@pytest.mark.asyncio
async def test_var_json_decode_error(
    mock_db_init: Mock, captured_output: io.StringIO
) -> None:
    """Test handling of invalid JSON response."""
    with patch("app.commands.var.db_contains") as mock_contains:
        mock_contains.return_value = mongodbResponse(
            status=True,
            message="invalid{json",
        )
        result = await var.show.callback("test_var")
        output = strip_ansi(captured_output.getvalue())
        assert "Error" in output
