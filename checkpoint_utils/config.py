"""Configuration management for Check Point automation."""

from dataclasses import dataclass
from typing import Optional

# Constants
MIN_PASSWORD_LENGTH = 6


@dataclass
class FirewallConfig:
    """Configuration class for firewall connection details."""

    ip_address: str
    # Required fields - defaults are provided by caller
    username: str
    password: str
    timeout: int
    read_timeout: int
    last_read: int
    logging_level: str
    expert_password: str
    # Optional fields
    script_content: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.ip_address:
            raise ValueError("IP address is required")

        if self.expert_password and len(self.expert_password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Expert password must be at least {MIN_PASSWORD_LENGTH} characters long")
