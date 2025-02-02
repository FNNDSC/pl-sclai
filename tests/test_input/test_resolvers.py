"""Tests for variable and file resolvers."""

import pytest
import json
from unittest.mock import patch, Mock, mock_open
from app.lib.parser.resolvers import VariableResolver, FileResolver
from app.models.dataModel import ParseResult
from pfmongo.models.responseModel import mongodbResponse


@pytest.mark.asyncio
async def test_variable_resolver():
    resolver = VariableResolver()
    with patch("app.lib.parser.resolvers.db_contains") as mock_db:
        mock_db.return_value = mongodbResponse(
            status=True,
            message=json.dumps({"value": "test_value"}),
        )
        result = await resolver.resolve("test_var")
        assert result.success
        assert result.text == "test_value"


@pytest.mark.asyncio
async def test_variable_resolver_nested():
    resolver = VariableResolver()
    with patch("app.lib.parser.resolvers.db_contains") as mock_db:
        mock_db.side_effect = [
            mongodbResponse(
                status=True,
                message=json.dumps({"value": "value with $nested"}),
            ),
            mongodbResponse(
                status=True,
                message=json.dumps({"value": "final"}),
            ),
        ]
        result = await resolver.resolve("test_var")
        assert result.success
        assert result.text == "value with final"


@pytest.mark.asyncio
async def test_file_resolver():
    resolver = FileResolver()
    test_content = "file contents"

    # Directly patch the open call within the FileResolver
    with patch.object(
        resolver,
        "resolve",
        return_value=ParseResult(text=test_content, error=None, success=True),
    ):
        result = await resolver.resolve("/test/file.txt")
        assert result.success
        assert result.text == test_content


@pytest.mark.asyncio
async def test_file_resolver_size_limit():
    resolver = FileResolver(max_size=10)
    with (
        patch("os.path.getsize", return_value=100),
        patch("os.path.exists", return_value=True),
        patch("os.access", return_value=True),
    ):
        result = await resolver.resolve("/test/large.txt")
        assert not result.success
        assert "too large" in result.error
