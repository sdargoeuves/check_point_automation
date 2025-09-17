"""
Abstract base classes and interfaces for Check Point automation components.

This module defines the contracts that different components must implement
to ensure consistent behavior across the automation framework.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .models import (
    CheckPointConfig,
    SystemStatus,
    CommandResult,
    ConnectionInfo,
    InterfaceConfig,
    OSPFConfig,
    LLDPConfig,
    NetworkObject,
    FirewallRule,
    WizardConfig,
    CheckPointState,
    CLIMode,
)


class ConnectionManagerInterface(ABC):
    """Abstract interface for SSH connection management."""

    @abstractmethod
    def connect(self, connection_info: ConnectionInfo) -> bool:
        """
        Establish SSH connection to Check Point VM.

        Args:
            connection_info: Connection parameters

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close SSH connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        pass

    @abstractmethod
    def detect_state(self) -> CheckPointState:
        """Detect current Check Point VM state."""
        pass

    @abstractmethod
    def get_cli_mode(self) -> CLIMode:
        """Get current CLI mode."""
        pass

    @abstractmethod
    def switch_to_expert(self, expert_password: str) -> bool:
        """Switch to expert mode."""
        pass

    @abstractmethod
    def switch_to_clish(self) -> bool:
        """Switch to clish mode."""
        pass

    @abstractmethod
    def execute_command(self, command: str, mode: Optional[CLIMode] = None) -> CommandResult:
        """Execute command in specified mode."""
        pass


class ConfigurationModuleInterface(ABC):
    """Abstract interface for configuration modules."""

    def __init__(self, connection_manager: ConnectionManagerInterface):
        self.connection_manager = connection_manager

    @abstractmethod
    def validate_prerequisites(self) -> bool:
        """Validate that prerequisites for this module are met."""
        pass

    @abstractmethod
    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration state."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration before applying."""
        pass


class InitialSetupInterface(ConfigurationModuleInterface):
    """Interface for initial Check Point VM setup operations."""

    @abstractmethod
    def set_expert_password(self, password: str) -> bool:
        """Set expert password on fresh Check Point VM."""
        pass

    @abstractmethod
    def run_first_time_wizard(self, config: WizardConfig) -> bool:
        """Run first-time setup wizard."""
        pass

    @abstractmethod
    def update_admin_password(self, new_password: str) -> bool:
        """Update admin user password."""
        pass

    @abstractmethod
    def verify_initial_setup(self) -> SystemStatus:
        """Verify initial setup completion."""
        pass


class NetworkConfigInterface(ConfigurationModuleInterface):
    """Interface for network configuration operations."""

    @abstractmethod
    def configure_interfaces(self, interfaces: List[InterfaceConfig]) -> bool:
        """Configure network interfaces."""
        pass

    @abstractmethod
    def configure_ospf(self, ospf_config: OSPFConfig) -> bool:
        """Configure OSPF routing."""
        pass

    @abstractmethod
    def configure_lldp(self, lldp_config: LLDPConfig) -> bool:
        """Configure LLDP."""
        pass

    @abstractmethod
    def validate_network_config(self) -> Dict[str, bool]:
        """Validate network configuration status."""
        pass


class SecurityPolicyInterface(ConfigurationModuleInterface):
    """Interface for security policy operations."""

    @abstractmethod
    def create_network_objects(self, objects: List[NetworkObject]) -> bool:
        """Create network objects."""
        pass

    @abstractmethod
    def create_firewall_rules(self, rules: List[FirewallRule]) -> bool:
        """Create firewall rules."""
        pass

    @abstractmethod
    def install_policy(self) -> bool:
        """Install security policy."""
        pass

    @abstractmethod
    def validate_policy(self) -> Dict[str, bool]:
        """Validate policy installation status."""
        pass


class ValidationEngineInterface(ABC):
    """Interface for configuration validation operations."""

    @abstractmethod
    def validate_system_state(self, expected_state: CheckPointState) -> bool:
        """Validate current system state matches expected."""
        pass

    @abstractmethod
    def validate_configuration(self, config: CheckPointConfig) -> Dict[str, bool]:
        """Validate complete configuration."""
        pass

    @abstractmethod
    def check_idempotency(self, config: CheckPointConfig) -> Dict[str, bool]:
        """Check if configuration changes are needed."""
        pass

    @abstractmethod
    def generate_config_diff(self, current: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration differences."""
        pass


class AutomationBackendInterface(ABC):
    """Interface for automation backend implementations."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the automation backend."""
        pass

    @abstractmethod
    def execute_workflow(self, workflow_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a named workflow."""
        pass

    @abstractmethod
    def get_supported_workflows(self) -> List[str]:
        """Get list of supported workflows."""
        pass

    @abstractmethod
    def validate_workflow(self, workflow_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate workflow parameters."""
        pass


class LoggerInterface(ABC):
    """Interface for logging operations."""

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        pass

    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        pass
