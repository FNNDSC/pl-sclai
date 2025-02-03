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
from app.models.dataModel import RouteKey, RouteModel, RouteHandler, Action


class Router:
    def __init__(self) -> None:
        """Initialize empty route registry."""
        self._routes: dict[RouteKey, RouteHandler] = {}

    def register(self, command: str, context: str, handler: RouteHandler) -> None:
        """Register handler for command/context pair.

        Args:
            command: Command identifier
            context: Command context
            handler: Handler instance for route

        Raises:
            ValueError: If route already registered
        """
        key = RouteKey(command, context)
        if key in self._routes:
            raise ValueError(f"Handler already registered for {command}/{context}")
        self._routes[key] = handler

    async def dispatch(self, route: RouteModel) -> Any:
        """Dispatch command to appropriate handler.

        Args:
            route: Route model containing command info

        Returns:
            Handler response

        Raises:
            ValueError: If no handler found
            RuntimeError: If handler operation fails
        """
        key = RouteKey(route.command, route.context)
        if key not in self._routes:
            raise ValueError(f"No handler for {route.command}/{route.context}")

        handler = self._routes[key]
        try:
            if route.action == Action.GET:
                return await handler.get()
            return await handler.set(route.value)
        except Exception as e:
            raise RuntimeError(f"Handler operation failed: {e}")
