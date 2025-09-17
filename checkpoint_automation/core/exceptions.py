"""
Exception classes for Check Point automation operations.

This module defines the exception hierarchy used throughout the automation
framework to handle different types of errors that can occur during
Check Point VM operations.
"""

from typing import Optional, Dict, Any


class CheckPointError(Exception):
    """
    Base exception for all Check Point automation operations.

    This is the root exception class that all other Check Point-specific
    exceptions inherit from.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ConnectionError(CheckPointError):
    """
    Exception raised for SSH connection related errors.

    This includes connection failures, authentication failures,
    and session timeout issues.
    """

    pass


class ConfigurationError(CheckPointError):
    """
    Exception raised for configuration command errors.

    This includes invalid command syntax, configuration conflicts,
    and resource limitations.
    """

    pass


class ValidationError(CheckPointError):
    """
    Exception raised for configuration validation errors.

    This includes validation failures, state inconsistencies,
    and verification errors.
    """

    pass


class StateError(CheckPointError):
    """
    Exception raised for unexpected system state errors.

    This includes unexpected system states, incomplete configurations,
    and state transition failures.
    """

    pass


class AuthenticationError(ConnectionError):
    """
    Exception raised for authentication-specific errors.

    This includes credential failures, password policy violations,
    and authentication timeout issues.
    """

    pass
