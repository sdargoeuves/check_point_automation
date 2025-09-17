"""
Check Point VM Automation Package

This package provides automation capabilities for Check Point VM appliances,
including initial setup, network configuration, and security policy management.
"""

__version__ = "1.0.0"
__author__ = "Network Automation Team"

from .core.exceptions import CheckPointError, ConfigurationError, ConnectionError, ValidationError
from .core.models import CheckPointConfig, CheckPointState, SystemStatus

__all__ = [
    "CheckPointError",
    "ConnectionError",
    "ConfigurationError",
    "ValidationError",
    "CheckPointConfig",
    "CheckPointState",
    "SystemStatus",
]
