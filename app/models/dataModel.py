"""
dataModel.py

This module defines the data models and schemas used throughout the SCLAI application.
The models leverage Pydantic for validation and type safety.

Features:
- Enum classes for message and logging types.
- Models for MongoDB interaction results and default document structures.
- Data structures for REPL commands and dynamic command groups.
- Input processing results
- Parsing results
- Command processing
- Database operations

Usage:
Import these models to validate and structure data used in the application.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict, NamedTuple
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

    model_config = ConfigDict(arbitrary_types_allowed=True)
    commands: Dict[str, click.Group] = Field(
        ..., description="Mapping of command names to Click groups."
    )


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


class ParseResult(BaseModel):
    """Result of token parsing operation.

    Attributes:
        text: The processed text after substitutions
        error: Optional error message if parsing failed
        success: Whether parsing succeeded
    """

    text: str
    error: str | None
    success: bool


class InputResult(BaseModel):
    """Result of input collection operation.

    Attributes:
        text: The collected input text
        continue_loop: Whether to continue processing
        error: Optional error message if input collection failed
    """

    text: str
    continue_loop: bool
    error: str | None = None


class ProcessResult(BaseModel):
    """Result of command/input processing.

    Attributes:
        text: Processed output text or command output
        is_command: Whether input was a command
        should_exit: Whether to exit processing
        error: Optional error message
        success: Whether processing succeeded
        exit_code: Exit code for non-interactive mode
    """

    text: str
    is_command: bool
    should_exit: bool
    error: str | None = None
    success: bool = True
    exit_code: int = 0


class InputMode(BaseModel):
    """Input mode determination.

    Attributes:
        has_stdin: Whether stdin has content
        ask_string: Direct query string if provided
        use_repl: Whether to use interactive REPL
    """

    has_stdin: bool = False
    ask_string: str | None = None
    use_repl: bool = True
