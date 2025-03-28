"""
User Management Commands

This module provides CLI commands for managing user authentication and session context.
It allows users to create an account, log in, and manage session context.

MongoDB Structure:
- Core Database (`tame`):
  - `auth`: Stores user authentication tokens
    - `<authtoken>-auth.json`: Login information for a user session

- Users Database (`users`):
  - Collection per user (e.g., `alice`)
    - `password.json`: Stores plaintext password (for now)
    - `session.json`: Tracks active LLM & session ID
    - `auth.json`: Authentication details

Commands:
- /user create: Create a new user
- /user login <name>: Log in as a user
- /user:<name> session get: Retrieve the user's active session context
- /user:<name> session set <llm> <session_id>: Set the active session context
- /user:<name> auth get: Retrieve the user's authentication details
- /user:<name> auth set <value>: Set the user's authentication details
"""

from click.parser import normalize_opt
import click
from app.commands.base import RichGroup, RichCommand, rich_help
from app.lib.router import Router, router, accessor_handle
from app.lib.handlers import UserLLMSessionHandler, UserAuthHandler
from app.lib.mongodb_manager import db_manager, std_documents, core_collections
from app.models.dataModel import (
    DocumentData,
    DatabaseCollectionModel,
    Accessor,
    ProviderModel,
    Trait,
    RouteMapperModel,
    UserCreateModel,
    UserLoginModel,
)
from pfmongo.models.responseModel import mongodbResponse
from app.config.settings import console
from app.lib.log import LOG
from app.lib.session import sessionID_generate
from typing import Optional, Any, cast, Dict, List, Callable
import getpass
import json
import datetime
import functools
import pudb

# Global state for user providers
user_providers: Dict[str, ProviderModel] = {}


class UAM:
    """
    User Account Management class (Singleton)

    Handles user authentication operations including creation, login,
    and MongoDB connections. Maintains global user state through
    class variables for the REPL interface.
    """

    # Singleton instance
    _instance: Optional["UAM"] = None

    # Class variables for global state
    user_current: str = ""
    user_loggedIn: bool = False
    user_providers: Dict[str, ProviderModel] = {}
    passwordFileName: str = std_documents.PASSWORD

    def __new__(cls, *args: Any, **kwargs: Any) -> "UAM":
        """
        Ensure only one instance of UAM exists (Singleton pattern)

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            UAM: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(UAM, cls).__new__(cls)
        return cls._instance

    def __init__(self, username: Optional[str] = None) -> None:
        """
        Initialize UAM instance

        Args:
            username: Optional username to set as current user
        """
        # Skip initialization if already done (singleton pattern)
        if hasattr(self, "initialized"):
            return

        if username:
            UAM.user_current = username

        self.initialized: bool = True

    async def collection_connect(
        self, username: str
    ) -> Optional[DatabaseCollectionModel]:
        """
        Ensures the user collection exists in MongoDB

        Args:
            username: The username to create a collection for

        Returns:
            DatabaseCollectionModel containing database and collection names,
            or None if the collection could not be resolved
        """
        try:
            return await db_manager.collection_connect(username)
        except Exception as e:
            LOG(f"Error connecting to user collection: {e}")
            return None

    async def user_create(self, username: str, password: str) -> UserCreateModel:
        """
        Create a new user account

        Args:
            username: Username for the new account
            password: Password for the new account

        Returns:
            UserCreateModel with creation status information
        """
        userCreate: UserCreateModel = UserCreateModel(
            status=False, message="", username=username, alreadyExists=False
        )

        # Check if user exists
        try:
            exists: bool = await db_manager.document_exists(
                username, self.passwordFileName
            )
            if exists:
                userCreate.alreadyExists = True
                userCreate.message = "User already exists."
                return userCreate

            # Create user
            password_doc: Dict[str, str] = {"password": password}
            result: mongodbResponse = await db_manager.document_add(
                username, self.passwordFileName, password_doc
            )

            if result.status:
                userCreate.status = True
                userCreate.message = "User created successfully."
            else:
                userCreate.message = f"Error creating user: {result.message}"

        except Exception as e:
            userCreate.message = f"Error during user creation: {str(e)}"

        return userCreate

    async def user_login(self, username: str, password: str) -> UserLoginModel:
        """
        Log in a user by verifying credentials

        Args:
            username: Username to log in
            password: Password to verify

        Returns:
            UserLoginModel with login status, auth token and messages
        """
        current_time: str = datetime.datetime.now().isoformat()

        loginModel: UserLoginModel = UserLoginModel(
            status=False, message="", username=username, auth="", timestamp=current_time
        )

        try:
            # Get password document
            passwordValue: mongodbResponse = await db_manager.document_get(
                username, self.passwordFileName
            )

            if not passwordValue.status:
                loginModel.message = "User does not exist."
                return loginModel

            # Verify password
            stored_data: Dict[str, str] = json.loads(passwordValue.message)
            if stored_data["password"] == password:
                # Generate auth token and update model
                auth_token: str = sessionID_generate("auth")
                loginModel.auth = auth_token
                loginModel.message = "Login successful."
                loginModel.status = True

                # Update global state
                UAM.user_current = username
                UAM.user_loggedIn = True

                # Store auth token in auth collection
                await db_manager.document_add(
                    core_collections.AUTH,
                    auth_token,
                    loginModel.model_dump(),  # Convert Pydantic model to dict
                )
            else:
                loginModel.message = "Incorrect password."

        except json.JSONDecodeError:
            loginModel.message = "Failed to decode password data."
        except Exception as e:
            loginModel.message = f"Error during login: {str(e)}"

        return loginModel

    async def user_logout(self) -> bool:
        """
        Log out the current user

        Invalidates the current user session and resets global state.

        Returns:
            bool: True if logout was successful
        """
        if not UAM.user_loggedIn:
            return False

        UAM.user_current = ""
        UAM.user_loggedIn = False
        return True

    @property
    def current_user(self) -> str:
        """
        Get the current logged-in username

        Returns:
            str: Current username or empty string if not logged in
        """
        return UAM.user_current

    @property
    def is_logged_in(self) -> bool:
        """
        Check if a user is currently logged in

        Returns:
            bool: True if a user is logged in
        """
        return UAM.user_loggedIn


# Create a singleton instance with no username parameter
userAccessModule = UAM()


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


def register_provider_commands(provider: ProviderModel, cli: click.Group) -> None:
    """
    Register dynamic commands based on username

    Args:
        provider: Provider instance to register commands for
        cli: Click command group to register commands with
    """
    # First, create the provider group
    provider_group = RichGroup(name=provider.name)
    provider_group.help = (
        f"{provider.name.upper()} Provider Commands\nManage {provider.name} settings"
    )
    provider_group.short_help = f"{provider.name} specific commands"

    # Add provider group to CLI
    cli.add_command(provider_group)

    # Define commands for each trait
    for trait, trait_name in [(Trait.SESSION, "session"), (Trait.AUTH, "auth")]:
        # Create trait group
        trait_group = RichGroup(name=trait_name)
        trait_group.help = (
            f"{trait_name.capitalize()} management\nGet or set {trait_name}"
        )
        trait_group.short_help = f"Handle {trait_name} info for {provider.name}"

        # Add trait group to provider group
        provider_group.add_command(trait_group)

        # Create get command for this trait
        async def get_callback(trait=trait, trait_name=trait_name):
            """Get current value."""
            value = await provider.commands[Accessor.GET.value](
                provider.name,
                Accessor.GET,
                trait,
                None,
                f"{trait_name.capitalize()} detail for",
            )
            return value

        get_cmd = RichCommand(
            name="get",
            callback=get_callback,
            help=rich_help(
                command="get",
                description=f"Display current {trait_name} info for {provider.name}",
                usage=f"/{provider.name} {trait_name} get",
                args={"<None>": "no arguments"},
            ),
            short_help=f"Get {trait_name} info",
        )

        # Create set command for this trait
        async def set_callback(value, trait=trait, trait_name=trait_name):
            """Set new value."""
            result = await provider.commands[Accessor.SET.value](
                provider.name,
                Accessor.SET,
                trait,
                value,
                f"{trait_name.capitalize()} detail for",
            )
            return result

        set_cmd = RichCommand(
            name="set",
            callback=set_callback,
            params=[click.Argument(["value"])],
            help=rich_help(
                command="set",
                description=f"Set the {trait_name} for {provider.name}",
                usage=f"/{provider.name} {trait_name} set <value>",
                args={"<value>": f"{trait_name} to store"},
            ),
            short_help=f"Set {trait_name} value",
        )

        # Add commands to trait group
        trait_group.add_command(get_cmd)
        trait_group.add_command(set_cmd)


# def register_provider_commands(provider: ProviderModel, cli: click.Group) -> None:
#     """
#     Register dynamic commands based on username
#
#     Args:
#         provider: Provider instance to register commands for
#         cli: Click command group to register commands with
#     """
#     # First, create the provider group
#     provider_group = click.Group(name=provider.name)
#     provider_group.help = (
#         f"{provider.name.upper()} Provider Commands\nManage {provider.name} settings"
#     )
#     provider_group.short_help = f"{provider.name} specific commands"
#
#     # Add provider group to CLI
#     cli.add_command(provider_group)
#
#     # Define commands for each trait
#     for trait, trait_name in [(Trait.SESSION, "session"), (Trait.AUTH, "auth")]:
#         # Create trait group
#         trait_group = click.Group(name=trait_name)
#         trait_group.help = (
#             f"{trait_name.capitalize()} management\nGet or set {trait_name}"
#         )
#         trait_group.short_help = f"Handle {trait_name} info for {provider.name}"
#
#         # Add trait group to provider group
#         provider_group.add_command(trait_group)
#
#         # Create get command for this trait
#         async def get_callback(trait=trait, trait_name=trait_name):
#             """Get current value."""
#             value = await provider.commands[Accessor.GET.value](
#                 provider.name,
#                 Accessor.GET,
#                 trait,
#                 None,
#                 f"{trait_name.capitalize()} detail for",
#             )
#             return value
#
#         get_cmd = click.Command(
#             name="get", callback=get_callback, help=f"Get {trait_name} info"
#         )
#
#         # Create set command for this trait
#         async def set_callback(value, trait=trait, trait_name=trait_name):
#             """Set new value."""
#             result = await provider.commands[Accessor.SET.value](
#                 provider.name,
#                 Accessor.SET,
#                 trait,
#                 value,
#                 f"{trait_name.capitalize()} detail for",
#             )
#             return result
#
#         set_cmd = click.Command(
#             name="set",
#             callback=set_callback,
#             params=[click.Argument(["value"])],
#             help=f"Set {trait_name} value",
#         )
#
#         # Add commands to trait group
#         trait_group.add_command(get_cmd)
#         trait_group.add_command(set_cmd)


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
    username: str = input("Enter username: ").strip()
    if not username:
        console.print("[bold red]Error: Username cannot be empty.[/bold red]")
        return

    password: str = getpass.getpass("Enter password: ").strip()
    if not password:
        console.print("[bold red]Error: Password cannot be empty.[/bold red]")
        return

    # Use UAM singleton to create user
    result: UserCreateModel = await userAccessModule.user_create(username, password)

    if result.alreadyExists:
        console.print(f"[bold red]Error: User '{username}' already exists.[/bold red]")
        return

    if not result.status:
        console.print(f"[bold red]Error: {result.message}[/bold red]")
        return

    console.print(
        f"[bold green]User [yellow]{username}[/yellow] created successfully.[/bold green]"
    )


def dynamicRouting_set(user: str) -> Optional[ProviderModel]:
    """
    Set up dynamic routing for a user

    Creates provider model and registers handlers for different traits.

    Args:
        user: Username for dynamic routing

    Returns:
        ProviderModel or None if registration failed
    """
    provider: ProviderModel = ProviderModel(
        name=user,
        commands={
            Accessor.GET.value: accessor_handle,
            Accessor.SET.value: accessor_handle,
        },
    )
    user_providers[user] = provider

    # Create handlers for different traits
    userLLMSessionHandler: UserLLMSessionHandler = UserLLMSessionHandler(
        user, Trait.SESSION
    )
    userAuthHandler: UserAuthHandler = UserAuthHandler(user, Trait.AUTH)

    try:
        # Register handlers with router
        router.register(user, Trait.SESSION, userLLMSessionHandler)
        router.register(user, Trait.AUTH, userAuthHandler)
    except Exception as e:
        console.print(
            f"[red]It seems that a route registration issue was triggered for [yellow]{user}[/yellow].[/red]"
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

    Args:
        ctx: Click context for command execution
        name: The username to log in
    """
    password: str = getpass.getpass("Enter password: ").strip()

    # Use UAM singleton to handle login
    result: UserLoginModel = await userAccessModule.user_login(name, password)

    if not result.status:
        # Handle login failure
        console.print(
            f"[bold red]Error: [yellow]{name}[/yellow]: {result.message}[/bold red]"
        )
        if "does not exist" in result.message:
            console.print("Please create first with [yellow]/user create[/yellow]")
        return

    # Login successful
    console.print(
        f"[bold green]Login successful! Welcome, [yellow]{name}[/yellow].[/bold green]"
    )

    # Continue with dynamic routing setup
    cmdName: str = f"user:{name}"
    provider: Optional[ProviderModel] = dynamicRouting_set(cmdName)
    if provider and "cli" in ctx.obj:
        register_provider_commands(provider, ctx.obj["cli"])
