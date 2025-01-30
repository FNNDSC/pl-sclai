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
from app.commands.base import RichGroup, RichCommand, rich_help
from app.lib.mongodb import db_init, db_docAdd, db_contains, db_docDel, db_showAll
from app.models.dataModel import DocumentData, DatabaseCollectionModel, DbInitResult
from app.lib.log import LOG
from pfmongo.models.responseModel import mongodbResponse
import json

console: Console = Console()


@click.group(
    cls=RichGroup,
    short_help="fortune teller",
    help="""
    fortune 

    Yes. A fortune teller.
    """,
)
def fortune() -> None:
    """
    Root group for variable-related commands.
    """
    pass




ftn: click.Group = ftn 


@var.command(
    cls=RichCommand,
    help=rich_help(
        command="set",
        description="Set a user-defined variable.",
        usage="/var set <name> <value>",
        args={
            "<None>:
            "<name>": "The name of the variable to set.",
            "<value>": "The value to assign to the variable.",
        },
    ),
)
async def tell() -> None:
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
