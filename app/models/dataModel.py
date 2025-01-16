"""
dataModel.py

This module defines the data models and schemas used throughout the SCLAI application.
The models leverage Pydantic for validation and type safety.

Features:
- Enum classes for message and logging types.
- Models for MongoDB interaction results and default document structures.
- Data structures for REPL commands and dynamic command groups.

Usage:
Import these models to validate and structure data used in the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum
from pfmongo.models.responseModel import mongodbResponse
import click


class MessageType(Enum):
    """
    Enum for message type/level.
    """

    INFO = 1
    ERROR = 2


class LoggingType(Enum):
    """
    Enum for logging type.
    """

    CONSOLE = 1
    NDJSON = 2


class Time(BaseModel):
    """
    A simple model that includes a time string field.
    """

    time: str = Field(..., description="Timestamp in ISO 8601 format.")


class InitializationResult(BaseModel):
    """
    Model for representing the result of database and collection initialization.

    Attributes:
        status (bool): Indicates whether the initialization was successful.
        source (str): Specifies the source of the operation (e.g., "MongoDB", "Local").
        message (Optional[str]): Provides additional context or information about the operation.
    """

    status: bool
    source: str
    message: Optional[str] = Field(
        default=None, description="Additional context or information."
    )


class DefaultDocument(BaseModel):
    """
    Model for the default document structure stored in a database or locally.

    Attributes:
        path (str): Specifies the logical path in the form "<database>/<collection>".
        id (Optional[str]): Unique identifier for the document.
        metadata (Optional[dict]): Additional metadata for the document.
    """

    path: str = Field(..., description="Logical path as '<database>/<collection>'.")
    id: Optional[str] = Field(
        default=None, description="Unique identifier for the document."
    )
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata for the document."
    )


class CommandGroup(BaseModel):
    """
    Model to define the structure for dynamic commands in the REPL.

    Attributes:
        commands (dict[str, click.Group]): A dictionary mapping command names to their associated Click groups.
    """

    commands: Dict[str, click.Group] = Field(
        ..., description="Mapping of command names to Click groups."
    )

    class Config:
        """
        Pydantic model configuration.
        """

        arbitrary_types_allowed = True


class DbInitResult(BaseModel):
    """
    Model representing the result of the `db_init` function.

    Attributes:
        db_response (mongodbResponse): The response object for the database connection.
        col_response (mongodbResponse): The response object for the collection connection.
    """

    db_response: mongodbResponse = Field(
        ..., description="Response object for the database connection."
    )
    col_response: mongodbResponse = Field(
        ..., description="Response object for the collection connection."
    )


class DocumentData(BaseModel):
    """
    Model representing the input data for the `db_add` function.

    Attributes:
        data (dict): The document data to be added to the collection.
        id (str): The unique identifier for the document.
    """

    data: Dict[str, Any] = Field(..., description="The document data to store.")
    id: str = Field(..., description="The unique identifier for the document.")


class DatabaseCollectionModel(BaseModel):
    """
    Model to represent a database and collection parsed from a dbcollection string.

    Attributes:
        database (str): The name of the database.
        collection (str): The name of the collection.
    """

    database: str
    collection: str
