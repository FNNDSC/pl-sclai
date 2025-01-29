"""
Token resolvers for SCLAI.

Implements specific resolution strategies for different token types:
- Variables: MongoDB lookup with recursion handling
- Files: File system reads with size limits and safety checks
"""

from typing import Set, Self
import json
import os
from app.lib.mongodb import db_contains
from app.lib.log import LOG
from app.models.dataModel import mongodbResponse, ParseResult


class VariableResolver:
    """Resolver for variable tokens using MongoDB."""

    def __init__(self: Self, max_depth: int = 10) -> None:
        """Initialize resolver with recursion limit."""
        self.max_depth: int = max_depth
        self.current_depth: int = 0
        self.seen_vars: Set[str] = set()

    async def resolve(self: Self, token_value: str) -> ParseResult:
        """Resolve variable from MongoDB.

        Args:
            token_value: Variable name to resolve

        Returns:
            ParseResult containing resolved value or error details
        """
        if self.current_depth >= self.max_depth or token_value in self.seen_vars:
            msg: str = f"Max depth exceeded or circular reference: {token_value}"
            LOG(msg)
            return ParseResult(text="", error=msg, success=False)

        try:
            self.seen_vars.add(token_value)
            self.current_depth += 1

            result: mongodbResponse = await db_contains(token_value)
            if not result.status:
                return ParseResult(
                    text="", error=f"Variable not found: {token_value}", success=False
                )

            try:
                data: dict = json.loads(result.message)
                value: str | None = data.get("value")

                if value is None:
                    msg: str = f"No value found for variable: {token_value}"
                    LOG(msg)
                    return ParseResult(text="", error=msg, success=False)

                if not isinstance(value, str):
                    msg: str = f"Variable {token_value} value is not a string"
                    LOG(msg)
                    return ParseResult(text="", error=msg, success=False)

                # If value contains tokens, recursively resolve them
                if "$" in value:
                    from app.lib.parser import (
                        BaseTokenParser,
                    )  # Import here to avoid circular import

                    parser = BaseTokenParser(token="$", resolver=self)
                    nested_result: ParseResult = await parser.parse(value)
                    if not nested_result.success:
                        return nested_result
                    value = nested_result.text

                return ParseResult(text=value, error=None, success=True)

            except json.JSONDecodeError:
                msg: str = f"Error decoding JSON for variable {token_value}"
                LOG(msg)
                return ParseResult(text="", error=msg, success=False)

        finally:
            self.current_depth -= 1
            self.seen_vars.remove(token_value)


class FileResolver:
    """Resolver for file tokens using filesystem."""

    def __init__(
        self: Self, max_size: int = 1024 * 1024, base_path: str | None = None
    ) -> None:
        """Initialize resolver with size limit and optional base path restriction."""
        self.max_size: int = max_size
        self.base_path: str | None = os.path.abspath(base_path) if base_path else None

    async def resolve(self: Self, token_value: str) -> ParseResult:
        """Read and return file contents."""
        try:
            path: str = os.path.abspath(os.path.expanduser(token_value))

            # Path traversal check
            if self.base_path and not path.startswith(self.base_path):
                msg: str = f"Access denied - path outside base directory: {path}"
                LOG(msg)
                return ParseResult(text="", error=msg, success=False)

            if not os.path.exists(path):
                msg: str = f"File not found: {path}"
                LOG(msg)
                return ParseResult(text="", error=msg, success=False)

            if not os.access(path, os.R_OK):
                msg: str = f"File not readable: {path}"
                LOG(msg)
                return ParseResult(text="", error=msg, success=False)

            size: int = os.path.getsize(path)
            if size > self.max_size:
                msg: str = f"File too large: {path} ({size} bytes)"
                LOG(msg)
                return ParseResult(text="", error=msg, success=False)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content: str = f.read()
                    return ParseResult(text=content, error=None, success=True)
            except UnicodeDecodeError:
                msg: str = f"File is not valid UTF-8: {path}"
                LOG(msg)
                return ParseResult(text="", error=msg, success=False)

        except Exception as e:
            msg: str = f"Error reading file {token_value}: {e}"
            LOG(msg)
            return ParseResult(text="", error=msg, success=False)
