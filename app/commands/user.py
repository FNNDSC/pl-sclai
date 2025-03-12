"""
User Management Commands

This module provides CLI commands for managing user authentication and session context.
It allows users to create an account, log in, and manage session context.

MongoDB Structure:
- Database: `users`
- Collection per user (e.g., `alice`)
  - `password.json`: Stores plaintext password (for now).
  - `context.json`: Tracks active LLM & session ID.

Commands:
- /user create: Create a new user.
- /user login <name>: Log in as a user.
- /user context get: Retrieve the user's active session context.
- /user context set <llm> <session_id>: Set the active session context.
"""

from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand, rich_help
from app.lib.router import Router, router, accessor_handle
from app.lib.handlers import UserLLMSessionHandler
from app.lib.mongodb import db_init, db_docAdd, db_contains
from app.models.dataModel import (
    DocumentData,
    DatabaseCollectionModel,
    Accessor,
    ProviderModel,
    Trait,
    RouteMapperModel,
)
from app.config.settings import collections, console
from app.lib.log import LOG
import getpass
import json
import pudb


current_user: str = ""  # Stores logged-in user globally
user_providers: dict[str, ProviderModel] = {}


@click.group(
    cls=RichGroup,
    short_help="Manage users",
    help="""User Management

    Commands to create and log in users.
    """,
)
def user() -> None:
    """
    Root group for user-related commands.
    """
    pass


async def _ensure_user_collection(username: str) -> DatabaseCollectionModel | None:
    """
    Ensures the user collection exists in MongoDB.

    :param username: The username to create a collection for.
    :return: DatabaseCollectionModel containing database and collection names.
    """
    db_collection: DatabaseCollectionModel | None = collections.dbcollection_resolve(
        username
    )
    if not db_collection:
        return None
    await db_init(db_collection)
    return db_collection


def register_provider_commands(provider: ProviderModel, cli: click.Group) -> None:
    """Register dynamic commands based on username

    Creates command group and subcommands for provider:
    - session get: get session info
    - session set: set session info

    Args:
        provider: Provider instance to register commands for
        cli: Click command group to register commands with

    Note:
        Commands are registered with root CLI group
        Help text available at each command level
    """

    @click.group(
        cls=RichGroup,
        short_help=f"{provider.name} specific commands",
        help=f"""
        {provider.name.upper()} Provider Commands
        Manage {provider.name} session
        """,
    )
    def provider_group() -> None:
        """Command group for managing {provider.name} provider."""
        pass

    @provider_group.group(
        cls=RichGroup,
        short_help=f"Handle session info for {provider.name}",
        help=f"""
        Session management 
        get or set session info for {provider.name}
        """,
    )
    def session() -> None:
        """Manage session configuration."""
        pass

    @session.command(
        cls=RichCommand,
        short_help="Get session info",
        help=rich_help(
            command="get",
            description=f"Display current session info for {provider.name}",
            usage=f"/{provider.name} session get",
            args={"<None>": "no arguments"},
        ),
    )
    async def get() -> str:
        """Show current session data."""
        # pudb.set_trace()
        value: str = await provider.commands[Accessor.GET.value](
            provider.name, Accessor.GET, Trait.SESSION, None, "Session detail for"
        )
        return value

    @session.command(
        cls=RichCommand,
        short_help="Set the user session",
        help=rich_help(
            command="set",
            description=f"Set the session for {provider.name}",
            usage=f"/{provider.name} session set <value>",
            args={"<value>": "session to store"},
        ),
    )
    @click.argument("value", type=str)
    async def set(value: str) -> str:
        """Set session value."""
        # pudb.set_trace()
        set: str = await provider.commands[Accessor.SET.value](
            provider.name, Accessor.SET, Trait.SESSION, value, "Session detail for"
        )
        return set

    cli.add_command(provider_group, name=provider.name)


@user.command(
    cls=RichCommand,
    short_help="Create a new user",
    help=rich_help(
        command="create",
        description="Create a new user account",
        usage="/user create",
        args={"<None>": "No arguments"},
    ),
)
async def create() -> None:
    """
    Creates a new user by prompting for a username and password.
    """
    global current_user
    username = input("Enter username: ").strip()
    if not username:
        console.print("[bold red]Error: Username cannot be empty.[/bold red]")
        return

    password = getpass.getpass("Enter password: ").strip()
    if not password:
        console.print("[bold red]Error: Password cannot be empty.[/bold red]")
        return

    # Ensure user collection exists
    await _ensure_user_collection(username)

    # Check if password.json already exists
    result = await db_contains("password.json")
    if result.status:
        console.print(f"[bold red]Error: User '{username}' already exists.[/bold red]")
        return

    # Store password (plaintext for now)
    password_doc = {"password": password}
    await db_docAdd(DocumentData(data=password_doc, id="password.json"))

    # Create empty session.json
    context_doc = {"llm": None, "active_session": None}
    await db_docAdd(DocumentData(data=context_doc, id="session.json"))

    console.print(
        f"[bold green]User [yellow]{username}[/yellow] created successfully.[/bold green]"
    )


def dynamicRouting_set(user: str) -> ProviderModel | None:
    provider: ProviderModel = ProviderModel(
        name=user,
        commands={
            Accessor.GET.value: accessor_handle,
            Accessor.SET.value: accessor_handle,
        },
    )
    user_providers[user] = provider
    userLLMSessionHandler: UserLLMSessionHandler = UserLLMSessionHandler(
        user, Trait.SESSION
    )
    try:
        router.register(user, Trait.SESSION, userLLMSessionHandler)
    except Exception as e:
        console.print(
            f"[green]It seems [yellow]{user}[/yellow] is already logged in.[/green]"
        )
        return None
    return provider


@user.command(
    cls=RichCommand,
    short_help="Log in as a user",
    help=rich_help(
        command="login",
        description="Log in to an existing user account",
        usage="/user login <name>",
        args={"<name>": "Username to log in"},
    ),
)
@click.argument("name", type=str)
@click.pass_context
async def login(ctx: click.Context, name: str) -> None:
    """
    Logs in a user by verifying the password.

    :param name: The username.
    """
    global current_user

    await _ensure_user_collection(name)

    password = getpass.getpass("Enter password: ").strip()
    result = await db_contains("password.json")

    if not result.status:
        console.print(f"[bold red]Error: User '{name}' does not exist.[/bold red]")
        console.print("Please create first with [yellow]/user create[/yellow]")
        return

    try:
        stored_data = json.loads(result.message)
        if stored_data["password"] == password:
            current_user = name  # Set global user
            console.print(
                f"[bold green]Login successful! Welcome, {name}.[/bold green]"
            )
        else:
            console.print("[bold red]Error: Incorrect password.[/bold red]")
    except json.JSONDecodeError:
        console.print("[bold red]Error: Failed to read user data.[/bold red]")
    cmdName: str = f"user:{name}"
    provider: ProviderModel | None = dynamicRouting_set(cmdName)
    if provider:
        if "cli" in ctx.obj:
            register_provider_commands(provider, ctx.obj["cli"])
