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
from app.config.settings import console
import click
from app.commands.base import RichGroup, RichCommand, rich_help
from app.lib.router import Router, router, accessor_handle
from app.lib.handlers import LLMAccessorHandler
from app.models.dataModel import Accessor, RouteMapperModel, ProviderModel, Trait
import pudb


llm_providers: dict[str, ProviderModel] = {}


def register_provider_commands(provider: ProviderModel, cli: click.Group) -> None:
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
        short_help=f"{provider.name} specific commands",
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
        short_help=f"Handle API keys for {provider.name}",
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
        short_help="Get the API key",
        help=rich_help(
            command="show",
            description=f"Display current API key for {provider.name}",
            usage=f"/{provider.name} key show",
            args={"<None>": "no arguments"},
        ),
    )
    async def get() -> str:
        """Show current API key."""
        # pudb.set_trace()
        value: str = await provider.commands[Accessor.GET.value](
            provider.name, Accessor.GET, Trait.KEY, None, "API key for"
        )
        return value

    @key.command(
        cls=RichCommand,
        short_help="Set the API key",
        help=rich_help(
            command="set",
            description=f"Set API key for {provider.name}",
            usage=f"/{provider.name} key set <value>",
            args={"<value>": "API key value to store"},
        ),
    )
    @click.argument("value", type=str)
    async def set(value: str) -> str:
        """Set API key value."""
        # pudb.set_trace()
        set: str = await provider.commands[Accessor.SET.value](
            provider.name, Accessor.SET, Trait.KEY, value, "API key for"
        )
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
    cmdName: str = f"llm:{provider_name}"
    provider = ProviderModel(
        name=cmdName,
        commands={
            Accessor.GET.value: accessor_handle,
            Accessor.SET.value: accessor_handle,
        },
    )
    llm_providers[cmdName] = provider

    # Register route handlers
    keyHandler: LLMAccessorHandler = LLMAccessorHandler(cmdName, Trait.KEY)
    router.register(cmdName, Trait.KEY, keyHandler)

    if "cli" in ctx.obj:
        register_provider_commands(provider, ctx.obj["cli"])
    console.print(f"[green]Connected to[/green] [yellow]{provider_name}[/yellow]")
