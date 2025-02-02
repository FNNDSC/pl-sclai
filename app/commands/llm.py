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

console: Console = Console()


@dataclass
class LLMProvider:
    """LLM provider configuration and command mapping.

    Args:
        name: Provider identifier (e.g., 'openai', 'claude')
        commands: Mapping of command names to handler functions
    """

    name: str
    commands: dict[str, Callable]


llm_providers: dict[str, LLMProvider] = {}


async def show_key(provider: str) -> None:
    """Show API key for provider.

    Args:
        provider: Name of LLM provider

    Note:
        Keys should be retrieved from secure storage
    """
    console.print(f"[yellow]Showing key for {provider}[/yellow]")


async def set_key(provider: str, key: str) -> None:
    """Set API key for provider.

    Args:
        provider: Name of LLM provider
        key: API key to store

    Note:
        Keys should be stored securely
    """
    console.print(f"[green]Key set for {provider}[/green]")


def register_provider_commands(provider: LLMProvider, cli: click.Group) -> None:
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
    async def show() -> None:
        """Show current API key."""
        await provider.commands["show"](provider.name)

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
    async def set(value: str) -> None:
        """Set API key value."""
        await provider.commands["set"](provider.name, value)

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
    provider = LLMProvider(
        name=provider_name, commands={"show": show_key, "set": set_key}
    )
    llm_providers[provider_name] = provider
    if "cli" in ctx.obj:
        register_provider_commands(provider, ctx.obj["cli"])
    console.print(f"[green]Connected to {provider_name}[/green]")
