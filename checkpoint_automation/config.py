"""
Configuration management for Check Point automation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FirewallConfig:
    """Configuration class for firewall connection details."""
    
    ip_address: str
    username: str = "admin"
    password: str = "admin"
    expert_password: Optional[str] = None
    logging_level: str = "INFO" # Logging level for console output (DEBUG, INFO, WARNING, ERROR)
    script_content: Optional[str] = None
    # Timeout configuration
    timeout: int = 15          # Connection and command timeout in seconds
    read_timeout: int = 3      # Read timeout for connection checks
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.ip_address:
            raise ValueError("IP address is required")
        
        if self.expert_password and len(self.expert_password) < 6:
            raise ValueError("Expert password must be at least 6 characters long")