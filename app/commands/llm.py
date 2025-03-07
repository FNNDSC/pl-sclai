"""
LLM provider management and dynamic command registration.
Handles connection and command routing for different LLM providers.

Features:
- Dynamic command registration for LLM providers
- API key management per provider
- Command routing and execution
- Secure key storage and retrieval
- Provider state management

Usage:
    /llm connect <provider>     Connect to LLM provider
    /<provider> key show        Display provider API key
    /<provider> key set <key>   Set provider API key
"""

from dataclasses import dataclass
from typing import Callable
from rich.console import Console
import click
from app.commands.base import RichGroup, RichCommand, rich_help
from app.lib.router import Router
from app.lib.handlers import LLMAccessorHandler
from app.models.dataModel import Accessor, RouteMapperModel, LLMProviderModel, Trait
import pudb

console: Console = Console()

router = Router()


llm_providers: dict[str, LLMProviderModel] = {}


async def accessor_handle(
    provider: str, action: Accessor, trait: Trait, value: str | None = None
) -> str | None:
    route: RouteMapperModel = RouteMapperModel(
        command=provider, context=trait, accessor=action, value=value
    )
    result: str | None = await router.disptch(route)
    return result


async def handle_key_command(
    provider: str, action: Accessor, value: str | None = None
) -> None:
    route = RouteMapperModel(
        command=provider, context=Trait.KEY, accessor=action, value=value
    )
    result = await router.dispatch(route)
    if action == Accessor.GET:
        console.print(f"[yellow]API Key: {result}[/yellow]")


async def show_key(provider: str) -> None:
    """Show API key for provider.

    Args:
        provider: Name of LLM provider (e.g. 'openai', 'claude')

    Raises:
        RuntimeError: If key retrieval fails
        ValueError: If provider not found

    Note:
        Keys are retrieved from MongoDB llm/keys collection
        Provider name is used as document ID
    """
    route = RouteMapperModel(provider, Trait.KEY, Accessor.GET, None)
    result = await router.dispatch(route)
    console.print(f"[yellow]API Key for {provider}: {result}[/yellow]")


async def set_key(provider: str, key: str) -> None:
    """Set API key for provider.

    Args:
        provider: Name of LLM provider
        key: API key to store

    Raises:
        RuntimeError: If storage fails
        ValueError: If key invalid or provider not found

    Note:
        Keys are stored in MongoDB llm/keys collection
        Provider name is used as document ID
        Existing keys are overwritten
    """
    # pudb.set_trace()
    route = RouteMapperModel(provider, Trait.KEY, Accessor.SET, key)
    await router.dispatch(route)
    console.print(f"[green]Key set for {provider}[/green]")


def register_provider_commands(provider: LLMProviderModel, cli: click.Group) -> None:
    """Register dynamic commands for an LLM provider.

    Creates command group and subcommands for provider:
    - key show: Display provider API key
    - key set: Configure provider API key

    Args:
        provider: LLMProvider instance to register commands for
        cli: Click command group to register commands with

    Note:
        Commands are registered with root CLI group
        Help text available at each command level
    """

    @click.group(
        cls=RichGroup,
        help=f"""
        {provider.name.upper()} Provider Commands
        Manage configuration and API keys for {provider.name}
        """,
    )
    def provider_group() -> None:
        """Command group for managing {provider.name} provider."""
        pass

    @provider_group.group(
        cls=RichGroup,
        help=f"""
        API Key Management
        Show or set API key for {provider.name}
        """,
    )
    def key() -> None:
        """Manage API key configuration."""
        pass

    @key.command(
        cls=RichCommand,
        help=rich_help(
            command="show",
            description=f"Display current API key for {provider.name}",
            usage="/<provider> key show",
            args={"<None>": "no arguments"},
        ),
    )
    async def get() -> str:
        """Show current API key."""
        value: str = await provider.commands[Accessor.GET.value](provider.name)
        return value

    @key.command(
        cls=RichCommand,
        help=rich_help(
            command="set",
            description=f"Set API key for {provider.name}",
            usage="/<provider> key set <value>",
            args={"<value>": "API key value to store"},
        ),
    )
    @click.argument("value", type=str)
    async def set(value: str) -> str:
        """Set API key value."""
        pudb.set_trace()
        set: str = await provider.commands[Accessor.SET.value](provider.name, value)
        return set

    cli.add_command(provider_group, name=provider.name)


@click.group(
    cls=RichGroup,
    short_help="Manage local LLM interface",
    help="""
    LLM Provider Management
    Commands to manage API key configuration and connections.
    """,
)
def llm() -> None:
    """The root group for LLM-related commands.

    Handles:
    - Provider connections
    - Command registration
    - API key management
    """
    pass


@llm.command(
    cls=RichCommand,
    short_help="Connect to an AI provider (OpenAI, claude, etc.)",
    help=rich_help(
        command="connect",
        description="Connect to an LLM provider",
        usage="/llm connect <provider>",
        args={"<provider>": "Name of LLM provider (e.g. openai, claude)"},
    ),
)
@click.argument("provider_name", type=str)
@click.pass_context
async def connect(ctx: click.Context, provider_name: str) -> None:
    """Connect to LLM provider and register commands.

    Args:
        ctx: Click context containing CLI group reference
        provider_name: Name of provider to connect

    Note:
        Creates provider instance and registers commands
        Provider remains active until session end
    """
    # pudb.set_trace()
    provider = LLMProviderModel(
        name=provider_name,
        commands={Accessor.GET.value: show_key, Accessor.SET.value: set_key},
    )
    llm_providers[provider_name] = provider

    # Register route handlers
    keyHandler: LLMAccessorHandler = LLMAccessorHandler(provider_name, Trait.KEY)
    router.register(provider_name, Trait.KEY, keyHandler)

    if "cli" in ctx.obj:
        register_provider_commands(provider, ctx.obj["cli"])
    console.print(f"[green]Connected to {provider_name}[/green]")
