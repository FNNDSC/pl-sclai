r"""
Variable substitution parser for SCLAI.

Handles parsing and substitution of variables in input strings. Variables are
denoted by $ prefix and can contain nested variables. Supports escape sequences
with \$.
"""

from typing import Set
from app.lib.mongodb import db_contains
from app.lib.log import LOG
from app.models.dataModel import ParseResult
import re
import json


class StringParser:
    def __init__(self, max_depth: int = 10):
        """Initialize parser with recursion limit.

        Args:
            max_depth: Maximum recursion depth for nested variables
        """
        self.max_depth = max_depth
        self.current_depth = 0
        self.var_cache = {}
        self.seen_vars: Set[str] = set()

    async def parse(self, input_text: str) -> ParseResult:
        """Parse input string and substitute variables.

        Args:
            input_text: String containing variables to substitute

        Returns:
            ParseResult with substituted text or error
        """
        try:
            self.current_depth = 0
            self.seen_vars.clear()

            variables = self._extract_variables(input_text)
            processed_text = input_text

            for var in variables:
                if var in self.seen_vars:
                    return ParseResult(
                        text="",
                        error=f"Circular reference detected: ${var}",
                        success=False,
                    )

                value = await self._resolve_variable(var)
                if not value:
                    return ParseResult(
                        text="", error=f"Undefined variable: ${var}", success=False
                    )

                processed_text = processed_text.replace(f"${var}", value)

            processed_text = self._handle_escapes(processed_text)
            return ParseResult(text=processed_text, error=None, success=True)

            return ParseResult(text=processed_text, error=None, success=True)

        except Exception as e:
            LOG(f"Error parsing string: {e}")
            return ParseResult(text="", error=str(e), success=False)

    async def _resolve_variable(self, var_name: str) -> str | None:
        """Resolve variable value, handling nested variables.

        Args:
            var_name: Name of variable to resolve

        Returns:
            Resolved value or None if not found
        """
        if self.current_depth >= self.max_depth:
            raise Exception(f"Max recursion depth ({self.max_depth}) exceeded")

        self.seen_vars.add(var_name)
        self.current_depth += 1

        try:
            result = await db_contains(var_name)
            if not result.status:
                return None

            try:
                value = json.loads(result.message).get("value")
                if value and "$" in value:
                    parse_result = await self.parse(value)
                    if not parse_result.success:
                        raise Exception(parse_result.error)
                    value = parse_result.text
                return value
            except json.JSONDecodeError:
                LOG(f"Error decoding JSON for variable {var_name}")
                return None

        finally:
            self.current_depth -= 1
            self.seen_vars.remove(var_name)

    def _extract_variables(self, text: str) -> list[str]:
        """Extract $ prefixed variables from text.

        Args:
            text: Input text to parse

        Returns:
            List of variable names without $ prefix
        """
        pattern = r"(?<!\\)\$([a-zA-Z]\w*)"
        return re.findall(pattern, text)

    def _handle_escapes(self, text: str) -> str:
        """Process escaped $ sequences.

        Args:
            text: Input text with escape sequences

        Returns:
            Text with escapes processed
        """
        return re.sub(r"\\\$", "$", text)
