from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from pathlib import Path
import click


class messageType(Enum):
    """
    Enum for message type/level.
    """

    INFO = 1
    ERROR = 2


class loggingType(Enum):
    """
    Enum for logging type.
    """

    CONSOLE = 1
    NDJSON = 2


class time(BaseModel):
    """
    A simple model that includes a time string field.
    """

    time: str


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
    message: Optional[str] = None


class DefaultDocument(BaseModel):
    """
    Model for the default document structure stored in a database or locally.

    Attributes:
        path (str): Specifies the logical path in the form "<database>/<collection>".
        id (Optional[str]): Unique identifier for the document.
        metadata (Optional[dict]): Additional metadata for the document.
    """

    path: str
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
        commands: A dictionary mapping command names to their associated Click groups.
    """

    commands: dict[str, click.Group]

    class Config:
        """
        Pydantic model configuration.
        """

        arbitrary_types_allowed = True
