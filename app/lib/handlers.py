"""
Base handler implementations for SCLAI command routing.

This module provides base handler classes for the routing system:
- MongoDB integration through pfmongo
- Standard get/set operations
- Error handling and validation
- Storage location management

Implementation:
    Handlers map commands to MongoDB operations:
    /<command>/<context> -> database/collection/document

Example:
    /openai key -> maps to database="llm", collection="keys", document="openai"
"""

from typing import Any
from app.models.dataModel import RouteHandler
from pfmongo import pfmongo
from pfmongo.commands import smash


class BaseHandler(RouteHandler):
    """Base route handler with MongoDB storage."""

    def __init__(
        self, database: str, collection: str, document: str | None = None
    ) -> None:
        """Initialize handler with storage location.

        Args:
            database: MongoDB database name
            collection: MongoDB collection name
            document: Optional document identifier
        """
        self.database = database
        self.collection = collection
        self.document = document

    async def get(self) -> Any:
        """Get value from MongoDB.

        Returns:
            Stored value

        Raises:
            RuntimeError: If retrieval fails
        """
        try:
            options = pfmongo.options_initialize(
                database=self.database, collection=self.collection
            )
            if self.document:
                options["document"] = self.document
            return await smash.show_get(options)
        except Exception as e:
            raise RuntimeError(f"Failed to get value: {e}")

    async def set(self, value: Any) -> None:
        """Store value in MongoDB.

        Args:
            value: Data to store

        Raises:
            RuntimeError: If storage fails
            ValueError: If value invalid
        """
        if not value:
            raise ValueError("Value cannot be empty")

        try:
            options = pfmongo.options_initialize(
                database=self.database, collection=self.collection
            )
            if self.document:
                options["document"] = self.document
            await smash.show_set(options, value)
        except Exception as e:
            raise RuntimeError(f"Failed to set value: {e}")


class LLMKeyHandler(BaseHandler):
    """Handler for LLM API key management."""

    def __init__(self, provider: str) -> None:
        """Initialize handler for specific LLM provider.

        Args:
            provider: LLM provider name (e.g. 'openai', 'claude')
        """
        super().__init__(database="llm", collection="keys", document=provider)
