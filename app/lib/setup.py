"""
setup.py

This module handles application setup and initialization, including database
configuration, API key management, and local storage fallback.

The module centralizes initialization tasks previously spread across settings.py
and sclai.py, providing a cleaner separation of concerns.

Features:
- Database and collection initialization
- Configuration management for LLM API keys and preferences
- Local storage fallback mechanisms
- Structured initialization result reporting

Usage:
Call app_initialize() to perform complete application setup.
Use config_update() to update LLM settings.
"""

import json
from pathlib import Path
from typing import Any, Optional, Final, Dict
from argparse import Namespace
import asyncio

from app.lib.mongodb_manager import db_manager
from app.lib.log import LOG
from app.config.settings import (
    CONFIG_FILE,
    CONFIG_DIR,
    json_validate,
    localStorage_pathEnsure,
)
from app.models.dataModel import (
    InitializationResult,
    DatabaseCollectionModel,
    DocumentData,
    DefaultDocument,
)
from pfmongo.models.responseModel import mongodbResponse
from rich.console import Console

# Console instance for rich output
console: Final[Console] = Console()

# Default metadata configuration
DEFAULT_META: Final[DefaultDocument] = DefaultDocument(
    path="settings/meta",
    id="meta.json",
    metadata={"keys": {"OpenAI": "", "Claude": ""}, "use": "OpenAI"},
)

# Core collections that need initialization
CORE_COLLECTIONS: Final[list[str]] = ["settings", "vars", "crawl", "auth"]


async def collection_initialize(
    collection_name: str, document: Optional[DefaultDocument] = None
) -> InitializationResult:
    """
    Initialize a MongoDB collection with an optional default document.

    Uses mongodb_manager to establish the connection and add the document
    if specified. Falls back to local storage if MongoDB operations fail.

    Args:
        collection_name: Name of the collection to initialize
        document: Optional default document to add to the collection

    Returns:
        InitializationResult: Result of the initialization operation
    """
    # Resolve collection to database
    db_collection: DatabaseCollectionModel = db_manager.collection_resolve(
        collection_name
    )

    # Skip document addition if none provided
    if not document:
        try:
            # Just connect to ensure collection exists
            await db_manager.collection_connect(collection_name)
            return InitializationResult(
                status=True,
                source="MongoDB",
                message=f"Collection {collection_name} initialized.",
            )
        except Exception as e:
            LOG(f"MongoDB initialization failed: {e}")
            return fallback_localCreate(
                db_collection.database, db_collection.collection
            )

    # Validate document if provided
    if not json_validate(document.model_dump()):
        return InitializationResult(
            status=False,
            source="Validation",
            message="Document contains invalid JSON and cannot be stored.",
        )

    try:
        # Check if document exists
        exists: bool = await db_manager.document_exists(
            collection_name, document.id or ""
        )

        if not exists and document.id:
            # Add document if it doesn't exist
            add_result: mongodbResponse = await db_manager.document_add(
                collection_name, document.id, document.model_dump()
            )

            if add_result.status:
                LOG(f"Document added to MongoDB: {document.id}")
                return InitializationResult(
                    status=True,
                    source="MongoDB",
                    message="Document added successfully.",
                )
            else:
                raise RuntimeError(f"Failed to add document: {add_result.message}")
        else:
            LOG("Document already exists in MongoDB.")
            return InitializationResult(
                status=True, source="MongoDB", message="Document already exists."
            )
    except Exception as e:
        LOG(f"MongoDB document operation failed: {e}")
        return fallback_localCreate(
            db_collection.database, db_collection.collection, document
        )


def fallback_localCreate(
    database: str, collection: str, document: Optional[DefaultDocument] = None
) -> InitializationResult:
    """
    Fallback to local storage when MongoDB operations fail.

    Creates the appropriate directory structure and saves document
    as a JSON file if provided.

    Args:
        database: The database name
        collection: The collection name
        document: Optional document to save locally

    Returns:
        InitializationResult: Result of the local fallback operation
    """
    try:
        # Create directory structure
        local_path: Path = localStorage_pathEnsure(database, collection)

        # If no document provided, just ensure the path exists
        if not document:
            return InitializationResult(
                status=True,
                source="Local",
                message=f"Local storage initialized at {local_path}",
            )

        # Save document if provided
        doc_filename: str = document.id or "default.json"
        file_path: Path = local_path / doc_filename

        with file_path.open("w") as f:
            json.dump(document.model_dump(), f, indent=4)

        LOG(f"Document written to local storage: {file_path}")
        return InitializationResult(
            status=True, source="Local", message=f"Document stored at {file_path}"
        )
    except Exception as e:
        LOG(f"Failed to write document to local storage: {e}")
        return InitializationResult(
            status=False,
            source="Local",
            message=f"Failed to store document locally: {str(e)}",
        )


async def app_initialize() -> InitializationResult:
    """
    Perform complete application initialization.

    Initializes all required collections and the default metadata document.

    Returns:
        InitializationResult: Result of the initialization process
    """
    # Initialize the settings collection with metadata
    meta_result: InitializationResult = await collection_initialize(
        "settings", document=DEFAULT_META
    )

    if not meta_result.status:
        return meta_result

    # Initialize other core collections
    for collection in CORE_COLLECTIONS:
        if collection != "settings":  # Already initialized above
            result: InitializationResult = await collection_initialize(collection)
            if not result.status:
                LOG(f"Warning: Failed to initialize {collection}: {result.message}")

    return meta_result  # Return the result of the primary initialization


async def config_update(llm: Optional[str], key: Optional[str]) -> bool:
    """
    Update the LLM configuration settings.

    Updates the active LLM provider and/or API key in either MongoDB
    or local storage.

    Args:
        llm: The LLM provider to use (e.g., "OpenAI", "Claude")
        key: The API key for the specified provider

    Returns:
        bool: True if update successful, False otherwise

    Raises:
        ValueError: If key is provided without specifying the LLM
    """
    try:
        # Try MongoDB first
        if await db_manager.document_exists("settings", DEFAULT_META.id or ""):
            LOG("Updating configuration in MongoDB.")

            # Get existing config
            response: mongodbResponse = await db_manager.document_get(
                "settings", DEFAULT_META.id or ""
            )

            if not response.status:
                raise RuntimeError("Failed to retrieve existing configuration.")

            existing_config: dict[str, Any] = json.loads(response.message)

            # Update config with new values
            if llm:
                existing_config["metadata"]["use"] = llm
            if key:
                if llm:
                    existing_config["metadata"]["keys"][llm] = key
                else:
                    raise ValueError(
                        "You must specify the LLM provider with '--use' when setting a key."
                    )

            # Save updated config
            add_result: mongodbResponse = await db_manager.document_add(
                "settings", DEFAULT_META.id or "", existing_config
            )

            if add_result.status:
                LOG("Configuration successfully updated in MongoDB.")
                return True
            else:
                LOG(f"Failed to update configuration in MongoDB: {add_result.message}")
                return False

        # Fall back to local storage if MongoDB unavailable
        else:
            LOG("MongoDB unavailable. Falling back to local configuration file.")

            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Load existing config or create new one
            if CONFIG_FILE.exists():
                config: dict[str, Any] = json.loads(CONFIG_FILE.read_text())
            else:
                config: dict[str, Any] = {
                    "metadata": DEFAULT_META.metadata,
                    "path": DEFAULT_META.path,
                    "id": DEFAULT_META.id,
                }

            # Update config with new values
            if llm:
                config["metadata"]["use"] = llm
            if key:
                if llm:
                    config["metadata"]["keys"][llm] = key
                else:
                    raise ValueError(
                        "You must specify the LLM provider with '--use' when setting a key."
                    )

            # Save updated config
            CONFIG_FILE.write_text(json.dumps(config, indent=4))
            LOG(f"Updated local configuration file: {CONFIG_FILE}.")
            return True

    except Exception as e:
        LOG(f"Failed to update configuration: {e}")
        return False


async def app_configure(options: Namespace) -> bool:
    """
    Configure application based on command-line options.

    Handles initialization and updates configuration if required.

    Args:
        options: Parsed command-line arguments

    Returns:
        bool: True if configuration successful, False otherwise
    """
    try:
        # Initialize system
        result: InitializationResult = await app_initialize()

        if not result.status:
            console.print(
                f"[bold red]Configuration initialization failed: {result.message}[/bold red]"
            )
            return False

        # Update configuration if options provided
        if options.use or options.key:
            try:
                if await config_update(options.use, options.key):
                    console.print(
                        "[bold green]Configuration updated successfully.[/bold green]"
                    )
                else:
                    console.print(
                        "[bold red]Failed to update configuration.[/bold red]"
                    )
                    return False
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                return False

        return True

    except Exception as e:
        LOG(f"Configuration setup failed: {e}")
        return False
