r"""
Variable substitution parser for SCLAI.

Handles parsing and substitution of variables in input strings. Variables are
denoted by $ prefix and can contain nested variables. Supports escape sequences
with \$.

Implementation uses token-based parsing:
1. Split on escaped sequences first
2. Process variables within each token
3. Handle nested variable substitution recursively

Example:
    Input: "Value is \$100 but $var is $nested"
    Output: "Value is $100 but substituted_value is nested_value"
"""

from typing import Set
from app.lib.mongodb import db_contains
from app.lib.log import LOG
from app.models.dataModel import ParseResult
import json


class StringParser:
    def __init__(self, max_depth: int = 10):
        """Initialize the string parser.

        Args:
            max_depth: Maximum recursion depth for nested variables.
                      Prevents infinite loops in circular references.
        """
        self.max_depth = max_depth
        self.current_depth = 0
        self.seen_vars: Set[str] = set()

    async def parse(self, input_text: str) -> ParseResult:
        """Parse input string and process all variable substitutions.

        Main entry point for string parsing. Handles the complete substitution
        process including escaped sequences and nested variables.

        Args:
            input_text: Raw input string containing variables and escapes

        Returns:
            ParseResult containing:
                - text: Processed string with all substitutions
                - error: Error message if any
                - success: Boolean indicating success/failure
        """
        try:
            self.current_depth = 0
            self.seen_vars.clear()
            return await self._process_tokens(input_text)
        except Exception as e:
            LOG(f"Error parsing string: {e}")
            return ParseResult(text="", error=str(e), success=False)

    async def _process_tokens(self, text: str) -> ParseResult:
        """Process text by splitting on escaped sequences first.

        Splits input on escaped $ sequences, then processes each resulting
        token for variable substitutions.

        Args:
            text: Input text to process

        Returns:
            ParseResult with processed text
        """
        parts = text.split("\\$")
        result = []

        for i, part in enumerate(parts):
            if i > 0:  # Parts after escaped $
                result.append("$" + await self._substitute_vars(part))
            else:  # First part
                result.append(await self._substitute_vars(part))

        return ParseResult(text="".join(result), error=None, success=True)

    async def _substitute_vars(self, text: str) -> str:
        """Substitute variables in a token.

        Processes a single token for variable substitutions. Handles word
        boundaries and maintains unmatched $ literals.

        Args:
            text: Token to process for variables

        Returns:
            Processed string with variables substituted
        """
        if not "$" in text:
            return text

        parts = text.split("$")
        result = [parts[0]]  # First part has no substitution

        for part in parts[1:]:
            var_name = ""
            remainder = ""

            for i, char in enumerate(part):
                if char.isalnum() or char == "_":
                    var_name += char
                else:
                    remainder = part[i:]
                    break

            if var_name:
                value = await self._resolve_variable(var_name)
                if value:
                    result.append(value + remainder)
                else:
                    result.append("$" + var_name + remainder)
            else:
                result.append("$" + part)

        return "".join(result)

    async def _resolve_variable(self, var_name: str) -> str | None:
        """Resolve a variable's value, handling nested variables.

        Queries MongoDB for variable value and handles recursive
        processing of nested variables.

        Args:
            var_name: Name of variable to resolve

        Returns:
            Resolved variable value or None if not found/error
        """
        if self.current_depth >= self.max_depth or var_name in self.seen_vars:
            return None

        try:
            self.seen_vars.add(var_name)
            self.current_depth += 1

            result = await db_contains(var_name)
            if not result.status:
                return None

            try:
                value = json.loads(result.message).get("value")
                if value and "$" in value:
                    parse_result = await self._process_tokens(value)
                    if not parse_result.success:
                        return None
                    value = parse_result.text
                return value
            except json.JSONDecodeError:
                LOG(f"Error decoding JSON for variable {var_name}")
                return None

        finally:
            self.current_depth -= 1
            self.seen_vars.remove(var_name)
