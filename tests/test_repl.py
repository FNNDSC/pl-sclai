import subprocess
from unittest.mock import patch, MagicMock
import pytest
from app.lib.repl import fortune_get, repl_start


def test_fortune_get_success(monkeypatch):
    """
    Test fortune_get when the `fortune` command is available.
    """
    mock_output = "This is a fortune."
    monkeypatch.setattr(
        subprocess, 
        "check_output", 
        lambda *args, **kwargs: mock_output
    )
    result = fortune_get()
    assert result == mock_output


def test_fortune_get_failure(monkeypatch):
    """
    Test fortune_get when the `fortune` command is not available.
    """
    def mock_check_output(*args, **kwargs):
        raise FileNotFoundError
    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    result = fortune_get()
    assert result == "Fortune command not found. Please install 'fortune' for simulated responses."


@patch("builtins.input", side_effect=["Hello", "exit"])
@patch("builtins.print")
def test_repl_start_normal(mock_print, mock_input):
    """
    Test repl_start with normal user inputs.
    """
    with patch("app.lib.repl.fortune_get", return_value="Mocked fortune"):
        repl_start()
    # Check input and output calls
    mock_print.assert_any_call("Welcome to the SCLAI REPL. Type 'exit' to quit.\n")
    mock_print.assert_any_call("LLM: Mocked fortune")
    mock_print.assert_any_call("Exiting REPL. Goodbye!")


@patch("builtins.input", side_effect=KeyboardInterrupt)
@patch("builtins.print")
def test_repl_start_ctrl_c(mock_print, mock_input):
    """
    Test repl_start handling <Ctrl+C> (KeyboardInterrupt).
    """
    repl_start()
    mock_print.assert_any_call("\nREPL interrupted. Exiting gracefully. Goodbye!")

