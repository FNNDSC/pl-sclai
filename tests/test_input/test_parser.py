"""Tests for string parser functionality."""

import unittest
import pytest
from unittest.mock import patch, Mock, AsyncMock
from app.lib.parser.base import BaseTokenParser
from app.lib.parser.resolvers import VariableResolver, FileResolver
from app.models.dataModel import ParseResult


@pytest.fixture
def mock_resolver():
    resolver = Mock()
    resolver.resolve = AsyncMock()
    return resolver


@pytest.fixture
def parser(mock_resolver):
    return BaseTokenParser(token="$", resolver=mock_resolver)


@pytest.mark.asyncio
async def test_basic_substitution(parser, mock_resolver):
    mock_resolver.resolve.return_value = ParseResult(
        text="value", error=None, success=True
    )
    result = await parser.parse("Hello $var")
    mock_resolver.resolve.assert_awaited_once_with("var")
    assert result.text == "Hello value"
    assert result.success


@pytest.mark.asyncio
async def test_escaped_token(parser):
    result = await parser.parse(r"Hello \$var")
    assert result.text == "Hello $var"
    assert result.success


@pytest.mark.asyncio
async def test_multiple_substitutions(parser, mock_resolver):
    mock_resolver.resolve.side_effect = [
        ParseResult(text="first", error=None, success=True),
        ParseResult(text="second", error=None, success=True),
    ]
    result = await parser.parse("$var1 and $var2")
    mock_resolver.resolve.assert_has_awaits(
        [unittest.mock.call("var1"), unittest.mock.call("var2")]
    )
    assert result.text == "first and second"
    assert result.success


@pytest.mark.asyncio
async def test_resolver_error(parser, mock_resolver):
    mock_resolver.resolve.return_value = ParseResult(
        text="", error="Resolution failed", success=False
    )
    result = await parser.parse("$var")
    mock_resolver.resolve.assert_awaited_once_with("var")
    assert not result.success
    assert "Resolution failed" in result.error
