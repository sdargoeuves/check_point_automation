"""
Check Point VM Automation Framework

A Python library for automating Check Point firewall configuration and management.
"""

__version__ = "0.1.0"
__author__ = "Check Point Automation Team"

from .ssh_connection import SSHConnectionManager
from .config import FirewallConfig

__all__ = ["SSHConnectionManager", "FirewallConfig"]