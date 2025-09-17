"""
Data models for Check Point automation configuration and state management.

This module defines the dataclasses and enums used to represent
Check Point VM configurations, system states, and operational data.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class CheckPointState(Enum):
    """Enumeration of possible Check Point VM states."""

    FRESH_INSTALL = "fresh"
    EXPERT_PASSWORD_SET = "expert_set"
    WIZARD_COMPLETE = "wizard_complete"
    FULLY_CONFIGURED = "configured"
    UNKNOWN = "unknown"


class CLIMode(Enum):
    """Enumeration of Check Point CLI modes."""

    CLISH = "clish"
    EXPERT = "expert"
    UNKNOWN = "unknown"


class NetworkObjectType(Enum):
    """Types of network objects in Check Point."""

    HOST = "host"
    NETWORK = "network"
    RANGE = "range"
    GROUP = "group"


class FirewallAction(Enum):
    """Firewall rule actions."""

    ACCEPT = "accept"
    DROP = "drop"
    REJECT = "reject"


@dataclass
class InterfaceConfig:
    """Configuration for a network interface."""

    name: str
    ip_address: str
    subnet_mask: str
    description: Optional[str] = None
    enabled: bool = True

    def __post_init__(self):
        """Validate interface configuration."""
        if not self.name:
            raise ValueError("Interface name cannot be empty")
        if not self.ip_address:
            raise ValueError("IP address cannot be empty")
        if not self.subnet_mask:
            raise ValueError("Subnet mask cannot be empty")


@dataclass
class OSPFArea:
    """OSPF area configuration."""

    area_id: str
    area_type: str = "normal"  # normal, stub, nssa

    def __post_init__(self):
        """Validate OSPF area configuration."""
        if not self.area_id:
            raise ValueError("OSPF area ID cannot be empty")
        if self.area_type not in ["normal", "stub", "nssa"]:
            raise ValueError(f"Invalid OSPF area type: {self.area_type}")


@dataclass
class OSPFNetwork:
    """OSPF network configuration."""

    network: str
    area_id: str

    def __post_init__(self):
        """Validate OSPF network configuration."""
        if not self.network:
            raise ValueError("OSPF network cannot be empty")
        if not self.area_id:
            raise ValueError("OSPF area ID cannot be empty")


@dataclass
class OSPFConfig:
    """OSPF routing protocol configuration."""

    router_id: str
    areas: List[OSPFArea] = field(default_factory=list)
    networks: List[OSPFNetwork] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self):
        """Validate OSPF configuration."""
        if not self.router_id:
            raise ValueError("OSPF router ID cannot be empty")


@dataclass
class LLDPConfig:
    """LLDP configuration."""

    enabled: bool = True
    transmit_interval: int = 30
    hold_multiplier: int = 4
    interfaces: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate LLDP configuration."""
        if self.transmit_interval <= 0:
            raise ValueError("LLDP transmit interval must be positive")
        if self.hold_multiplier <= 0:
            raise ValueError("LLDP hold multiplier must be positive")


@dataclass
class NetworkObject:
    """Check Point network object definition."""

    name: str
    type: NetworkObjectType
    value: str
    description: Optional[str] = None

    def __post_init__(self):
        """Validate network object configuration."""
        if not self.name:
            raise ValueError("Network object name cannot be empty")
        if not self.value:
            raise ValueError("Network object value cannot be empty")


@dataclass
class FirewallRule:
    """Check Point firewall rule definition."""

    name: str
    source: List[str]
    destination: List[str]
    service: List[str]
    action: FirewallAction
    track: str = "Log"
    enabled: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        """Validate firewall rule configuration."""
        if not self.name:
            raise ValueError("Firewall rule name cannot be empty")
        if not self.source:
            raise ValueError("Firewall rule must have at least one source")
        if not self.destination:
            raise ValueError("Firewall rule must have at least one destination")
        if not self.service:
            raise ValueError("Firewall rule must have at least one service")


@dataclass
class WizardConfig:
    """Configuration for Check Point first-time wizard."""

    hostname: str
    timezone: str = "UTC"
    ntp_servers: List[str] = field(default_factory=list)
    dns_servers: List[str] = field(default_factory=list)
    domain_name: Optional[str] = None

    def __post_init__(self):
        """Validate wizard configuration."""
        if not self.hostname:
            raise ValueError("Hostname cannot be empty")


@dataclass
class CheckPointConfig:
    """Complete Check Point VM configuration."""

    hostname: str
    management_ip: str
    expert_password: str
    admin_password: str
    interfaces: List[InterfaceConfig] = field(default_factory=list)
    ospf_config: Optional[OSPFConfig] = None
    lldp_config: Optional[LLDPConfig] = None
    network_objects: List[NetworkObject] = field(default_factory=list)
    firewall_rules: List[FirewallRule] = field(default_factory=list)
    wizard_config: Optional[WizardConfig] = None

    def __post_init__(self):
        """Validate complete configuration."""
        if not self.hostname:
            raise ValueError("Hostname cannot be empty")
        if not self.management_ip:
            raise ValueError("Management IP cannot be empty")
        if not self.expert_password:
            raise ValueError("Expert password cannot be empty")
        if not self.admin_password:
            raise ValueError("Admin password cannot be empty")


@dataclass
class SystemStatus:
    """Current system status and state information."""

    state: CheckPointState
    version: str
    hostname: str
    interfaces_configured: bool = False
    policy_installed: bool = False
    last_config_change: Optional[datetime] = None
    cli_mode: CLIMode = CLIMode.UNKNOWN
    expert_password_set: bool = False
    wizard_completed: bool = False

    def __post_init__(self):
        """Validate system status."""
        if not self.version:
            raise ValueError("Version cannot be empty")
        if not self.hostname:
            raise ValueError("Hostname cannot be empty")


@dataclass
class CommandResult:
    """Result of a CLI command execution."""

    command: str
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None

    def __post_init__(self):
        """Validate command result."""
        if not self.command:
            raise ValueError("Command cannot be empty")


@dataclass
class ConnectionInfo:
    """SSH connection information."""

    host: str
    port: int = 22
    username: str = "admin"
    password: str = "admin"
    timeout: int = 30

    def __post_init__(self):
        """Validate connection information."""
        if not self.host:
            raise ValueError("Host cannot be empty")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        if not self.username:
            raise ValueError("Username cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
