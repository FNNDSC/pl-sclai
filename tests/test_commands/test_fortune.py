"""Tests for fortune command functionality."""

import pytest
from unittest.mock import patch
import io
from rich.console import Console
from app.commands import fortune


@pytest.fixture
def captured_output() -> io.StringIO:
    """Capture console output."""
    output = io.StringIO()
    console = Console(file=output)
    with patch("app.commands.fortune.console", console):
        yield output


@pytest.mark.asyncio
async def test_fortune_tell_success(captured_output: io.StringIO) -> None:
    """Test fortune telling command."""
    test_fortune = "Test fortune message"
    with patch("app.commands.fortune.fate", return_value=test_fortune):
        await fortune.tell.callback()
        assert test_fortune in captured_output.getvalue()


@pytest.mark.asyncio
async def test_fortune_error(captured_output: io.StringIO) -> None:
    """Test fortune error handling."""
    with patch("app.commands.fortune.fate", side_effect=Exception("Fortune error")):
        await fortune.tell.callback()
        assert "Error" in captured_output.getvalue()
