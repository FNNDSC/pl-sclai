"""Tests for LLM command functionality."""

import pytest
import click
from click.testing import CliRunner
from app.commands import llm


@pytest.fixture
def runner() -> CliRunner:
    """Provide Click test runner."""
    return CliRunner()


def test_llm_command_group(runner: CliRunner) -> None:
    """Test LLM command group structure."""
    assert isinstance(llm.llm, click.Group)
    assert "connect" in llm.llm.commands

    result = runner.invoke(llm.llm, ["--help"])
    assert result.exit_code == 0
    assert "LLM Database Management" in result.output


def test_llm_connect_success(runner: CliRunner) -> None:
    """Test successful database connection."""
    result = runner.invoke(llm.connect, ["test_db"])
    assert result.exit_code == 0
    assert "Connecting to database" in result.output


@pytest.mark.parametrize(
    "args,error_message",
    [
        ([], "Missing argument"),
        (["db1", "db2"], "Got unexpected extra argument"),
    ],
)
def test_llm_connect_validation(
    runner: CliRunner, args: list[str], error_message: str
) -> None:
    """Test command argument validation."""
    result = runner.invoke(llm.connect, args)
    assert result.exit_code != 0
    assert error_message in result.output
