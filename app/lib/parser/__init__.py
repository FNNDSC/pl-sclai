"""
Parser package for SCLAI token substitution.

Provides a modular system for token-based string substitution using
configurable resolvers.
"""

from .base import BaseTokenParser, TokenResolver
from .resolvers import VariableResolver, FileResolver

__all__ = ["BaseTokenParser", "TokenResolver", "VariableResolver", "FileResolver"]
