"""
Centralized logging configuration using Loguru.

This module provides:
- A custom Loguru filter to respect application settings (e.g., 'beQuiet').
- A consistent logging format for all application logs.

Usage:
Import and use `LOG` for application-wide logging.
"""

from loguru import logger
from typing import Any
import sys


def log_filter(record: Any) -> bool:
    """
    Filter Loguru logs based on the 'beQuiet' flag.

    This function checks the application settings to determine whether logging should be suppressed.

    :param record: The log record.
    :return: True if logging should not be suppressed, False otherwise.
    """
    from app.config.settings import appsettings  # Ensure appsettings is up-to-date

    return not appsettings.beQuiet


# Logging configuration
logger_format: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> │ "
    "<level>{level: <5}</level> │ "
    "<yellow>{name: >28}</yellow>::"
    "<cyan>{function: <30}</cyan> @ "
    "<cyan>{line: <4}</cyan> ║ "
    "<level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, format=logger_format, filter=log_filter)
LOG: Any = logger.debug
