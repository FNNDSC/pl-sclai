"""
Context Management Commands

Provides CLI commands for managing execution contexts.

MongoDB Structure:
- Core Database (`tame`):
  - `contexts`: Collection storing execution context metadata
    - Documents identified by context ID contain session metadata

Commands:
- /context create [<context_id>]: Create a new context (auto-generates if omitted)
- /context set <context_id>: Set the active REPL context
- /context get: Retrieve the active REPL context
- /context revoke: Clear the active REPL context
- /context list: List all stored contexts
- /context delete <context_id>: Remove a context
"""

import click
import ast
from typing import Optional, List, Any, cast
from datetime import datetime
from pydantic import BaseModel

from app.commands.base import RichGroup, RichCommand, rich_help
from app.config.settings import console
from app.lib.mongodb_manager import db_manager
from app.models.dataModel import (
    DocumentData,
    DatabaseCollectionModel,
    RuntimeInstance,
    Trait,
)
from app.lib.session import sessionID_generate
from app.lib.log import LOG
from pfmongo.models.responseModel import mongodbResponse


# Context operation models
class ContextOperationModel(BaseModel):
    """
    Base model for context operations

    Attributes:
        status: Operation success status
        message: Detailed result message
        context_id: ID of the context
        timestamp: ISO format timestamp of the operation
    """

    status: bool = False
    message: str = ""
    context_id: str = ""
    timestamp: str = datetime.now().isoformat()


class ContextCreateModel(ContextOperationModel):
    """
    Result model for context creation operations

    Attributes:
        already_exists: Whether the context already existed
    """

    already_exists: bool = False


class ContextGetModel(BaseModel):
    """
    Result model for context get operations

    Attributes:
        context_id: Currently active context ID or empty string
        has_active: Whether there is an active context
        timestamp: ISO format timestamp of the operation
    """

    context_id: str = ""
    has_active: bool = False
    timestamp: str = datetime.now().isoformat()


class ContextListModel(BaseModel):
    """
    Result model for context list operations

    Attributes:
        status: Operation success status
        message: Detailed result message
        contexts: List of available context IDs
        active_context: Currently active context ID or empty string
        timestamp: ISO format timestamp of the operation
    """

    status: bool = False
    message: str = ""
    contexts: List[str] = []
    active_context: str = ""
    timestamp: str = datetime.now().isoformat()


class ContextDeleteModel(ContextOperationModel):
    """
    Result model for context delete operations

    Attributes:
        exists: Whether the context existed
        was_active: Whether the deleted context was active
    """

    exists: bool = False
    was_active: bool = False


class CAM:
    """Context Access Manager class (Singleton)

    Handles context operations including creation, listing, and
    selection. Maintains global context state for the REPL interface
    and manages MongoDB connections for context persistence.
    """

    # Singleton instance
    _instance: Optional["CAM"] = None

    # Class variables for global state
    context_active: Optional[str] = None
    context_collection: str = "contexts"

    def __new__(cls, *args: Any, **kwargs: Any) -> "CAM":
        """
        Ensure only one instance of CAM exists (Singleton pattern)

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            CAM: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(CAM, cls).__new__(cls)
        return cls._instance

    def __init__(self, context_id: Optional[str] = None) -> None:
        """
        Initialize CAM instance

        Args:
            context_id: Optional context ID to set as current
        """
        # Skip initialization if already done (singleton pattern)
        if hasattr(self, "initialized"):
            return

        if context_id:
            CAM.context_active = context_id

        self.initialized: bool = True

    async def collection_ensure(self) -> DatabaseCollectionModel:
        """
        Ensures the MongoDB collection for contexts exists and is accessible

        Connects to the contexts collection in the MongoDB database
        using mongodb_manager. Creates the collection if it doesn't exist.
        This method should be called before any operation that interacts
        with the contexts collection.

        Returns:
            DatabaseCollectionModel: Database connection model containing
                                    database and collection names with
                                    established connection
        """
        db_collection: DatabaseCollectionModel = db_manager.collection_resolve(
            self.context_collection
        )
        await db_manager.collection_connect(self.context_collection)
        return db_collection

    async def context_create(
        self, context_id: Optional[str] = None
    ) -> ContextCreateModel:
        """
        Create a new execution context in MongoDB

        Creates a new context with either the provided ID or a generated one.
        Also sets the newly created context as the active context for REPL
        and other operations. If a context with the provided ID already exists,
        the operation fails without modifying the active context.

        Args:
            context_id: Optional identifier for the context.
                       If None, a unique ID with "ctx" prefix is generated.

        Returns:
            ContextCreateModel: Result model containing:
                - status: Whether the operation succeeded
                - message: Description of the result
                - context_id: ID of the context (provided or generated)
                - already_exists: Whether the context ID already existed

        Notes:
            - Successful creation automatically sets the context as active
            - The context document contains start time and instance ID
        """
        result: ContextCreateModel = ContextCreateModel()

        await self.collection_ensure()

        # Generate ID if not provided
        if context_id is None:
            context_id = sessionID_generate("ctx")

        result.context_id = context_id

        # Check if context already exists
        exists: bool = await db_manager.document_exists(
            self.context_collection, context_id
        )

        if exists:
            result.already_exists = True
            result.message = f"Context already exists"
            return result

        # Create RuntimeInstance model
        runtime_instance: RuntimeInstance = RuntimeInstance(instance_id=context_id)
        context_data: dict = runtime_instance.model_dump()
        context_data["start_time"] = runtime_instance.start_time.isoformat()

        # Store in MongoDB
        response: mongodbResponse = await db_manager.document_add(
            self.context_collection, context_id, context_data
        )

        if response.status:
            # Set as active context
            CAM.context_active = context_id
            result.status = True
            result.message = "Context created successfully"
            return result
        else:
            result.message = f"Failed to create context: {response.message}"
            return result

    async def context_set(self, context_id: str) -> ContextOperationModel:
        """
        Set an existing context as the active REPL context

        Changes the active context to the specified ID if it exists.
        The active context is used by REPL operations and other parts
        of the application that depend on context. This operation only
        succeeds if the context exists in the database.

        Args:
            context_id: Identifier of the context to activate.
                      Must exist in the database.

        Returns:
            ContextOperationModel: Result model containing:
                - status: Whether the operation succeeded
                - message: Description of the result
                - context_id: ID of the requested context
                - timestamp: ISO format timestamp of when the operation occurred

        Notes:
            - If the context doesn't exist, the active context remains unchanged
            - This operation only updates in-memory state and doesn't modify the database
        """
        result: ContextOperationModel = ContextOperationModel(context_id=context_id)

        await self.collection_ensure()

        # Check if context exists
        exists: bool = await db_manager.document_exists(
            self.context_collection, context_id
        )

        if not exists:
            result.message = "Context does not exist"
            return result

        # Update active context
        CAM.context_active = context_id
        result.status = True
        result.message = "Context set as active"
        return result

    def context_get(self) -> ContextGetModel:
        """
        Get the currently active context ID

        Retrieves information about the current active context
        without modifying any state. This operation always succeeds
        but may indicate that no active context is set.

        Returns:
            ContextGetModel: Model containing:
                - context_id: Currently active context ID or empty string if none
                - has_active: Boolean indicating whether an active context exists

        Notes:
            - Returns empty context_id with has_active=False when no context is active
            - Operation is synchronous as it only reads in-memory state
        """
        result: ContextGetModel = ContextGetModel()

        if CAM.context_active:
            result.context_id = CAM.context_active
            result.has_active = True

        return result

    def context_revoke(self) -> ContextGetModel:
        """
        Clear the active REPL context

        Revokes the currently active context by setting it to None.
        This operation always succeeds, even if no context is currently
        active. After this operation, no context will be active until
        context_set() is called.

        Returns:
            ContextGetModel: Model reflecting the cleared state:
                - context_id: Empty string
                - has_active: Always False

        Notes:
            - Safe to call even when no context is active
            - Only affects in-memory state, doesn't modify the database
            - The previously active context still exists in the database
        """
        # Store previous state for the result
        had_active: bool = CAM.context_active is not None
        previous_context: str = CAM.context_active or ""

        # Clear the active context
        CAM.context_active = None

        # Return empty context model
        return ContextGetModel(context_id="", has_active=False)

    async def contexts_list(self) -> ContextListModel:
        """
        List all available execution contexts in the database

        Retrieves a list of all context IDs stored in the MongoDB collection.
        Also includes information about which context is currently active.
        This operation may fail if the database connection cannot be established.

        Returns:
            ContextListModel: Model containing:
                - status: Whether the operation succeeded
                - message: Description of the result
                - contexts: List of available context IDs
                - active_context: Currently active context ID or empty string

        Notes:
            - Empty list is returned if no contexts exist
            - The active_context field reflects the current in-memory state
            - A failed operation will have empty contexts list but may still
              correctly report the active context
        """
        result: ContextListModel = ContextListModel(
            active_context=CAM.context_active or ""
        )

        await self.collection_ensure()

        # Get all documents in the collection
        response: mongodbResponse = await db_manager.documents_getAll(
            self.context_collection
        )

        if not response.status or not response.response:
            result.message = "No contexts found"
            return result

        # Parse the response
        contexts: List[str] = ast.literal_eval(response.message)
        result.contexts = contexts
        result.status = True
        result.message = f"Found {len(contexts)} contexts"
        return result

    async def context_delete(self, context_id: str) -> ContextDeleteModel:
        """
        Delete an execution context from the database

        Permanently removes a context from the MongoDB collection.
        If the deleted context is currently active, the active context
        is cleared. This operation may fail if the context doesn't exist
        or the database operation fails.

        Args:
            context_id: Identifier of the context to delete

        Returns:
            ContextDeleteModel: Result model containing:
                - status: Whether the delete operation succeeded
                - message: Description of the result
                - context_id: ID of the context that was to be deleted
                - exists: Whether the context existed before the operation
                - was_active: Whether the deleted context was active

        Notes:
            - If the context was active, active context is set to None
            - Context is completely removed from the database
            - Operation fails if the context doesn't exist
            - All documents related to this context are permanently deleted
        """
        result: ContextDeleteModel = ContextDeleteModel(context_id=context_id)

        await self.collection_ensure()

        # Check if context exists
        exists: bool = await db_manager.document_exists(
            self.context_collection, context_id
        )

        result.exists = exists

        if not exists:
            result.message = "Context does not exist"
            return result

        # Check if this is the active context
        result.was_active = CAM.context_active == context_id

        # Delete the context
        response: mongodbResponse = await db_manager.document_delete(
            self.context_collection, context_id
        )

        if response.status:
            # Clear active context if it was deleted
            if result.was_active:
                CAM.context_active = None

            result.status = True
            result.message = "Context deleted successfully"
            return result
        else:
            result.message = f"Failed to delete context: {response.message}"
            return result


# Create singleton instance
contextAccessManager = CAM()


@click.group(
    cls=RichGroup,
    short_help="Manage execution contexts",
    help="""Context Management

    Commands to create, list, and manage execution contexts.
    """,
)
def context() -> None:
    """Root group for context-related commands."""
    pass


@context.command(
    cls=RichCommand,
    short_help="Create a new execution context",
    help=rich_help(
        command="create",
        description="Create a new named execution context. If no ID is provided, one is generated automatically.",
        usage="/context create [<context_id>]",
        args={
            "<context_id>": "Optional identifier for the context (auto-generated if omitted)"
        },
    ),
)
@click.argument("context_id", required=False, type=str)
async def create(context_id: Optional[str] = None) -> None:
    """Creates a new execution context in MongoDB, generating an ID if omitted."""
    result: ContextCreateModel = await contextAccessManager.context_create(context_id)

    if result.already_exists:
        console.print(
            f"[bold red]Error: Context '{result.context_id}' already exists.[/bold red]"
        )
        return

    if not result.status:
        console.print(f"[bold red]Error: {result.message}.[/bold red]")
        return

    console.print(
        f"[bold green]Context '{result.context_id}' created and set as active.[/bold green]"
    )


@context.command(
    cls=RichCommand,
    short_help="Set the active REPL context",
    help=rich_help(
        command="set",
        description="Set the active execution context.",
        usage="/context set <context_id>",
        args={"<context_id>": "Existing context to activate"},
    ),
)
@click.argument("context_id", type=str)
async def set(context_id: str) -> None:
    """Sets an existing context as the active REPL context."""
    result: ContextOperationModel = await contextAccessManager.context_set(context_id)

    if not result.status:
        console.print(
            f"[bold red]Error: Context '{result.context_id}' does not exist.[/bold red]"
        )
        return

    console.print(
        f"[bold green]Context '{result.context_id}' set as active.[/bold green]"
    )


@context.command(
    cls=RichCommand,
    short_help="Retrieve the active REPL context",
    help=rich_help(
        command="get",
        description="Retrieve the active execution context.",
        usage="/context get",
        args={"<None>": "No arguments"},
    ),
)
async def get() -> None:
    """Retrieves the currently active REPL context."""
    result: ContextGetModel = contextAccessManager.context_get()

    active_context: str = result.context_id if result.has_active else "None"
    console.print(f"[bold green]Active context: {active_context}[/bold green]")


@context.command(
    cls=RichCommand,
    short_help="Clear the active REPL context",
    help=rich_help(
        command="revoke",
        description="Clear the currently active execution context.",
        usage="/context revoke",
        args={"<None>": "No arguments"},
    ),
)
async def revoke() -> None:
    """Clears the active REPL context."""
    contextAccessManager.context_revoke()
    console.print("[bold green]REPL context cleared.[/bold green]")


@context.command(
    cls=RichCommand,
    short_help="List all available contexts",
    help=rich_help(
        command="list",
        description="List all available execution contexts.",
        usage="/context list",
        args={"<None>": "No arguments"},
    ),
)
async def list() -> None:
    """Lists all stored execution contexts in MongoDB."""
    result: ContextListModel = await contextAccessManager.contexts_list()

    if not result.status or not result.contexts:
        console.print("[bold yellow]No contexts found.[/bold yellow]")
        return

    for ctx_id in result.contexts:
        status: str = "active" if ctx_id == result.active_context else "available"
        console.print(f"- [bold cyan]{ctx_id}[/bold cyan] ({status})")


@context.command(
    cls=RichCommand,
    short_help="Delete a context",
    help=rich_help(
        command="delete",
        description="Delete an execution context from MongoDB.",
        usage="/context delete <context_id>",
        args={"<context_id>": "Context ID to delete"},
    ),
)
@click.argument("context_id", type=str)
async def delete(context_id: str) -> None:
    """Deletes an execution context from MongoDB."""
    result: ContextDeleteModel = await contextAccessManager.context_delete(context_id)

    if not result.exists:
        console.print(
            f"[bold red]Error: Context '{result.context_id}' does not exist.[/bold red]"
        )
        return

    if not result.status:
        console.print(f"[bold red]Error: {result.message}.[/bold red]")
        return

    console.print(
        f"[bold green]Context '{result.context_id}' deleted successfully.[/bold green]"
    )

    if result.was_active:
        console.print(
            "[bold yellow]Note: The active context was cleared.[/bold yellow]"
        )
