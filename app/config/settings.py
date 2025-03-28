"""
settings.py

This module provides application configuration management for the SCLAI application.
Core database operations have been moved to mongodb_manager.py.

Features:
- Centralized application configuration using Pydantic settings
- Constants for application-wide use
- Basic JSON validation utilities

Usage:
Import appsettings for application configuration values.
"""

import json
from pathlib import Path
from typing import Any, Final
from appdirs import user_config_dir
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.lib.log import LOG
from app.lib.mongodb_manager import db_manager, std_documents
from rich.console import Console

# Console instance for rich output
console: Final[Console] = Console()

# Base directory for local fallback storage
BASE_DIR: Final[Path] = Path.home() / "data" / "tame"

# Set up the configuration directory and file using appdirs
CONFIG_DIR: Final[Path] = Path(user_config_dir("sclai", ""))
CONFIG_FILE: Final[Path] = CONFIG_DIR / "config.json"


class App(BaseSettings):
    """
    Application settings model.

    Provides a centralized configuration for application behavior and features.
    Settings can be overridden through environment variables with SCL_ prefix.

    Attributes:
        beQuiet: Suppress detailed logging output
        noComplain: Disable complaint logs
        detailedOutput: Enable detailed output format
        eventLoopDebug: Enable asyncio event loop debug mode
        fontawesomeUse: Use FontAwesome in rich console outputs
    """

    beQuiet: bool = False
    noComplain: bool = False
    detailedOutput: bool = False
    eventLoopDebug: bool = False
    fontawesomeUse: bool = True

    # Debug mode flag
    debug_mode: bool = False

    # API request timeout in seconds
    request_timeout: int = 30

    model_config = SettingsConfigDict(
        env_prefix="SCL_",  # Environment variables with this prefix override settings
        case_sensitive=False,  # Allow case-insensitive environment variables
        extra="allow",  # Allow additional attributes not defined in the model
    )


def json_validate(data: dict[str, Any]) -> bool:
    """
    Validate if the provided data is serializable as JSON.

    Tests whether the data can be properly serialized to JSON format,
    which ensures it can be stored in MongoDB or written to files.

    Args:
        data: The data dictionary to validate

    Returns:
        bool: True if valid JSON, False otherwise
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError) as e:
        LOG(f"Invalid JSON data: {e}")
        return False


def localStorage_pathGet(database: str, collection: str) -> Path:
    """
    Get the local filesystem path for fallback storage.

    Creates a path structure that mirrors the MongoDB organization
    for consistent access in case of database failures.

    Args:
        database: The database name
        collection: The collection name

    Returns:
        Path: The local filesystem path
    """
    return BASE_DIR / database / collection


def localStorage_pathEnsure(database: str, collection: str) -> Path:
    """
    Ensure local storage path exists and return it.

    Creates the directory structure if it doesn't exist.

    Args:
        database: The database name
        collection: The collection name

    Returns:
        Path: The created or existing path
    """
    path = localStorage_pathGet(database, collection)
    path.mkdir(parents=True, exist_ok=True)
    return path


# Create the application settings instance
appsettings: Final[App] = App()
