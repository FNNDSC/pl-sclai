"""
mongodb_manager.py

A centralized manager for MongoDB operations with explicit context handling.

Database Architecture:
- Core Database ("tame" by default):
  Used for system-level data and configurations. Contains collections:
  - settings: Application settings and configuration
  - vars: System variables
  - session: Session contexts for authenticated users
  - auth: Authentication tokens and permissions
  - crawl: Cached website data in b64 encoded zips

- Users Database ("users" by default):
  Contains a collection per user, named after the username.
  Each user collection contains:
  - password.json: User credentials (stored as plaintext for now)
  - session.json: User's active LLM and session context

Usage:
Import the MongoDBManager singleton instance `db_manager` to perform database operations.
All operations take explicit collection names and handle their own database resolution.
"""

from argparse import Namespace
from typing import Optional, Any, cast
import json
import os
from pydantic import BaseModel, Field
from pfmongo import pfmongo
from pfmongo.commands.dbop import connect as database
from pfmongo.commands.clop import connect as collection
from pfmongo.commands.docop import add as datacol, get
from pfmongo.commands.document import delete as deldoc
from pfmongo.commands.docop import showAll
from pfmongo.models.responseModel import mongodbResponse
from app.models.dataModel import DbInitResult, DocumentData, DatabaseCollectionModel
from app.lib.log import LOG
import pudb


class DatabaseNames(BaseModel):
    """
    MongoDB database names configuration

    These values define the MongoDB database structure and can be
    configured through environment variables if needed.
    """

    CORE: str = Field(default="tame", description="Core system database name")
    USERS: str = Field(default="users", description="User data database name")


class CoreCollections(BaseModel):
    """
    Core database collections configuration

    Defines the collections within the core database.
    """

    SETTINGS: str = Field(
        default="settings", description="Application settings collection"
    )
    VARS: str = Field(default="vars", description="System variables collection")
    SESSION: str = Field(default="session", description="Session contexts collection")
    AUTH: str = Field(default="auth", description="Authentication tokens collection")
    CRAWL: str = Field(default="crawl", description="Cached website data collection")

    def collections_getAll(self) -> list[str]:
        """
        Retrieve all core collection names

        Returns:
            list[str]: List of all collection names defined in this configuration
        """
        return [self.SETTINGS, self.VARS, self.SESSION, self.AUTH, self.CRAWL]


class StandardDocuments(BaseModel):
    """
    Standard document names configuration

    Defines standard document names used across collections.
    """

    PASSWORD: str = Field(default="password.json", description="User password document")
    SESSION: str = Field(
        default="session.json", description="User session context document"
    )
    AUTH: str = Field(
        default="auth.json", description="User authentication token document"
    )


# Create configuration instances
# First check for config file, then fall back to defaults
config_file_path: str = os.path.join(
    os.path.dirname(__file__), "..", "config", "db_config.json"
)
db_names: DatabaseNames = DatabaseNames()
core_collections: CoreCollections = CoreCollections()
std_documents: StandardDocuments = StandardDocuments()

# Try to load from config file if it exists
if os.path.exists(config_file_path):
    try:
        with open(config_file_path) as f:
            config: dict[str, Any] = json.load(f)
            db_names = DatabaseNames(**config.get("database_names", {}))
            core_collections = CoreCollections(**config.get("core_collections", {}))
            std_documents = StandardDocuments(**config.get("standard_documents", {}))
        LOG(f"Loaded database configuration from {config_file_path}")
    except Exception as e:
        LOG(f"Error loading database configuration: {e}. Using defaults.")


class MongoDBManager:
    """MongoDB connection and operation manager with explicit contexts

    Handles all database operations with explicit collection naming.
    Determines appropriate database for each collection and manages
    connections automatically for each operation.

    Database organization:
    - Core database (configurable, default: "tame"): System settings and global data
      Contains collections defined in CoreCollections class
    - Users database (configurable, default: "users"): User-specific data
      Each user has their own collection named after their username
    """

    # Singleton instance
    _instance: Optional["MongoDBManager"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MongoDBManager":
        """
        Ensure only one instance exists (Singleton pattern)

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            MongoDBManager: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
        return cls._instance

    def __init__(
        self, core_db: str = db_names.CORE, users_db: str = db_names.USERS
    ) -> None:
        """
        Initialize the MongoDB manager

        Args:
            core_db: Name of the core database (default from configuration)
            users_db: Name of the users database (default from configuration)
        """
        # Skip initialization if already done (singleton pattern)
        if hasattr(self, "initialized"):
            return

        self.core_db: str = core_db
        self.users_db: str = users_db
        self.core_collections: list[str] = core_collections.collections_getAll()
        self.initialized: bool = True

    def database_resolve(self, collection_name: str) -> str:
        """
        Determine which database a collection belongs to

        Maps collection names to their appropriate database.
        Core collections go to core_db, everything else to users_db.

        Args:
            collection_name: Name of the collection

        Returns:
            str: Database name where the collection should be stored
        """
        return (
            self.core_db if collection_name in self.core_collections else self.users_db
        )

    def collection_resolve(self, collection_name: str) -> DatabaseCollectionModel:
        """
        Create a DatabaseCollectionModel by resolving collection to its database

        Args:
            collection_name: Name of the collection

        Returns:
            DatabaseCollectionModel: Model with proper database assignment
        """
        database: str = self.database_resolve(collection_name)
        return DatabaseCollectionModel(database=database, collection=collection_name)

    async def connection_init(
        self, db_collection: DatabaseCollectionModel
    ) -> DbInitResult:
        """
        Initialize connection to a database and collection

        Args:
            db_collection: Database and collection to connect to

        Returns:
            DbInitResult: Result of the connection initialization
        """
        try:
            # Initialize database connection
            db_options: Namespace = database.options_add(
                db_collection.database, pfmongo.options_initialize()
            )
            db_response: mongodbResponse = await database.connectTo_asModel(db_options)

            # Initialize collection connection
            col_options: Namespace = collection.options_add(
                db_collection.collection, pfmongo.options_initialize()
            )
            col_response: mongodbResponse = await collection.connectTo_asModel(
                col_options
            )

            LOG(f"Connected to {db_collection.database}/{db_collection.collection}")
            return DbInitResult(db_response=db_response, col_response=col_response)
        except Exception as e:
            error_msg: str = f"Error initializing MongoDB: {e}"
            LOG(error_msg)

            # Create error response models
            db_error: mongodbResponse = mongodbResponse(
                status=False,
                message=f"Error initializing database: {e}",
                response={},
                exitCode=1,
            )
            col_error: mongodbResponse = mongodbResponse(
                status=False,
                message=f"Error initializing collection: {e}",
                response={},
                exitCode=1,
            )

            return DbInitResult(db_response=db_error, col_response=col_error)

    async def collection_connect(self, collection_name: str) -> DatabaseCollectionModel:
        """
        Connect to a specific collection

        Args:
            collection_name: Name of the collection to connect to

        Returns:
            DatabaseCollectionModel: Model with connection information
        """
        db_collection: DatabaseCollectionModel = self.collection_resolve(
            collection_name
        )
        await self.connection_init(db_collection)
        return db_collection

    async def document_add(
        self, collection_name: str, document_id: str, data: dict[str, Any]
    ) -> mongodbResponse:
        """
        Add a document to a specific collection

        Args:
            collection_name: Name of the collection to add to
            document_id: ID for the document
            data: Document content

        Returns:
            mongodbResponse: Result of the document addition operation
        """
        # Connect to collection
        await self.collection_connect(collection_name)

        # Add document
        try:
            # Prepare document data
            document_data: DocumentData = DocumentData(data=data, id=document_id)

            # Initialize options
            options: Namespace = datacol.options_add(
                json.dumps(document_data.data),
                document_data.id,
                pfmongo.options_initialize(),
            )

            # Add document
            result: mongodbResponse = await datacol.documentAdd_asModel(options)
            return result
        except Exception as e:
            error_msg: str = f"Error adding document to MongoDB: {e}"
            LOG(error_msg)
            return mongodbResponse(
                status=False,
                message=error_msg,
                response={},
                exitCode=1,
            )

    async def document_get(
        self, collection_name: str, document_id: str
    ) -> mongodbResponse:
        """
        Get a document from a collection

        Args:
            collection_name: Name of the collection
            document_id: ID of the document to retrieve

        Returns:
            mongodbResponse: MongoDB response with document data
        """
        # Connect to collection
        await self.collection_connect(collection_name)

        # Get document
        try:
            options: Namespace = get.options_add(
                document_id, pfmongo.options_initialize()
            )
            return await get.documentGet_asModel(options)
        except Exception as e:
            error_msg: str = f"Error retrieving document from MongoDB: {e}"
            LOG(error_msg)
            return mongodbResponse(
                status=False,
                message=error_msg,
                response={},
                exitCode=1,
            )

    async def document_exists(self, collection_name: str, document_id: str) -> bool:
        """
        Check if a document exists in a collection

        Args:
            collection_name: Name of the collection to check
            document_id: ID of the document to check for

        Returns:
            bool: True if document exists, False otherwise
        """
        # Connect to collection
        await self.collection_connect(collection_name)

        # Check for document
        result: mongodbResponse = await self.document_get(collection_name, document_id)
        return result.status

    async def document_delete(
        self, collection_name: str, document_id: str
    ) -> mongodbResponse:
        """
        Delete a document from a collection

        Args:
            collection_name: Name of the collection
            document_id: ID of the document to delete

        Returns:
            mongodbResponse: MongoDB response with deletion result
        """
        # Connect to collection
        await self.collection_connect(collection_name)

        # Delete document
        try:
            options: Namespace = deldoc.options_add(
                document_id, pfmongo.options_initialize()
            )
            result: mongodbResponse = await deldoc.deleteDo_asModel(options)
            return result
        except Exception as e:
            error_msg: str = f"Error deleting document from MongoDB: {e}"
            LOG(error_msg)
            return mongodbResponse(
                status=False,
                message=error_msg,
                response={},
                exitCode=1,
            )

    async def documents_getAll(
        self, collection_name: str, sort_field: str = "_id"
    ) -> mongodbResponse:
        """
        Retrieve all documents from a collection

        Args:
            collection_name: Name of the collection
            sort_field: Field to sort results by (default: "_id")

        Returns:
            mongodbResponse: MongoDB response with all documents
        """
        # Connect to collection
        await self.collection_connect(collection_name)

        # Get all documents
        try:
            options: Namespace = showAll.options_add(
                sort_field, pfmongo.options_initialize()
            )
            result: mongodbResponse = await showAll.showAll_asModel(options)
            return result
        except Exception as e:
            error_msg: str = f"Error retrieving all documents: {e}"
            LOG(error_msg)
            return mongodbResponse(
                status=False,
                message=error_msg,
                response={},
                exitCode=1,
            )


# Create singleton instance
db_manager: MongoDBManager = MongoDBManager()
