"""
Check Point VM Automation Framework

A Python library for automating Check Point firewall configuration and management.
"""

__version__ = "0.1.0"
__author__ = "Check Point Automation Team"

from .command_executor import CommandExecutor, CommandResponse, FirewallMode
from .config import FirewallConfig
from .expert_password import ExpertPasswordManager
from .script_deployment import ScriptDeployment
from .ssh_connection import SSHConnectionManager

__all__ = [
    "SSHConnectionManager",
    "FirewallConfig",
    "CommandExecutor",
    "CommandResponse",
    "FirewallMode",
    "ExpertPasswordManager",
    "ScriptDeployment",
]
