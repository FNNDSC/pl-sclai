"""
Centralized application-specific logging using Loguru.

This module provides a function-based logging mechanism (`LOG`) that dynamically
respects the `beQuiet` flag from application settings.

Features:
- A custom `LOG` function for application-specific debug logging.
- Dynamic checking of the `beQuiet` flag to suppress logs when necessary.
- Consistent and customizable logging format.

Usage:
- Use `LOG` for application-specific debug logging.
- The `beQuiet` flag controls whether logs are displayed.

Example:
    from app.lib.log import LOG
    LOG("This is a debug message.")

Environment:
- Set `SCL_BEQUIET=True` to suppress detailed logging output.
"""

from loguru import logger
from typing import Any
import sys

# Create a distinct logger instance for the app
app_logger = logger.bind(app="SCLAI")

# Configure the app-specific logger
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> │ "
    "<level>{level: <5}</level> │ "
    "<yellow>{name: >28}</yellow>::"
    "<cyan>{function: <30}</cyan> @ "
    "<cyan>{line: <4}</cyan> ║ "
    "<level>{message}</level>"
)

app_logger.remove()  # Remove any default handlers
app_logger.add(sys.stderr, format=logger_format)


def LOG(*args: Any, **kwargs: Any) -> None:
    """
    Application-specific logging function.

    This function checks the `beQuiet` flag in `appsettings` and logs the message
    only if logging is enabled.

    :param args: Positional arguments for the log message.
    :param kwargs: Keyword arguments for additional log metadata.
    """
    try:
        from app.config.settings import appsettings  # Ensure up-to-date settings

        if not appsettings.beQuiet:
            app_logger.debug(*args, **kwargs)
    except Exception as e:
        print(f"Logging error: {e}")  # Fallback to standard output on failure
