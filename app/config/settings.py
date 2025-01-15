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
from app.lib.mongodb import db_init, db_contains, db_add
from app.models.dataModel import InitializationResult, DefaultDocument
from app.lib.log import LOG
from pydantic_settings import BaseSettings
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
    """

    beQuiet: bool = False
    noComplain: bool = False
    detailedOutput: bool = False
    eventLoopDebug: bool = False
    fontawesomeUse: bool = True

    class Config:
        env_prefix = "SCL_"  # Matches environment variables with SCL to this app
        case_sensitive = False  # Optional: Allows case-insensitive matching


def validate_json(data: dict) -> bool:
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
    database: str, collection: str, document: Optional[DefaultDocument] = None
) -> InitializationResult:
    """
    Generalized method to initialize a MongoDB database and collection, with a default document.

    :param database: The name of the database.
    :param collection: The name of the collection.
    :param document: The document to initialize in the collection. Defaults to a basic document if not provided.
    :return: InitializationResult indicating success/failure and source (MongoDB or local storage).
    """
    # Use default document if none is provided
    if document is None:
        document = DefaultDocument(path=f"{database}/{collection}")

    # Ensure document has a valid id
    if not document.id:
        document.id = f"{collection}_default.json"

    # Validate the document
    if not validate_json(document.model_dump()):
        return InitializationResult(
            status=False,
            source="Validation",
            message="Document contains invalid JSON and cannot be stored.",
        )

    try:
        # Initialize MongoDB
        LOG(
            f"Initializing MongoDB database '{database}' and collection '{collection}'."
        )
        db: mongodbResponse
        col: mongodbResponse
        db, col = await db_init(database, collection)

        # Check if the document exists
        response: mongodbResponse = await db_contains(document.id)
        if not response.status:
            add_result: mongodbResponse = await db_add(
                document.model_dump(), document.id
            )
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
        return _initialize_local(database, collection, document)


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
    return await databaseCollection_initialize("claimm", "settings", DEFAULT_META)


async def config_update(llm: str | None, key: str | None) -> bool:
    """
    Updates the MongoDB 'meta' collection or the local configuration file with the specified LLM and/or API key.

    :param llm: The LLM to use (e.g., OpenAI, Claude).
    :param key: The API key for the specified LLM.
    :return: True if the configuration update succeeds, False otherwise.
    """
    try:
        # Check if MongoDB is initialized
        response: mongodbResponse = await db_contains(DEFAULT_META.id or "")

        if response.status:
            LOG("Updating configuration in MongoDB.")
            # Fetch existing configuration from MongoDB
            existing_config: dict = json.loads(response.message)

            # Update the LLM and/or API key in the configuration
            if llm:
                existing_config["metadata"]["use"] = llm
            if key:
                if llm:
                    existing_config["metadata"]["keys"][llm] = key
                else:
                    raise ValueError(
                        "You must specify '--use' with '--key' to associate the key with an LLM."
                    )

            # Save updated configuration to MongoDB
            add_result: mongodbResponse = await db_add(
                existing_config, DEFAULT_META.id or ""
            )
            if add_result.status:
                LOG("Configuration successfully updated in MongoDB.")
                return True
            else:
                LOG("Failed to update configuration in MongoDB.")
                return False
        else:
            # Fallback to local configuration
            LOG("MongoDB unavailable. Falling back to local configuration file.")
            if CONFIG_FILE.exists():
                config: dict = json.loads(CONFIG_FILE.read_text())
            else:
                config = DEFAULT_META.dict()

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
