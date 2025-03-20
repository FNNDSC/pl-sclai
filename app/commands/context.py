"""
Context Management Commands

Provides CLI commands for managing execution contexts.

MongoDB Structure:
- Database: `rootDB.core`
- Collection: `contexts`
  - Documents store execution session metadata.

Commands:
- /context create [<context_id>]: Create a new context (auto-generates if omitted).
- /context set <context_id>: Set the active REPL context.
- /context get: Retrieve the active REPL context.
- /context revoke: Clear the active REPL context.
- /context list: List all stored contexts.
"""

from typing import Optional, List
import click
import ast
from app.commands.base import RichGroup, RichCommand, rich_help
from app.config.settings import collections, console, rootDB
from app.lib.mongodb import db_init, db_docAdd, db_contains, db_showAll, db_docDel
from app.models.dataModel import (
    DocumentData,
    DatabaseCollectionModel,
    RuntimeInstance,
    Trait,
)
from app.lib.session import sessionID_generate
from app.lib.log import LOG
from pfmongo.models.responseModel import mongodbResponse
import pudb

# Global REPL state
active_context: Optional[str] = None

# MongoDB config
DB_NAME: str = rootDB.core
COLLECTION_NAME: str = "contexts"


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


async def _ensure_context_collection() -> DatabaseCollectionModel:
    """
    Ensures the MongoDB collection exists for storing contexts.

    :return: DatabaseCollectionModel containing database and collection names.
    """
    db_collection: DatabaseCollectionModel = DatabaseCollectionModel(
        database=DB_NAME, collection=COLLECTION_NAME
    )
    await db_init(db_collection)
    return db_collection


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
    global active_context
    await _ensure_context_collection()

    if context_id is None:
        context_id: str = sessionID_generate(
            "ctx"
        )  # Generates a unique session ID with "ctx" prefix

    result: mongodbResponse = await db_contains(context_id)
    if result.status:
        console.print(
            f"[bold red]Error: Context '{context_id}' already exists.[/bold red]"
        )
        return

    # Store as a `RuntimeInstance` model
    runtime_instance: RuntimeInstance = RuntimeInstance(instance_id=context_id)
    context_data: dict = runtime_instance.model_dump()
    context_data["start_time"] = (
        runtime_instance.start_time.isoformat()
    )  # Convert datetime to string

    response: mongodbResponse = await db_docAdd(
        DocumentData(data=context_data, id=context_id)
    )

    if response.status:
        active_context = context_id
        console.print(
            f"[bold green]Context '{context_id}' created and set as active.[/bold green]"
        )
    else:
        console.print(
            f"[bold red]Error: Failed to create context '{context_id}'.[/bold red]"
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
    global active_context
    await _ensure_context_collection()

    result: mongodbResponse = await db_contains(context_id)
    if not result.status:
        console.print(
            f"[bold red]Error: Context '{context_id}' does not exist.[/bold red]"
        )
        return

    active_context = context_id
    console.print(f"[bold green]Context '{context_id}' set as active.[/bold green]")


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
    console.print(
        f"[bold green]Active context: {active_context if active_context else 'None'}[/bold green]"
    )


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
    global active_context
    active_context = None
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
    await _ensure_context_collection()

    result: mongodbResponse = await db_showAll()
    if not result.status or not result.response:
        console.print("[bold yellow]No contexts found.[/bold yellow]")
        return

    l_result: List[str] = ast.literal_eval(result.message)
    for ctx_id in l_result:
        status: str = "active" if ctx_id == active_context else "available"
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
    await _ensure_context_collection()

    result: mongodbResponse = await db_contains(context_id)
    if not result.status:
        console.print(
            f"[bold red]Error: Context '{context_id}' does not exist.[/bold red]"
        )
        return

    response: mongodbResponse = await db_docDel(DocumentData(data={}, id=context_id))
    if response.status:
        global active_context
        if active_context == context_id:
            active_context = None
        console.print(
            f"[bold green]Context '{context_id}' deleted successfully.[/bold green]"
        )
    else:
        console.print(
            f"[bold red]Error: Failed to delete context '{context_id}'.[/bold red]"
        )
