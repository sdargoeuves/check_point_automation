"""
Logging configuration for Check Point automation framework.

This module provides centralized logging configuration with support for
different log levels, formatters, and output destinations.
"""

import logging
import logging.config
from pathlib import Path
from typing import Any, Dict, Optional

from .interfaces import LoggerInterface


class CheckPointLogger(LoggerInterface):
    """
    Logger implementation for Check Point automation operations.

    Provides structured logging with context information and
    integration with the automation framework.
    """

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Add context for all log messages
        self._context = {}

    def set_context(self, **kwargs) -> None:
        """Set context information for log messages."""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear context information."""
        self._context.clear()

    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context information."""
        context = {**self._context, **kwargs}
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            return f"{message} | {context_str}"
        return message

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(self._format_message(message, **kwargs))

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(self._format_message(message, **kwargs))


def get_logging_config(
    log_level: str = "INFO", log_file: Optional[str] = None, console_output: bool = True
) -> Dict[str, Any]:
    """
    Get logging configuration dictionary.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        console_output: Whether to output to console

    Returns:
        Logging configuration dictionary
    """

    formatters = {
        "detailed": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "datefmt": "%Y-%m-%d %H:%M:%S"},
        "simple": {"format": "%(levelname)s - %(message)s"},
    }

    handlers = {}

    if console_output:
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        }

    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            "checkpoint_automation": {"level": log_level, "handlers": list(handlers.keys()), "propagate": False}
        },
        "root": {"level": log_level, "handlers": list(handlers.keys())},
    }

    return config


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None, console_output: bool = True) -> None:
    """
    Setup logging configuration for the application.

    Args:
        log_level: Logging level
        log_file: Optional log file path
        console_output: Whether to output to console
    """
    config = get_logging_config(log_level, log_file, console_output)
    logging.config.dictConfig(config)


def get_logger(name: str, level: str = "INFO") -> CheckPointLogger:
    """
    Get a logger instance for the specified name.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        CheckPointLogger instance
    """
    return CheckPointLogger(name, level)


# Default logger for the framework
logger = get_logger("checkpoint_automation")
