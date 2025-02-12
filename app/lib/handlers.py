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
from typing_extensions import Doc
from app.models.dataModel import (
    DocumentData,
    RouteHandler,
    DatabaseCollectionModel,
    DbInitResult,
)
from app.lib.mongodb import db_contains, db_init, db_docAdd
from app.models.dataModel import Trait
from pfmongo.models.responseModel import mongodbResponse
import json


class BaseHandler(RouteHandler):
    """Base route handler with MongoDB storage."""

    def __init__(
        self, database: str, collection: str, document: Trait | None = None
    ) -> None:
        """Initialize handler with storage location.

        Args:
            database: MongoDB database name
            collection: MongoDB collection name
            document: Optional document identifier
        """
        self.database = database
        self.collection = collection
        if document:
            self.document = document.value
        else:
            self.document = None

    async def connect(self) -> DbInitResult | None:
        db_connect: DbInitResult = await db_init(
            DatabaseCollectionModel(database=self.database, collection=self.collection)
        )
        if not db_connect.db_response.status or not db_connect.col_response.status:
            return None
        return db_connect

    async def get(self) -> str | None:
        """Get value from MongoDB.

        Returns:
            Stored value or None
        """
        db_connect: DbInitResult | None = await self.connect()
        if not db_connect:
            return None
        if not self.document:
            return None
        result: mongodbResponse = await db_contains(self.document)
        message_data = json.loads(result.message)
        value: str = message_data.get("value", result.message)
        return value

    def pack(self, data: str) -> DocumentData | None:
        if not self.document:
            return None
        document_data: DocumentData = DocumentData(
            data={"name": self.document, "value": data}, id=self.document
        )
        return document_data

    async def set(self, value: str) -> str | None:
        """Store value in MongoDB.

        Args:
            value: Data to store

        Raises:
            RuntimeError: If storage fails
            ValueError: If value invalid
        """
        if not value:
            raise ValueError("Value cannot be empty")
        db_connect: DbInitResult | None = await self.connect()
        if not db_connect:
            return None
        payload: DocumentData | None = self.pack(value)
        if not payload:
            return None
        add: mongodbResponse = await db_docAdd(payload)
        if not add.status:
            return None
        return value


class LLMAccessorHandler(BaseHandler):
    """Handler for LLM API Accessor management."""

    def __init__(self, provider: str, trait: Trait) -> None:
        """Initialize handler for specific LLM provider


        Args:
            provider: LLM provider name (e.g. 'openai', 'claude')
        """
        super().__init__(database=provider, collection="settings", document=trait)
