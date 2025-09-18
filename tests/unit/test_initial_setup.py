"""
Unit tests for the initial setup module.

This module tests the expert password setup functionality and other
initial setup operations for Check Point VMs.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.models import (
    CheckPointState, CLIMode, CommandResult, SystemStatus, WizardConfig
)
from checkpoint_automation.core.exceptions import (
    ConfigurationError, ValidationError, AuthenticationError
)


class TestInitialSetupModule:
    """Test cases for InitialSetupModule."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_init(self):
        """Test module initialization."""
        assert self.initial_setup.connection_manager == self.mock_connection_manager
        assert hasattr(self.initial_setup, 'logger')

    def test_validate_prerequisites_success(self):
        """Test successful prerequisite validation."""
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        
        result = self.initial_setup.validate_prerequisites()
        
        assert result is True
        self.mock_connection_manager.is_connected.assert_called_once()
        self.mock_connection_manager.detect_state.assert_called_once()

    def test_validate_prerequisites_not_connected(self):
        """Test prerequisite validation when not connected."""
        self.mock_connection_manager.is_connected.return_value = False
        
        result = self.initial_setup.validate_prerequisites()
        
        assert result is False
        self.mock_connection_manager.is_connected.assert_called_once()

    def test_validate_prerequisites_invalid_state(self):
        """Test prerequisite validation with invalid state."""
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FULLY_CONFIGURED
        
        result = self.initial_setup.validate_prerequisites()
        
        assert result is False

    def test_get_current_config_success(self):
        """Test successful current config retrieval."""
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        config = self.initial_setup.get_current_config()
        
        expected = {
            "state": "fresh",
            "cli_mode": "clish",
            "expert_password_set": False,
            "wizard_completed": False
        }
        assert config == expected

    def test_get_current_config_exception(self):
        """Test current config retrieval with exception."""
        self.mock_connection_manager.detect_state.side_effect = Exception("Test error")
        
        config = self.initial_setup.get_current_config()
        
        assert config == {}

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config = {"expert_password": "TestPass123!"}
        
        result = self.initial_setup.validate_config(config)
        
        assert result is True

    def test_validate_config_missing_key(self):
        """Test configuration validation with missing key."""
        config = {}
        
        result = self.initial_setup.validate_config(config)
        
        assert result is False

    def test_validate_config_weak_password(self):
        """Test configuration validation with weak password."""
        config = {"expert_password": "weak"}
        
        result = self.initial_setup.validate_config(config)
        
        assert result is False


class TestSetExpertPassword:
    """Test cases for set_expert_password method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_set_expert_password_success(self):
        """Test successful expert password setup."""
        password = "admin15"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        # Mock the 3-step command execution sequence
        step1_result = CommandResult(
            command="set expert-password",
            success=True,
            output="Enter new expert password: "
        )
        step2_result = CommandResult(
            command=password,
            success=True,
            output=""
        )
        step3_result = CommandResult(
            command=password,
            success=True,
            output="gw-123456> "
        )
        
        self.mock_connection_manager.execute_command.side_effect = [
            step1_result, step2_result, step3_result
        ]
        
        # Mock expert mode verification
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.switch_to_clish.return_value = True
        
        result = self.initial_setup.set_expert_password(password)
        
        assert result is True
        assert self.mock_connection_manager.execute_command.call_count == 3
        self.mock_connection_manager.switch_to_expert.assert_called_with(password)

    def test_set_expert_password_prerequisites_fail(self):
        """Test expert password setup with failed prerequisites."""
        password = "TestPass123!"
        
        self.mock_connection_manager.is_connected.return_value = False
        
        with pytest.raises(ConfigurationError, match="Prerequisites not met"):
            self.initial_setup.set_expert_password(password)

    def test_set_expert_password_weak_password(self):
        """Test expert password setup with weak password."""
        password = "weak"  # Less than 6 characters
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        
        with pytest.raises(ValidationError, match="Password does not meet strength requirements"):
            self.initial_setup.set_expert_password(password)

    def test_set_expert_password_command_failure(self):
        """Test expert password setup with command failure."""
        password = "TestPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        # Mock command execution failure
        command_result = CommandResult(
            command="set expert-password",
            success=False,
            output="",
            error="Command failed"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        with pytest.raises(ConfigurationError, match="Expert password setup failed"):
            self.initial_setup.set_expert_password(password)

    def test_set_expert_password_verification_failure(self):
        """Test expert password setup with verification failure."""
        password = "admin15"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        # Mock successful command execution sequence
        step1_result = CommandResult(
            command="set expert-password",
            success=True,
            output="Enter new expert password: "
        )
        step2_result = CommandResult(
            command=password,
            success=True,
            output=""
        )
        step3_result = CommandResult(
            command=password,
            success=True,
            output="gw-123456> "
        )
        
        self.mock_connection_manager.execute_command.side_effect = [
            step1_result, step2_result, step3_result
        ]
        
        # Mock verification failure
        self.mock_connection_manager.switch_to_expert.return_value = False
        
        with pytest.raises(ConfigurationError, match="Expert password verification failed"):
            self.initial_setup.set_expert_password(password)

    def test_set_expert_password_mode_switch_required(self):
        """Test expert password setup when mode switch is required."""
        password = "admin15"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.EXPERT
        self.mock_connection_manager.switch_to_clish.return_value = True
        
        # Mock successful command execution sequence
        step1_result = CommandResult(
            command="set expert-password",
            success=True,
            output="Enter new expert password: "
        )
        step2_result = CommandResult(
            command=password,
            success=True,
            output=""
        )
        step3_result = CommandResult(
            command=password,
            success=True,
            output="gw-123456> "
        )
        
        self.mock_connection_manager.execute_command.side_effect = [
            step1_result, step2_result, step3_result
        ]
        
        # Mock expert mode verification
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.switch_to_clish.return_value = True
        
        result = self.initial_setup.set_expert_password(password)
        
        assert result is True
        self.mock_connection_manager.switch_to_clish.assert_called()

    def test_set_expert_password_mode_switch_failure(self):
        """Test expert password setup when mode switch fails."""
        password = "TestPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.FRESH_INSTALL
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.EXPERT
        self.mock_connection_manager.switch_to_clish.return_value = False
        
        with pytest.raises(ConfigurationError, match="Failed to switch to clish mode"):
            self.initial_setup.set_expert_password(password)


class TestPasswordValidation:
    """Test cases for password validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_validate_password_strength_valid(self):
        """Test password validation with valid password."""
        password = "TestPass123!"
        
        result = self.initial_setup._validate_password_strength(password)
        
        assert result is True

    def test_validate_password_strength_too_short(self):
        """Test password validation with too short password."""
        password = "short"  # Less than 6 characters
        
        result = self.initial_setup._validate_password_strength(password)
        
        assert result is False

    def test_validate_password_strength_valid_simple(self):
        """Test password validation with simple valid passwords."""
        passwords = ["admin15", "testpass", "123456", "simple"]
        
        for password in passwords:
            result = self.initial_setup._validate_password_strength(password)
            assert result is True

    def test_validate_password_strength_minimum_length(self):
        """Test password validation with minimum length."""
        password = "123456"  # Exactly 6 characters
        
        result = self.initial_setup._validate_password_strength(password)
        
        assert result is True

    def test_validate_password_strength_complex_still_valid(self):
        """Test that complex passwords are still valid."""
        password = "TestPassword123!"
        
        result = self.initial_setup._validate_password_strength(password)
        
        assert result is True

    def test_validate_password_strength_empty(self):
        """Test password validation with empty password."""
        password = ""
        
        result = self.initial_setup._validate_password_strength(password)
        
        assert result is False


class TestExpertPasswordCommand:
    """Test cases for expert password command execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_execute_expert_password_command_simple(self):
        """Test expert password command execution without proper prompts."""
        password = "admin15"
        
        # Mock command that doesn't contain the expected password prompt
        command_result = CommandResult(
            command="set expert-password",
            success=True,
            output="Password set successfully"  # Missing "Enter new expert password"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        result = self.initial_setup._execute_expert_password_command(password)
        
        assert result.success is False
        assert "Expected password prompt not found" in result.error
        self.mock_connection_manager.execute_command.assert_called_once_with(
            "set expert-password", CLIMode.CLISH
        )

    def test_execute_expert_password_command_with_prompts(self):
        """Test expert password command execution with proper prompts."""
        password = "admin15"
        
        # Mock initial command response with password prompt
        initial_result = CommandResult(
            command="set expert-password",
            success=True,
            output="Enter new expert password: "
        )
        
        # Mock password entry response (empty output is normal)
        password_result = CommandResult(
            command=password,
            success=True,
            output=""
        )
        
        # Mock final confirmation response with success
        confirm_result = CommandResult(
            command=password,
            success=True,
            output="gw-123456> "  # Back to prompt indicates success
        )
        
        self.mock_connection_manager.execute_command.side_effect = [
            initial_result, password_result, confirm_result
        ]
        
        result = self.initial_setup._execute_expert_password_command(password)
        
        assert result.success is True
        assert self.mock_connection_manager.execute_command.call_count == 3

    def test_verify_expert_password_success(self):
        """Test successful expert password verification."""
        password = "TestPass123!"
        
        self.mock_connection_manager.switch_to_expert.return_value = True
        self.mock_connection_manager.switch_to_clish.return_value = True
        
        result = self.initial_setup._verify_expert_password(password)
        
        assert result is True
        self.mock_connection_manager.switch_to_expert.assert_called_with(password)
        self.mock_connection_manager.switch_to_clish.assert_called_once()

    def test_verify_expert_password_failure(self):
        """Test expert password verification failure."""
        password = "TestPass123!"
        
        self.mock_connection_manager.switch_to_expert.return_value = False
        
        result = self.initial_setup._verify_expert_password(password)
        
        assert result is False

    def test_verify_expert_password_exception(self):
        """Test expert password verification with exception."""
        password = "TestPass123!"
        
        self.mock_connection_manager.switch_to_expert.side_effect = Exception("Test error")
        
        result = self.initial_setup._verify_expert_password(password)
        
        assert result is False


class TestUpdateAdminPassword:
    """Test cases for update_admin_password method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_update_admin_password_success(self):
        """Test successful admin password update."""
        new_password = "NewPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        # Mock command execution
        command_result = CommandResult(
            command="set user admin password",
            success=True,
            output="Password updated successfully"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        # Mock password verification
        with patch.object(self.initial_setup, '_verify_admin_password_change', return_value=True):
            result = self.initial_setup.update_admin_password(new_password)
        
        assert result is True
        self.mock_connection_manager.execute_command.assert_called()

    def test_update_admin_password_prerequisites_fail(self):
        """Test admin password update with failed prerequisites."""
        new_password = "NewPass123!"
        
        self.mock_connection_manager.is_connected.return_value = False
        
        with pytest.raises(ConfigurationError, match="Prerequisites not met"):
            self.initial_setup.update_admin_password(new_password)

    def test_update_admin_password_weak_password(self):
        """Test admin password update with weak password."""
        new_password = "weak"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        
        with pytest.raises(ValidationError, match="New password does not meet strength requirements"):
            self.initial_setup.update_admin_password(new_password)

    def test_update_admin_password_command_failure(self):
        """Test admin password update with command failure."""
        new_password = "NewPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        # Mock command execution failure
        command_result = CommandResult(
            command="set user admin password",
            success=False,
            output="",
            error="Command failed"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        with pytest.raises(ConfigurationError, match="Admin password update failed"):
            self.initial_setup.update_admin_password(new_password)

    def test_update_admin_password_verification_failure(self):
        """Test admin password update with verification failure."""
        new_password = "NewPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.CLISH
        
        # Mock successful command execution
        command_result = CommandResult(
            command="set user admin password",
            success=True,
            output="Password updated successfully"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        # Mock verification failure
        with patch.object(self.initial_setup, '_verify_admin_password_change', return_value=False):
            with pytest.raises(ConfigurationError, match="Admin password verification failed"):
                self.initial_setup.update_admin_password(new_password)

    def test_update_admin_password_mode_switch_required(self):
        """Test admin password update when mode switch is required."""
        new_password = "NewPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.EXPERT
        self.mock_connection_manager.switch_to_clish.return_value = True
        
        # Mock command execution
        command_result = CommandResult(
            command="set user admin password",
            success=True,
            output="Password updated successfully"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        # Mock password verification
        with patch.object(self.initial_setup, '_verify_admin_password_change', return_value=True):
            result = self.initial_setup.update_admin_password(new_password)
        
        assert result is True
        self.mock_connection_manager.switch_to_clish.assert_called()

    def test_update_admin_password_mode_switch_failure(self):
        """Test admin password update when mode switch fails."""
        new_password = "NewPass123!"
        
        # Mock prerequisites validation
        self.mock_connection_manager.is_connected.return_value = True
        self.mock_connection_manager.detect_state.return_value = CheckPointState.EXPERT_PASSWORD_SET
        self.mock_connection_manager.get_cli_mode.return_value = CLIMode.EXPERT
        self.mock_connection_manager.switch_to_clish.return_value = False
        
        with pytest.raises(ConfigurationError, match="Failed to switch to clish mode"):
            self.initial_setup.update_admin_password(new_password)


class TestAdminPasswordCommand:
    """Test cases for admin password command execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_execute_admin_password_command_simple(self):
        """Test simple admin password command execution."""
        new_password = "NewPass123!"
        
        command_result = CommandResult(
            command="set user admin password",
            success=True,
            output="Password updated successfully"
        )
        self.mock_connection_manager.execute_command.return_value = command_result
        
        result = self.initial_setup._execute_admin_password_command(new_password)
        
        assert result.success is True
        self.mock_connection_manager.execute_command.assert_called_once_with(
            "set user admin password", CLIMode.CLISH
        )

    def test_execute_admin_password_command_with_prompts(self):
        """Test admin password command execution with interactive prompts."""
        new_password = "NewPass123!"
        
        # Mock initial command response with password prompt
        initial_result = CommandResult(
            command="set user admin password",
            success=True,
            output="Enter new password:"
        )
        
        # Mock password entry response with confirmation prompt
        password_result = CommandResult(
            command=new_password,
            success=True,
            output="Confirm password:"
        )
        
        # Mock final confirmation response
        confirm_result = CommandResult(
            command=new_password,
            success=True,
            output="Password updated successfully"
        )
        
        self.mock_connection_manager.execute_command.side_effect = [
            initial_result, password_result, confirm_result
        ]
        
        result = self.initial_setup._execute_admin_password_command(new_password)
        
        assert result.success is True
        assert self.mock_connection_manager.execute_command.call_count == 3

    @patch('checkpoint_automation.core.connection.CheckPointConnectionManager')
    @patch('checkpoint_automation.core.models.ConnectionInfo')
    def test_verify_admin_password_change_success(self, mock_connection_info, mock_connection_manager_class):
        """Test successful admin password change verification."""
        new_password = "NewPass123!"
        
        # Mock current connection info
        self.mock_connection_manager.connection_info.host = "192.168.1.1"
        self.mock_connection_manager.connection_info.port = 22
        
        # Mock test connection manager
        mock_test_connection_manager = Mock()
        mock_test_connection_manager.connect.return_value = True
        mock_connection_manager_class.return_value = mock_test_connection_manager
        
        result = self.initial_setup._verify_admin_password_change(new_password)
        
        assert result is True
        mock_test_connection_manager.connect.assert_called_once()
        mock_test_connection_manager.disconnect.assert_called_once()

    @patch('checkpoint_automation.core.connection.CheckPointConnectionManager')
    @patch('checkpoint_automation.core.models.ConnectionInfo')
    def test_verify_admin_password_change_failure(self, mock_connection_info, mock_connection_manager_class):
        """Test admin password change verification failure."""
        new_password = "NewPass123!"
        
        # Mock current connection info
        self.mock_connection_manager.connection_info.host = "192.168.1.1"
        self.mock_connection_manager.connection_info.port = 22
        
        # Mock test connection manager
        mock_test_connection_manager = Mock()
        mock_test_connection_manager.connect.return_value = False
        mock_connection_manager_class.return_value = mock_test_connection_manager
        
        result = self.initial_setup._verify_admin_password_change(new_password)
        
        assert result is False

    @patch('checkpoint_automation.core.connection.CheckPointConnectionManager')
    def test_verify_admin_password_change_exception(self, mock_connection_manager_class):
        """Test admin password change verification with exception."""
        new_password = "NewPass123!"
        
        # Mock current connection info
        self.mock_connection_manager.connection_info.host = "192.168.1.1"
        self.mock_connection_manager.connection_info.port = 22
        
        # Mock exception during connection manager creation
        mock_connection_manager_class.side_effect = Exception("Test error")
        
        result = self.initial_setup._verify_admin_password_change(new_password)
        
        assert result is False


class TestNotImplementedMethods:
    """Test cases for methods that are not yet implemented."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)

    def test_run_first_time_wizard_implemented(self):
        """Test that first-time wizard is now implemented."""
        config = WizardConfig(hostname="test-host")
        
        # Since the method is now implemented, it should raise ConfigurationError
        # when prerequisites are not met (which they won't be in this mock setup)
        with pytest.raises(ConfigurationError):
            self.initial_setup.run_first_time_wizard(config)

    def test_verify_initial_setup_not_implemented(self):
        """Test that initial setup verification raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Initial setup verification not yet implemented"):
            self.initial_setup.verify_initial_setup()