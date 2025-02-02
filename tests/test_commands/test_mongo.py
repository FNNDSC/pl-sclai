"""Tests for MongoDB command functionality."""

import pytest
import click
from click.testing import CliRunner
from app.commands import mongo


@pytest.fixture
def runner() -> CliRunner:
    """Provide Click test runner."""
    return CliRunner()


def test_mongo_command_group(runner: CliRunner) -> None:
    """Test MongoDB command group structure."""
    assert isinstance(mongo.mongo, click.Group)
    assert "attach" in mongo.mongo.commands

    result = runner.invoke(mongo.mongo, ["--help"])
    assert result.exit_code == 0
    assert "MongoDB Management" in result.output


def test_mongo_attach_success(runner: CliRunner) -> None:
    """Test successful MongoDB attachment."""
    result = runner.invoke(mongo.attach)
    assert result.exit_code == 0
    assert "Attaching to MongoDB" in result.output
