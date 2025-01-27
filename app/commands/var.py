"""
Variable Management Commands

This module provides CLI commands for managing user-defined variables
stored in MongoDB. Variables can be set, echoed, listed, or deleted.

Commands:
- /var set <name> <value>: Set a variable.
- /var show <name>: Show a variable's value.
- /var showall: List all variables.
- /var delete <name>: Delete a variable.
"""

from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand
from app.lib.mongodb import db_init, db_docAdd, db_contains, db_docDel, db_showAll
from app.models.dataModel import DocumentData, DatabaseCollectionModel, DbInitResult
from app.lib.log import LOG
from pfmongo.models.responseModel import mongodbResponse
import json

console: Console = Console()


def rich_help(command: str, description: str, usage: str, args: dict) -> str:
    """
    Generate Rich-enhanced help text for commands.

    :param command: The command name.
    :param description: Description of the command.
    :param usage: Usage syntax for the command.
    :param args: Dictionary of arguments and their descriptions.
    :return: Formatted Rich help string.
    """
    help_text = f"[bold cyan]{description}[/bold cyan]\n\n"
    help_text += f"[bold yellow]Usage:[/bold yellow]\n    [green]{usage}[/green]\n\n"
    help_text += "[bold yellow]Arguments:[/bold yellow]\n"
    for arg, desc in args.items():
        help_text += f"    [green]{arg}[/green]: {desc}\n"
    return help_text


@click.group(
    cls=RichGroup,
    short_help="Manage variables",
    help="""
    Variable Management

    Commands to manage user-defined variables.
    """,
)
def var() -> None:
    """
    Root group for variable-related commands.
    """
    pass


async def _ensure_connection() -> DatabaseCollectionModel:
    """
    Ensures a connection to the MongoDB database and collection for variables.

    :return: DatabaseCollectionModel containing database and collection names.
    :raises RuntimeError: If the database or collection initialization fails.
    """
    db_collection: DatabaseCollectionModel = DatabaseCollectionModel(
        database="claimm", collection="vars"
    )

    result: DbInitResult = await db_init(db_collection)

    if not result.db_response.status or not result.col_response.status:
        raise RuntimeError(
            f"Failed to initialize MongoDB: {result.db_response.message}, {result.col_response.message}"
        )

    return db_collection


var: click.Group = var


@var.command(
    cls=RichCommand,
    help=rich_help(
        command="set",
        description="Set a user-defined variable.",
        usage="/var set <name> <value>",
        args={
            "<name>": "The name of the variable to set.",
            "<value>": "The value to assign to the variable.",
        },
    ),
)
@click.argument("name", type=str)
@click.argument("value", type=str)
async def set(name: str, value: str) -> None:
    """
    Sets a variable in the MongoDB collection.

    :param name: The name of the variable.
    :param value: The value of the variable.
    """
    try:
        await _ensure_connection()
        document_data: DocumentData = DocumentData(
            data={"name": name, "value": value}, id=name
        )
        result: mongodbResponse = await db_docAdd(document_data)

        if result.status:
            console.print(
                f"[bold green]Variable '{name}' set successfully.[/bold green]"
            )
        else:
            console.print(
                f"[bold red]Failed to set variable: {result.message}[/bold red]"
            )
    except Exception as e:
        LOG(f"Error setting variable '{name}': {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")


@var.command(
    cls=RichCommand,
    help=rich_help(
        command="show",
        description="Show the value of a user-defined variable.",
        usage="/var show <name>",
        args={
            "<name>": "The name of the variable to show.",
        },
    ),
)
@click.argument("name", type=str)
async def show(name: str) -> None:
    """
    Show a variable's value from the MongoDB collection.

    :param name: The name of the variable to show.
    """
    try:
        await _ensure_connection()
        result: mongodbResponse = await db_contains(name)

        if result.status:
            try:
                message_data = json.loads(result.message)
                value: str = message_data.get("value", result.message)
                console.print(f"[bold cyan]{name}:[/bold cyan] {value}")
            except json.JSONDecodeError:
                console.print(
                    f"[bold red]Error: Unable to decode response for variable '{name}'.[/bold red]"
                )
        else:
            console.print(
                f"[bold red]Variable '{name}' not found: {result.message}[/bold red]"
            )
    except Exception as e:
        LOG(f"Error showing variable '{name}': {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")


@var.command(
    cls=RichCommand,
    help=rich_help(
        command="showall",
        description="Show a list of all user-defined variables.",
        usage="/var showall",
        args={},
    ),
)
async def showall() -> None:
    """
    Displays all variables in the MongoDB collection.
    """
    try:
        await _ensure_connection()
        result: mongodbResponse = await db_showAll()

        if result.status:
            console.print(f"[bold yellow]All variables:[/bold yellow] {result.message}")
        else:
            console.print(
                f"[bold red]Failed to retrieve variables: {result.message}[/bold red]"
            )
    except Exception as e:
        LOG(f"Error showing all variables: {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")


@var.command(
    cls=RichCommand,
    help=rich_help(
        command="delete",
        description="Delete a user-defined variable.",
        usage="/var delete <name>",
        args={
            "<name>": "The name of the variable to delete.",
        },
    ),
)
@click.argument("name", type=str)
async def delete(name: str) -> None:
    """
    Deletes a variable from the MongoDB collection.

    :param name: The name of the variable to delete.
    """
    try:
        await _ensure_connection()
        document_data: DocumentData = DocumentData(data={}, id=name)
        result: mongodbResponse = await db_docDel(document_data)

        if result.status:
            console.print(
                f"[bold green]Variable '{name}' deleted successfully.[/bold green]"
            )
        else:
            console.print(
                f"[bold red]Failed to delete variable: {result.message}[/bold red]"
            )
    except Exception as e:
        LOG(f"Error deleting variable '{name}': {e}")
        console.print(f"[bold red]Error: {e}[/bold red]")
