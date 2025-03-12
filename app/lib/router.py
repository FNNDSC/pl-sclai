"""
Command routing and dispatch system for SCLAI.

This module implements a centralized routing system for /<command>/<context> style commands:
- Registration of command handlers
- Command dispatch to appropriate handlers
- Standardized route patterns: /<cmd> <ctx> [get|set] [value]

Example flow:
    /openai key set "abc123"  -> routes to OpenAI key handler's set() method
    /prompt persistent get    -> routes to Prompt persistence handler's get() method

Features:
- Dynamic handler registration
- Type-safe routing through Protocol enforcement
- Centralized error handling
- Command validation
"""

from typing import Any
from app.config.settings import console
from app.models.dataModel import (
    RouteContextModel,
    RouteMapperModel,
    RouteHandler,
    Accessor,
    Trait,
)
import pudb


class Router:
    def __init__(self) -> None:
        """Initialize empty route registry."""
        self._routes: dict[str, RouteHandler] = {}

    def register(self, command: str, context: Trait, handler: RouteHandler) -> None:
        """Register handler for command/context pair.

        Args:
            command: Command identifier
            context: Command context
            handler: Handler instance for route

        Raises:
            ValueError: If route already registered
        """
        pathRoute: RouteContextModel = RouteContextModel(command, context)
        pathStr: str = f"{pathRoute.command}_{pathRoute.context}"
        if pathStr in self._routes:
            raise ValueError(f"Handler already registered for {command}/{context}")
        self._routes[pathStr] = handler

    async def dispatch(self, route: RouteMapperModel) -> str | None:
        """Dispatch command to appropriate handler.

        Args:
            route: Route model containing command info

        Returns:
            Handler response

        Raises:
            ValueError: If no handler found
            RuntimeError: If handler operation fails
        """
        path: RouteContextModel = RouteContextModel(route.command, route.context)
        pathStr: str = f"{route.command}_{route.context}"
        if pathStr not in self._routes:
            raise ValueError(f"No handler for {route.command}/{route.context}")
        # pudb.set_trace()

        handler = self._routes[pathStr]
        try:
            if route.accessor == Accessor.GET:
                return await handler.get()
            if not route.value:
                return None
            return await handler.set(route.value)
        except Exception as e:
            raise RuntimeError(f"Handler operation failed: {e}")


router: Router = Router()


async def accessor_handle(
    provider: str,
    action: Accessor,
    trait: Trait,
    value: str | None = None,
    confirmation: str | None = None,
) -> str | None:
    route: RouteMapperModel = RouteMapperModel(
        command=provider, context=trait, accessor=action, value=value
    )
    result: str | None = await router.dispatch(route)
    console.print(
        f"[yellow]{confirmation} {provider}[/yellow]: [green]{result}[/green]"
    )
    return result
