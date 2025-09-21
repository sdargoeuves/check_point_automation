"""Configuration management for Check Point automation."""

from dataclasses import dataclass
from typing import Optional

# Constants
MIN_PASSWORD_LENGTH = 6


@dataclass
class FirewallConfig:
    """Configuration class for firewall connection details."""

    ip_address: str
    username: str = "admin"
    password: str = "admin"
    expert_password: Optional[str] = None
    logging_level: str = "INFO"  # Logging level for console output (DEBUG, INFO, WARNING, ERROR)
    script_content: Optional[str] = None
    # Timeout configuration
    timeout: int = 15  # Connection and command timeout in seconds
    read_timeout: int = 3  # Read timeout for connection checks

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.ip_address:
            raise ValueError("IP address is required")

        if self.expert_password and len(self.expert_password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Expert password must be at least {MIN_PASSWORD_LENGTH} characters long")
