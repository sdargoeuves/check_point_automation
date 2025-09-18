"""
Tests for Check Point first-time wizard automation.

This module tests the wizard automation functionality including
configuration generation, validation, and application.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.models import WizardConfig, CheckPointState, CLIMode, CommandResult
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError


class TestWizardAutomation:
    """Test cases for wizard automation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)
        
        # Default wizard config for testing
        self.wizard_config = WizardConfig(
            hostname="test-cp-gw",
            timezone="America/New_York",
            ntp_servers=["pool.ntp.org", "time.nist.gov"],
            dns_servers=["8.8.8.8", "8.8.4.4"],
            domain_name="example.com"
        )

    def test_validate_wizard_config_valid(self):
        """Test wizard configuration validation with valid config."""
        result = self.initial_setup._validate_wizard_config(self.wizard_config)
        assert result is True

    def test_validate_wizard_config_empty_hostname(self):
        """Test wizard configuration validation with empty hostname."""
        # WizardConfig will raise ValueError in __post_init__ for empty hostname
        with pytest.raises(ValueError, match="Hostname cannot be empty"):
            WizardConfig(hostname="", timezone="UTC")

    def test_validate_wizard_config_invalid_hostname(self):
        """Test wizard configuration validation with invalid hostname format."""
        invalid_config = WizardConfig(hostname="test_host!", timezone="UTC")
        result = self.initial_setup._validate_wizard_config(invalid_config)
        assert result is False

    def test_validate_wizard_config_invalid_dns(self):
        """Test wizard configuration validation with invalid DNS server."""
        invalid_config = WizardConfig(
            hostname="test-host",
            timezone="UTC",
            dns_servers=["invalid.dns.server", "300.300.300.300"]
        )
        result = self.initial_setup._validate_wizard_config(invalid_config)
        assert result is False

    def test_generate_wizard_config_basic(self):
        """Test wizard configuration file generation with basic config."""
        # Mock the password hash methods
        with patch.object(self.initial_setup, '_get_admin_password_hash', return_value='test_admin_hash'):
            with patch.object(self.initial_setup, '_generate_maintenance_password_hash', return_value='test_maint_hash'):
                config_content = self.initial_setup._generate_wizard_config(self.wizard_config)
                
                # Verify key configuration elements
                assert "hostname=test-cp-gw" in config_content
                assert "timezone='America/New_York'" in config_content
                assert "ntp_primary=pool.ntp.org" in config_content
                assert "ntp_secondary=time.nist.gov" in config_content
                assert "primary=8.8.8.8" in config_content
                assert "secondary=8.8.4.4" in config_content
                assert "domainname=example.com" in config_content
                assert "admin_hash='test_admin_hash'" in config_content
                assert "maintenance_hash='test_maint_hash'" in config_content
                assert "install_security_gw=true" in config_content
                assert "install_security_managment=true" in config_content

    def test_generate_wizard_config_minimal(self):
        """Test wizard configuration file generation with minimal config."""
        minimal_config = WizardConfig(hostname="minimal-host")
        
        with patch.object(self.initial_setup, '_get_admin_password_hash', return_value='test_hash'):
            with patch.object(self.initial_setup, '_generate_maintenance_password_hash', return_value='test_maint'):
                config_content = self.initial_setup._generate_wizard_config(minimal_config)
                
                # Verify minimal configuration
                assert "hostname=minimal-host" in config_content
                assert "timezone='UTC'" in config_content
                assert "ntp_primary=ntp.checkpoint.com" in config_content
                assert "ntp_secondary=ntp2.checkpoint.com" in config_content

    def test_write_wizard_config_file_success(self):
        """Test successful wizard configuration file writing."""
        config_content = "test configuration content"
        
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.return_value = CommandResult(
            command="cat > /tmp/test.conf",
            success=True,
            output="File written successfully"
        )
        
        result = self.initial_setup._write_wizard_config_file(config_content)
        
        # Verify file path format
        assert result.startswith("/tmp/ftw_config_")
        assert result.endswith(".conf")
        
        # Verify connection manager calls
        self.mock_connection_manager.switch_to_expert.assert_called_once()
        self.mock_connection_manager.execute_command.assert_called_once()

    def test_write_wizard_config_file_expert_mode_failure(self):
        """Test wizard configuration file writing when expert mode switch fails."""
        config_content = "test configuration content"
        
        # Mock expert mode switch failure
        self.mock_connection_manager.switch_to_expert.return_value = False
        
        with pytest.raises(ConfigurationError, match="Failed to switch to expert mode"):
            self.initial_setup._write_wizard_config_file(config_content)

    def test_validate_wizard_config_file_success(self):
        """Test successful wizard configuration file validation."""
        config_file_path = "/tmp/test_config.conf"
        
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.return_value = CommandResult(
            command="config_system --dry-run -f /tmp/test_config.conf",
            success=True,
            output="Configuration validation successful"
        )
        
        result = self.initial_setup._validate_wizard_config_file(config_file_path)
        assert result is True

    def test_validate_wizard_config_file_validation_failure(self):
        """Test wizard configuration file validation failure."""
        config_file_path = "/tmp/test_config.conf"
        
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.return_value = CommandResult(
            command="config_system --dry-run -f /tmp/test_config.conf",
            success=True,
            output="Configuration validation Failed: Invalid parameter"
        )
        
        result = self.initial_setup._validate_wizard_config_file(config_file_path)
        assert result is False

    def test_apply_wizard_config_success(self):
        """Test successful wizard configuration application."""
        config_file_path = "/tmp/test_config.conf"
        
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.side_effect = [
            CommandResult(
                command="config_system -f /tmp/test_config.conf",
                success=True,
                output="Configuration applied successfully"
            ),
            CommandResult(
                command="rm -f /tmp/test_config.conf",
                success=True,
                output=""
            )
        ]
        
        result = self.initial_setup._apply_wizard_config(config_file_path)
        assert result is True

    def test_verify_wizard_completion_success(self):
        """Test successful wizard completion verification."""
        # Mock connection manager state detection
        self.mock_connection_manager.detect_state.return_value = CheckPointState.WIZARD_COMPLETE
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = self.initial_setup._verify_wizard_completion()
            assert result is True

    def test_verify_wizard_completion_failure(self):
        """Test wizard completion verification failure."""
        # Mock connection manager state detection
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = self.initial_setup._verify_wizard_completion()
            assert result is False

    def test_get_admin_password_hash_success(self):
        """Test successful admin password hash retrieval."""
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.return_value = CommandResult(
            command="dbget passwd:admin:passwd",
            success=True,
            output="$6$salt$hashedpassword"
        )
        
        result = self.initial_setup._get_admin_password_hash()
        assert result == "$6$salt$hashedpassword"

    def test_get_admin_password_hash_fallback(self):
        """Test admin password hash retrieval fallback."""
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.return_value = CommandResult(
            command="dbget passwd:admin:passwd",
            success=False,
            output=""
        )
        
        result = self.initial_setup._get_admin_password_hash()
        assert result == "$1$salt$hash"  # Default fallback

    def test_generate_maintenance_password_hash_success(self):
        """Test successful maintenance password hash generation."""
        # Mock connection manager methods
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.execute_command.return_value = CommandResult(
            command="echo -e 'admin\\nadmin\\n' | grub2-mkpasswd-pbkdf2",
            success=True,
            output="Enter password:\nReenter password:\nPBKDF2 hash of your password is grub.pbkdf2.sha512.10000.ABC123"
        )
        
        result = self.initial_setup._generate_maintenance_password_hash()
        assert result == "grub.pbkdf2.sha512.10000.ABC123"

    def test_validate_ip_address_valid(self):
        """Test IP address validation with valid addresses."""
        assert self.initial_setup._validate_ip_address("192.168.1.1") is True
        assert self.initial_setup._validate_ip_address("10.0.0.1") is True
        assert self.initial_setup._validate_ip_address("8.8.8.8") is True

    def test_validate_ip_address_invalid(self):
        """Test IP address validation with invalid addresses."""
        assert self.initial_setup._validate_ip_address("300.300.300.300") is False
        assert self.initial_setup._validate_ip_address("192.168.1") is False
        assert self.initial_setup._validate_ip_address("not.an.ip.address") is False
        assert self.initial_setup._validate_ip_address("") is False

    def test_validate_hostname_or_ip_valid(self):
        """Test hostname or IP validation with valid values."""
        assert self.initial_setup._validate_hostname_or_ip("example.com") is True
        assert self.initial_setup._validate_hostname_or_ip("test-host") is True
        assert self.initial_setup._validate_hostname_or_ip("192.168.1.1") is True
        assert self.initial_setup._validate_hostname_or_ip("ntp.pool.org") is True
        assert self.initial_setup._validate_hostname_or_ip("123") is True  # Numeric hostname is valid
        assert self.initial_setup._validate_hostname_or_ip("300.300.300.300") is True  # Valid hostname (not IP)

    def test_validate_hostname_or_ip_invalid(self):
        """Test hostname or IP validation with invalid values."""
        assert self.initial_setup._validate_hostname_or_ip("invalid_host!") is False
        assert self.initial_setup._validate_hostname_or_ip("host..name") is False  # Double dots invalid
        assert self.initial_setup._validate_hostname_or_ip("") is False
        assert self.initial_setup._validate_hostname_or_ip("-invalid") is False  # Can't start with hyphen

    @patch('checkpoint_automation.modules.initial_setup.time.sleep')
    def test_run_first_time_wizard_success(self, mock_sleep):
        """Test successful complete wizard automation flow."""
        # Mock all prerequisite methods
        self.initial_setup.validate_prerequisites = Mock(return_value=True)
        self.initial_setup._validate_wizard_config = Mock(return_value=True)
        self.initial_setup._generate_wizard_config = Mock(return_value="test config content")
        self.initial_setup._write_wizard_config_file = Mock(return_value="/tmp/test_config.conf")
        self.initial_setup._validate_wizard_config_file = Mock(return_value=True)
        self.initial_setup._apply_wizard_config = Mock(return_value=True)
        self.initial_setup._verify_wizard_completion = Mock(return_value=True)
        
        result = self.initial_setup.run_first_time_wizard(self.wizard_config)
        assert result is True
        
        # Verify all methods were called
        self.initial_setup.validate_prerequisites.assert_called_once()
        self.initial_setup._validate_wizard_config.assert_called_once_with(self.wizard_config)
        self.initial_setup._generate_wizard_config.assert_called_once_with(self.wizard_config)
        self.initial_setup._write_wizard_config_file.assert_called_once()
        self.initial_setup._validate_wizard_config_file.assert_called_once()
        self.initial_setup._apply_wizard_config.assert_called_once()
        self.initial_setup._verify_wizard_completion.assert_called_once()

    def test_run_first_time_wizard_prerequisites_failure(self):
        """Test wizard automation with prerequisites failure."""
        self.initial_setup.validate_prerequisites = Mock(return_value=False)
        
        with pytest.raises(ConfigurationError, match="Prerequisites not met"):
            self.initial_setup.run_first_time_wizard(self.wizard_config)

    def test_run_first_time_wizard_config_validation_failure(self):
        """Test wizard automation with configuration validation failure."""
        self.initial_setup.validate_prerequisites = Mock(return_value=True)
        self.initial_setup._validate_wizard_config = Mock(return_value=False)
        
        with pytest.raises(ValidationError, match="Invalid wizard configuration"):
            self.initial_setup.run_first_time_wizard(self.wizard_config)

    def test_run_first_time_wizard_config_file_validation_failure(self):
        """Test wizard automation with config file validation failure."""
        self.initial_setup.validate_prerequisites = Mock(return_value=True)
        self.initial_setup._validate_wizard_config = Mock(return_value=True)
        self.initial_setup._generate_wizard_config = Mock(return_value="test config")
        self.initial_setup._write_wizard_config_file = Mock(return_value="/tmp/test.conf")
        self.initial_setup._validate_wizard_config_file = Mock(return_value=False)
        
        with pytest.raises(ConfigurationError, match="Wizard configuration validation failed"):
            self.initial_setup.run_first_time_wizard(self.wizard_config)

    def test_run_first_time_wizard_application_failure(self):
        """Test wizard automation with configuration application failure."""
        self.initial_setup.validate_prerequisites = Mock(return_value=True)
        self.initial_setup._validate_wizard_config = Mock(return_value=True)
        self.initial_setup._generate_wizard_config = Mock(return_value="test config")
        self.initial_setup._write_wizard_config_file = Mock(return_value="/tmp/test.conf")
        self.initial_setup._validate_wizard_config_file = Mock(return_value=True)
        self.initial_setup._apply_wizard_config = Mock(return_value=False)
        
        with pytest.raises(ConfigurationError, match="Failed to apply wizard configuration"):
            self.initial_setup.run_first_time_wizard(self.wizard_config)

    def test_run_first_time_wizard_completion_verification_failure(self):
        """Test wizard automation with completion verification failure."""
        self.initial_setup.validate_prerequisites = Mock(return_value=True)
        self.initial_setup._validate_wizard_config = Mock(return_value=True)
        self.initial_setup._generate_wizard_config = Mock(return_value="test config")
        self.initial_setup._write_wizard_config_file = Mock(return_value="/tmp/test.conf")
        self.initial_setup._validate_wizard_config_file = Mock(return_value=True)
        self.initial_setup._apply_wizard_config = Mock(return_value=True)
        self.initial_setup._verify_wizard_completion = Mock(return_value=False)
        
        with pytest.raises(ConfigurationError, match="Wizard completion verification failed"):
            self.initial_setup.run_first_time_wizard(self.wizard_config)