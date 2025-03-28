"""
Base handler implementations for SCLAI command routing.

This module provides base handler classes for the routing system:
- MongoDB integration through mongodb_manager
- Standard get/set operations
- Error handling and validation
- Storage location management

Implementation:
    Handlers map commands to MongoDB operations:
    /<command>/<context> -> database/collection/document

Example:
    /openai key -> maps to database="llm", collection="keys", document="openai"
"""

from typing import Any, Optional
from app.models.dataModel import (
    DocumentData,
    RouteHandler,
    DatabaseCollectionModel,
    DbInitResult,
)
from app.lib.mongodb_manager import db_manager
from app.models.dataModel import Trait
from pfmongo.models.responseModel import mongodbResponse
import json
from types import SimpleNamespace


class BaseHandler(RouteHandler):
    """
    Base route handler with MongoDB storage

    Provides a foundation for command routing with storage
    operations using mongodb_manager for database interaction.
    All specific handlers should inherit from this class.
    """

    def __init__(
        self, database: str, collection: str, document: Optional[Trait] = None
    ) -> None:
        """
        Initialize handler with storage location

        Sets up the handler with database location information
        that will be used for all storage operations.

        Args:
            database: MongoDB database name
            collection: MongoDB collection name
            document: Optional document identifier trait
        """
        self.database: str = database
        self.collection: str = collection
        self.document: Optional[str] = None
        if document:
            self.document = document.value

    async def connect(self) -> Optional[DatabaseCollectionModel]:
        """
        Ensure connection to the MongoDB collection

        Establishes a connection to the specified database and collection
        using mongodb_manager.

        Returns:
            DatabaseCollectionModel if connection successful, None otherwise
        """
        try:
            # Create collection model
            db_collection: DatabaseCollectionModel = DatabaseCollectionModel(
                database=self.database, collection=self.collection
            )

            # Connect to the collection
            await db_manager.collection_connect(self.collection)
            return db_collection
        except Exception as e:
            return None

    async def get(self) -> Optional[str]:
        """
        Get value from MongoDB.
        All the "get" methods eventually arrive here.

        Returns:
            Stored value or None
        """
        # Ensure connection
        db_collection: Optional[DatabaseCollectionModel] = await self.connect()
        if not db_collection or not self.document:
            return None

        # Check if document exists
        exists: bool = await db_manager.document_exists(self.collection, self.document)

        if not exists:
            return None

        # Get document data
        result: mongodbResponse = await db_manager.document_get(
            self.collection, self.document
        )

        # Extract value from result
        value: Optional[str] = None
        try:
            message_data = json.loads(result.message)
            value = message_data.get("value", result.message)
        except Exception as e:
            value = None

        return value

    def pack(self, data: str) -> Optional[DocumentData]:
        """
        Pack data into a DocumentData object for storage

        Prepares data structure for MongoDB storage.

        Args:
            data: Content to be stored

        Returns:
            DocumentData object or None if document ID not available
        """
        if not self.document:
            return None

        document_data: DocumentData = DocumentData(
            data={"name": self.document, "value": data}, id=self.document
        )
        return document_data

    async def set(self, value: str) -> Optional[str]:
        """
        Store value in MongoDB.
        All the "set" methods eventually arrive here.

        Args:
            value: Data to store

        Raises:
            RuntimeError: If storage fails
            ValueError: If value invalid
        """
        if not value:
            raise ValueError("Value cannot be empty")

        # Ensure connection
        db_collection: Optional[DatabaseCollectionModel] = await self.connect()
        if not db_collection:
            return None

        # Pack data for storage
        payload: Optional[DocumentData] = self.pack(value)
        if not payload:
            return None

        # Add document to collection
        add: mongodbResponse = await db_manager.document_add(
            self.collection, payload.id, payload.data
        )

        if not add.status:
            return None

        return value


class LLMAccessorHandler(BaseHandler):
    """
    Handler for LLM API Accessor management

    Specialized handler for managing LLM provider settings
    such as API keys and configuration values.
    """

    def __init__(self, provider: str, trait: Trait) -> None:
        """
        Initialize handler for specific LLM provider

        Sets up storage location for LLM provider settings.

        Args:
            provider: LLM provider name (e.g. 'openai', 'claude')
            trait: Type of setting to manage (e.g. KEY, MODEL)
        """
        super().__init__(database=provider, collection="settings", document=trait)


class UserLLMSessionHandler(BaseHandler):
    """
    Handler for User LLM Session Accessor management

    Specialized handler for managing user-specific LLM session data,
    allowing users to maintain persistent state with LLMs.
    """

    def __init__(self, user: str, trait: Trait) -> None:
        """
        Initialize handler for specific user's LLM Session

        Sets up storage location for user session data.

        Args:
            user: Username for session management
            trait: Type of session data to manage (e.g. SESSION, CONTEXT)
        """
        super().__init__(database="users", collection=user, document=trait)


class UserAuthHandler(BaseHandler):
    """
    Handler for User Auth management

    Specialized handler for managing user-specific auth data.
    """

    def __init__(self, user: str, trait: Trait) -> None:
        """
        Initialize handler for specific user's auth

        Sets up storage location for user auth data.

        Args:
            user: Username for session management
            trait: Type of session data to manage (e.g. SESSION, CONTEXT)
        """
        super().__init__(database="tame", collection="auth", document=trait)
