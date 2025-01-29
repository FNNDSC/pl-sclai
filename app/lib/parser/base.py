r"""
Base parser implementation for token substitution.

Provides a generic parsing engine that handles token-based string substitution
using configurable resolvers. Supports escaped tokens and custom resolution
strategies.

The parser handles:
- Token-based substitution with configurable token characters
- Escape sequences for literal token characters
- Resolver strategy pattern for different token types
- Error propagation from resolvers
- Nested token resolution

Example:
    parser = BaseTokenParser(token="$", resolver=VariableResolver())
    result = await parser.parse("Value is $var")
"""

from typing import Protocol, runtime_checkable, Self
from app.models.dataModel import ParseResult
from app.lib.log import LOG


@runtime_checkable
class TokenResolver(Protocol):
    """Protocol defining the resolver interface for token substitution.

    Resolvers must implement the resolve method to handle specific token types
    (e.g., variables, files). They should return ParseResult objects containing
    either the resolved value or error details.
    """

    async def resolve(self: Self, token_value: str) -> ParseResult:
        """Resolve a token value to its substitution.

        Args:
            token_value: Raw token value to resolve (without token prefix)

        Returns:
            ParseResult containing:
                - text: Resolved value if successful
                - error: Error message if resolution failed
                - success: Whether resolution succeeded
        """
        ...


class BaseTokenParser:
    """Generic token parser using resolver strategy.

    Handles the parsing of strings containing tokens, using a provided resolver
    to handle the actual token substitution. Supports escaped tokens and
    propagates resolver errors.

    Attributes:
        token: The token prefix character (e.g. "$" or "%")
        resolver: Strategy for resolving token values
        escape_char: Character used for escaping tokens
    """

    def __init__(
        self: Self, token: str, resolver: TokenResolver, escape_char: str = "\\"
    ) -> None:
        """Initialize parser with token configuration.

        Args:
            token: The token prefix character (e.g. "$" or "%")
            resolver: Strategy for resolving token values
            escape_char: Character used for escaping tokens

        Raises:
            ValueError: If token or escape_char is empty
        """
        if not token or not escape_char:
            raise ValueError("Token and escape character cannot be empty")

        self.token: str = token
        self.resolver: TokenResolver = resolver
        self.escape_char: str = escape_char

    async def parse(self: Self, input_text: str) -> ParseResult:
        """Parse input text and process all token substitutions.

        Main entry point for parsing. Handles empty input and delegates to
        token processing methods.

        Args:
            input_text: Raw input string containing tokens

        Returns:
            ParseResult with processed text or error details
        """
        try:
            if not input_text:
                return ParseResult(text="", error=None, success=True)

            return await self._process_tokens(input_text)
        except Exception as e:
            LOG(f"Error in parse: {e}")
            return ParseResult(text="", error=str(e), success=False)

    async def _process_tokens(self: Self, text: str) -> ParseResult:
        """Split on escaped tokens and process substitutions.

        Handles the initial split on escaped sequences and manages the
        processing of individual parts.

        Args:
            text: Text to process for tokens

        Returns:
            ParseResult with processed text or error details
        """
        parts: list[str] = text.split(f"{self.escape_char}{self.token}")
        result: list[str] = []

        for i, part in enumerate(parts):
            if i > 0:  # Parts after escaped token
                result.append(self.token + await self._substitute_tokens(part))
            else:  # First part
                process_result = await self._substitute_tokens(part)
                if isinstance(process_result, ParseResult):
                    return process_result  # Propagate error
                result.append(process_result)

        return ParseResult(text="".join(result), error=None, success=True)

    async def _substitute_tokens(self: Self, text: str) -> str | ParseResult:
        """Process a single token for substitution.

        Handles the actual token detection and resolution, including error
        propagation from resolvers.

        Args:
            text: Text segment to process

        Returns:
            Either:
                - str: Successfully processed text
                - ParseResult: Error details if resolution failed

        Note:
            Returns unmodified text if no tokens found
        """
        if self.token not in text:
            return text

        parts: list[str] = text.split(self.token)
        result: list[str] = [parts[0]]  # First part has no substitution

        for part in parts[1:]:
            token_value: str = ""
            remainder: str = ""

            # Extract token value until non-valid character
            for i, char in enumerate(part):
                if char.isalnum() or char in "_/.-":  # Added chars for paths
                    token_value += char
                else:
                    remainder = part[i:]
                    break
            else:
                token_value = part

            if token_value:
                resolve_result: ParseResult = await self.resolver.resolve(token_value)
                if not resolve_result.success:
                    # Propagate the error instead of falling back
                    return resolve_result
                result.append(resolve_result.text + remainder)
            else:
                result.append(self.token + part)

        return "".join(result)
