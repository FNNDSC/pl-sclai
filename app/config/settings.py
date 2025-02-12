"""
settings.py

This module provides configuration management and database initialization utilities
for the application.

Features:
- Centralized configuration using Pydantic settings.
- Functions for initializing MongoDB databases and collections.
- Fallback mechanisms for local storage in case of MongoDB failures.

Usage:
Call `config_initialize` to set up the default database and collection.
Use `databaseCollection_initialize` for custom database/collection setups.
"""

import json
from pathlib import Path
from typing import Any, Optional
from appdirs import user_config_dir
from app.models.dataModel import (
    DbInitResult,
    InitializationResult,
    DefaultDocument,
    DocumentData,
    DatabaseCollectionModel,
)
from app.lib.log import LOG
from app.lib.mongodb import db_init, db_contains, db_docAdd
from pydantic_settings import BaseSettings, SettingsConfigDict
from pfmongo.models.responseModel import mongodbResponse

# Base directory for local fallback storage
BASE_DIR: Path = Path.home() / "data" / "claimm"

# Consolidated default configuration
DEFAULT_META: DefaultDocument = DefaultDocument(
    path="settings/meta",
    id="meta.json",
    metadata={"keys": {"OpenAI": "", "Claude": ""}, "use": "OpenAI"},
)

# Set up the configuration directory and file using appdirs
CONFIG_DIR: Path = Path(user_config_dir("sclai", ""))
CONFIG_FILE: Path = CONFIG_DIR / "config.json"  # Ensure consistent naming and format


class App(BaseSettings):
    """
    Application settings model.

    Attributes:
        beQuiet (bool): Suppress detailed logging output.
        noComplain (bool): Disable complaint logs.
        detailedOutput (bool): Enable detailed output.
        eventLoopDebug (bool): Enable asyncio event loop debug mode.
        fontawesomeUse (bool): Use FontAwesome in outputs.
        settings_dbcollection (str): Path to the MongoDB collection for application settings.
        vars_dbcollection (str): Path to the MongoDB collection for user-defined variables.
        crawl_dbcollection (str): Path to the MongoDB collection for web crawl data.
    """

    beQuiet: bool = False
    noComplain: bool = False
    detailedOutput: bool = False
    eventLoopDebug: bool = False
    fontawesomeUse: bool = True
    settings_dbcollection: str = "/claimm/settings"
    vars_dbcollection: str = "/claimm/vars"
    crawl_dbcollection: str = "/claimm/crawl"

    def parse_dbcollection(self, dbcollection: str) -> DatabaseCollectionModel:
        """
        Parse a dbcollection string into database and collection components.

        :param dbcollection: The dbcollection string (e.g., '/database/collection').
        :return: A DatabaseCollectionModel containing the database and collection names.
        :raises ValueError: If the input string is not properly formatted.
        """
        if not dbcollection.startswith("/") or dbcollection.count("/") != 2:
            raise ValueError(
                f"Invalid dbcollection format: '{dbcollection}'. Expected format: '/database/collection'."
            )

        _, database, collection = dbcollection.split("/")
        return DatabaseCollectionModel(database=database, collection=collection)

    model_config = SettingsConfigDict(
        env_prefix="SCL_",  # Matches environment variables with this prefix
        case_sensitive=False,  # Allows case-insensitive matching of environment variables
        extra="allow",
    )


def validate_json(data: dict[str, Any]) -> bool:
    """
    Validate if the provided data is serializable as JSON.

    :param data: The data to validate.
    :return: True if valid, False otherwise.
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError) as e:
        LOG(f"Invalid JSON data: {e}")
        return False


async def databaseCollection_initialize(
    db_collection: DatabaseCollectionModel, document: Optional[DefaultDocument] = None
) -> InitializationResult:
    """
    Generalized method to initialize a MongoDB database and collection, with a default document.

    :param db_collection: A DatabaseCollectionModel containing the database and collection names.
    :param document: The document to initialize in the collection. Defaults to a basic document if not provided.
    :return: InitializationResult indicating success/failure and source (MongoDB or local storage).
    """
    # Use the provided document or create a default one
    document = document or DefaultDocument(
        path=f"{db_collection.database}/{db_collection.collection}"
    )

    # Ensure document has a valid id
    if not document.id:
        document.id = f"{db_collection.collection}_default.json"

    # Validate the document
    if not validate_json(document.model_dump()):
        return InitializationResult(
            status=False,
            source="Validation",
            message="Document contains invalid JSON and cannot be stored.",
        )

    try:
        # Initialize MongoDB
        dbinit: DbInitResult = await db_init(db_collection)

        # Check if the document exists
        response: mongodbResponse = await db_contains(document.id)
        if not response.status:
            doc_data: DocumentData = DocumentData(
                data=document.model_dump(), id=document.id
            )
            add_result: mongodbResponse = await db_docAdd(doc_data)
            if add_result.status:
                LOG(f"Document added to MongoDB: {add_result.message}")
                return InitializationResult(
                    status=True,
                    source="MongoDB",
                    message="Document added successfully.",
                )
            else:
                raise RuntimeError("Failed to add the document to MongoDB.")
        else:
            LOG("Document already exists in MongoDB.")
            return InitializationResult(
                status=True, source="MongoDB", message="Document already exists."
            )
    except Exception as e:
        LOG(f"MongoDB initialization failed: {e}")
        return _initialize_local(
            db_collection.database, db_collection.collection, document
        )


def _initialize_local(
    database: str, collection: str, document: DefaultDocument
) -> InitializationResult:
    """
    Fallback to local storage: create directories and save the document as a JSON file.

    :param database: The name of the database.
    :param collection: The name of the collection.
    :param document: The document to save locally.
    :return: InitializationResult indicating success or failure.
    """
    try:
        local_path: Path = BASE_DIR / database / collection
        local_path.mkdir(parents=True, exist_ok=True)
        default_file: Path = local_path / "default.json"
        with default_file.open("w") as f:
            json.dump(document.model_dump(), f, indent=4)
        LOG(f"Document written to local storage: {default_file}")
        return InitializationResult(
            status=True, source="Local", message=f"Document stored at {default_file}"
        )
    except Exception as e:
        LOG(f"Failed to write document to local storage: {e}")
        return InitializationResult(
            status=False, source="Local", message="Failed to store document locally."
        )


async def config_initialize() -> InitializationResult:
    """
    Initialize the default 'settings/meta' database and collection.

    :return: InitializationResult indicating the result of the operation.
    """
    result: InitializationResult = await databaseCollection_initialize(
        DatabaseCollectionModel(database="claimm", collection="settings"),
        document=DEFAULT_META,
    )

    return result


async def config_update(llm: Optional[str], key: Optional[str]) -> bool:
    """
    Updates the MongoDB 'meta' collection or the local configuration file with the specified LLM and/or API key.

    :param llm: The LLM to use (e.g., OpenAI, Claude).
    :param key: The API key for the specified LLM.
    :return: True if the configuration update succeeds, False otherwise.
    """
    try:
        response: mongodbResponse = await db_contains(DEFAULT_META.id or "")

        if response.status:
            LOG("Updating configuration in MongoDB.")
            existing_config: dict[str, Any] = json.loads(response.message)

            if llm:
                existing_config["metadata"]["use"] = llm
            if key:
                if llm:
                    existing_config["metadata"]["keys"][llm] = key
                else:
                    raise ValueError(
                        "You must specify '--use' with '--key' to associate the key with an LLM."
                    )

            doc_data: DocumentData = DocumentData(
                data=existing_config, id=DEFAULT_META.id or ""
            )
            add_result: mongodbResponse = await db_docAdd(doc_data)
            if add_result.status:
                LOG("Configuration successfully updated in MongoDB.")
                return True
            else:
                LOG("Failed to update configuration in MongoDB.")
                return False
        else:
            LOG("MongoDB unavailable. Falling back to local configuration file.")
            if CONFIG_FILE.exists():
                config: dict[str, Any] = json.loads(CONFIG_FILE.read_text())
            else:
                config: dict[str, Any] = {
                    "metadata": DEFAULT_META.metadata,
                    "path": DEFAULT_META.path,
                    "id": DEFAULT_META.id,
                }

            if llm:
                config["metadata"]["use"] = llm
            if key:
                if llm:
                    config["metadata"]["keys"][llm] = key
                else:
                    raise ValueError(
                        "You must specify '--use' with '--key' to associate the key with an LLM."
                    )

            CONFIG_FILE.write_text(json.dumps(config, indent=4))
            LOG(f"Updated local configuration file: {CONFIG_FILE}.")
            return True
    except Exception as e:
        LOG(f"Failed to update configuration: {e}")
        return False


appsettings: App = App()
