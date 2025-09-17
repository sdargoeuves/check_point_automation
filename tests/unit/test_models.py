"""
Unit tests for Check Point automation data models.
"""

import pytest
from datetime import datetime
from checkpoint_automation.core.models import (
    CheckPointState,
    CLIMode,
    NetworkObjectType,
    FirewallAction,
    InterfaceConfig,
    OSPFArea,
    OSPFNetwork,
    OSPFConfig,
    LLDPConfig,
    NetworkObject,
    FirewallRule,
    WizardConfig,
    CheckPointConfig,
    SystemStatus,
    CommandResult,
    ConnectionInfo,
)


class TestInterfaceConfig:
    """Test InterfaceConfig data model."""

    def test_valid_interface_config(self):
        """Test creating valid interface configuration."""
        config = InterfaceConfig(
            name="eth1", ip_address="192.168.1.1", subnet_mask="255.255.255.0", description="Test interface"
        )

        assert config.name == "eth1"
        assert config.ip_address == "192.168.1.1"
        assert config.subnet_mask == "255.255.255.0"
        assert config.description == "Test interface"
        assert config.enabled is True

    def test_interface_config_validation(self):
        """Test interface configuration validation."""
        with pytest.raises(ValueError, match="Interface name cannot be empty"):
            InterfaceConfig(name="", ip_address="192.168.1.1", subnet_mask="255.255.255.0")

        with pytest.raises(ValueError, match="IP address cannot be empty"):
            InterfaceConfig(name="eth1", ip_address="", subnet_mask="255.255.255.0")

        with pytest.raises(ValueError, match="Subnet mask cannot be empty"):
            InterfaceConfig(name="eth1", ip_address="192.168.1.1", subnet_mask="")


class TestOSPFConfig:
    """Test OSPF configuration models."""

    def test_ospf_area_valid(self):
        """Test creating valid OSPF area."""
        area = OSPFArea(area_id="0.0.0.0", area_type="normal")
        assert area.area_id == "0.0.0.0"
        assert area.area_type == "normal"

    def test_ospf_area_validation(self):
        """Test OSPF area validation."""
        with pytest.raises(ValueError, match="OSPF area ID cannot be empty"):
            OSPFArea(area_id="")

        with pytest.raises(ValueError, match="Invalid OSPF area type"):
            OSPFArea(area_id="0.0.0.0", area_type="invalid")

    def test_ospf_network_valid(self):
        """Test creating valid OSPF network."""
        network = OSPFNetwork(network="192.168.1.0/24", area_id="0.0.0.0")
        assert network.network == "192.168.1.0/24"
        assert network.area_id == "0.0.0.0"

    def test_ospf_config_valid(self):
        """Test creating valid OSPF configuration."""
        config = OSPFConfig(
            router_id="1.1.1.1",
            areas=[OSPFArea(area_id="0.0.0.0")],
            networks=[OSPFNetwork(network="192.168.1.0/24", area_id="0.0.0.0")],
        )
        assert config.router_id == "1.1.1.1"
        assert len(config.areas) == 1
        assert len(config.networks) == 1


class TestNetworkObject:
    """Test NetworkObject data model."""

    def test_valid_network_object(self):
        """Test creating valid network object."""
        obj = NetworkObject(
            name="Test_Host", type=NetworkObjectType.HOST, value="192.168.1.10", description="Test host object"
        )

        assert obj.name == "Test_Host"
        assert obj.type == NetworkObjectType.HOST
        assert obj.value == "192.168.1.10"
        assert obj.description == "Test host object"

    def test_network_object_validation(self):
        """Test network object validation."""
        with pytest.raises(ValueError, match="Network object name cannot be empty"):
            NetworkObject(name="", type=NetworkObjectType.HOST, value="192.168.1.10")

        with pytest.raises(ValueError, match="Network object value cannot be empty"):
            NetworkObject(name="Test", type=NetworkObjectType.HOST, value="")


class TestFirewallRule:
    """Test FirewallRule data model."""

    def test_valid_firewall_rule(self):
        """Test creating valid firewall rule."""
        rule = FirewallRule(
            name="Test_Rule",
            source=["Any"],
            destination=["Internal_Network"],
            service=["http", "https"],
            action=FirewallAction.ACCEPT,
            description="Test rule",
        )

        assert rule.name == "Test_Rule"
        assert rule.source == ["Any"]
        assert rule.destination == ["Internal_Network"]
        assert rule.service == ["http", "https"]
        assert rule.action == FirewallAction.ACCEPT
        assert rule.track == "Log"
        assert rule.enabled is True

    def test_firewall_rule_validation(self):
        """Test firewall rule validation."""
        with pytest.raises(ValueError, match="Firewall rule name cannot be empty"):
            FirewallRule(
                name="", source=["Any"], destination=["Internal"], service=["http"], action=FirewallAction.ACCEPT
            )

        with pytest.raises(ValueError, match="must have at least one source"):
            FirewallRule(
                name="Test", source=[], destination=["Internal"], service=["http"], action=FirewallAction.ACCEPT
            )


class TestSystemStatus:
    """Test SystemStatus data model."""

    def test_valid_system_status(self):
        """Test creating valid system status."""
        status = SystemStatus(
            state=CheckPointState.FULLY_CONFIGURED,
            version="R81.20",
            hostname="checkpoint-fw01",
            interfaces_configured=True,
            policy_installed=True,
            last_config_change=datetime.now(),
        )

        assert status.state == CheckPointState.FULLY_CONFIGURED
        assert status.version == "R81.20"
        assert status.hostname == "checkpoint-fw01"
        assert status.interfaces_configured is True
        assert status.policy_installed is True

    def test_system_status_validation(self):
        """Test system status validation."""
        with pytest.raises(ValueError, match="Version cannot be empty"):
            SystemStatus(state=CheckPointState.FRESH_INSTALL, version="", hostname="test")


class TestConnectionInfo:
    """Test ConnectionInfo data model."""

    def test_valid_connection_info(self):
        """Test creating valid connection info."""
        conn = ConnectionInfo(host="192.168.1.100", port=22, username="admin", password="admin", timeout=30)

        assert conn.host == "192.168.1.100"
        assert conn.port == 22
        assert conn.username == "admin"
        assert conn.password == "admin"
        assert conn.timeout == 30

    def test_connection_info_validation(self):
        """Test connection info validation."""
        with pytest.raises(ValueError, match="Host cannot be empty"):
            ConnectionInfo(host="")

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            ConnectionInfo(host="192.168.1.100", port=0)

        with pytest.raises(ValueError, match="Username cannot be empty"):
            ConnectionInfo(host="192.168.1.100", username="")

        with pytest.raises(ValueError, match="Timeout must be positive"):
            ConnectionInfo(host="192.168.1.100", timeout=0)
