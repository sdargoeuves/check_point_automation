"""
Utility functions for Check Point automation operations.

This module provides common utility functions used across
the automation framework.
"""

import functools
import time
from typing import Any, Callable, Dict

from .exceptions import ConnectionError
from .logging_config import get_logger

logger = get_logger(__name__)


def retry_on_failure(
    max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 2.0, exceptions: tuple = (ConnectionError,)
):
    """
    Decorator to retry function calls on specific exceptions.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {current_delay}s",
                            function=func.__name__,
                            error=str(e),
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed", function=func.__name__, error=str(e))

            # Re-raise the last exception if all attempts failed
            raise last_exception

        return wrapper

    return decorator


def validate_ip_address(ip_address: str) -> bool:
    """
    Validate IP address format.

    Args:
        ip_address: IP address string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parts = ip_address.split(".")
        if len(parts) != 4:
            return False

        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False

        return True
    except Exception:
        return False


def validate_subnet_mask(subnet_mask: str) -> bool:
    """
    Validate subnet mask format.

    Args:
        subnet_mask: Subnet mask string to validate

    Returns:
        True if valid, False otherwise
    """
    if not validate_ip_address(subnet_mask):
        return False

    # Convert to binary and check if it's a valid subnet mask
    try:
        parts = subnet_mask.split(".")
        binary = "".join([format(int(part), "08b") for part in parts])

        # Valid subnet mask should have all 1s followed by all 0s
        if "01" in binary:
            return False

        return True
    except Exception:
        return False


def sanitize_hostname(hostname: str) -> str:
    """
    Sanitize hostname to ensure it meets Check Point requirements.

    Args:
        hostname: Raw hostname string

    Returns:
        Sanitized hostname
    """
    # Remove invalid characters and ensure proper format
    sanitized = "".join(c for c in hostname if c.isalnum() or c in "-_")

    # Ensure it doesn't start or end with hyphen
    sanitized = sanitized.strip("-_")

    # Limit length
    if len(sanitized) > 63:
        sanitized = sanitized[:63]

    return sanitized


def parse_command_output(output: str, delimiter: str = "\n") -> list:
    """
    Parse command output into lines, removing empty lines and whitespace.

    Args:
        output: Raw command output
        delimiter: Line delimiter

    Returns:
        List of cleaned output lines
    """
    if not output:
        return []

    lines = output.split(delimiter)
    return [line.strip() for line in lines if line.strip()]


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.2f}s"


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries, with override taking precedence.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()

    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged


def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely get value from dictionary with dot notation support.

    Args:
        dictionary: Dictionary to search
        key: Key to search for (supports dot notation like 'a.b.c')
        default: Default value if key not found

    Returns:
        Value if found, default otherwise
    """
    try:
        keys = key.split(".")
        value = dictionary

        for k in keys:
            value = value[k]

        return value
    except (KeyError, TypeError):
        return default
