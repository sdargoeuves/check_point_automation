"""
Integration tests for the initial setup module.

These tests demonstrate how the expert password setup functionality
would work with a real connection manager implementation.
"""

import pytest
from unittest.mock import Mock, patch

from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.models import (
    CheckPointState, CLIMode, CommandResult, ConnectionInfo
)
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError


class MockConnectionManager:
    """Mock connection manager for integration testing."""
    
    def __init__(self):
        self.connected = False
        self.current_state = CheckPointState.FRESH_INSTALL
        self.current_mode = CLIMode.CLISH
        self.expert_password = None
        
    def is_connected(self):
        return self.connected
        
    def detect_state(self):
        return self.current_state
        
    def get_cli_mode(self):
        return self.current_mode
        
    def switch_to_clish(self):
        self.current_mode = CLIMode.CLISH
        return True
        
    def switch_to_expert(self, password):
        if self.expert_password == password:
            self.current_mode = CLIMode.EXPERT
            return True
        return False
        
    def execute_command(self, command, mode=None):
        if command == "set expert-password":
            self._step = 1
            return CommandResult(
                command=command,
                success=True,
                output="Enter new expert password: "
            )
        elif hasattr(self, '_step') and self._step == 1:
            # First password entry
            self._password = command
            self._step = 2
            return CommandResult(
                command=command,
                success=True,
                output=""  # Empty output is normal after first password
            )
        elif hasattr(self, '_step') and self._step == 2:
            # Password confirmation
            if command == self._password:
                # Passwords match - set expert password
                self.expert_password = command
                self._step = None
                return CommandResult(
                    command=command,
                    success=True,
                    output="gw-123456> "  # Back to prompt
                )
            else:
                # Passwords don't match
                return CommandResult(
                    command=command,
                    success=True,
                    output="Passwords do not match, try again"
                )
        
        return CommandResult(
            command=command,
            success=True,
            output="Command executed"
        )


class TestInitialSetupIntegration:
    """Integration tests for initial setup functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = MockConnectionManager()
        self.mock_connection_manager.connected = True
        self.initial_setup = InitialSetupModule(self.mock_connection_manager)
    
    def test_expert_password_setup_end_to_end(self):
        """Test complete expert password setup workflow."""
        password = "TestPass123!"
        
        # Execute the expert password setup
        result = self.initial_setup.set_expert_password(password)
        
        # Verify success
        assert result is True
        
        # Verify password was set in mock
        assert self.mock_connection_manager.expert_password == password
        
        # Verify we can switch to expert mode with the password
        assert self.mock_connection_manager.switch_to_expert(password) is True
    
    def test_expert_password_setup_with_weak_password(self):
        """Test expert password setup with weak password."""
        weak_password = "weak"
        
        # Should raise ValidationError for weak password
        with pytest.raises(ValidationError, match="Password does not meet strength requirements"):
            self.initial_setup.set_expert_password(weak_password)
    
    def test_expert_password_setup_not_connected(self):
        """Test expert password setup when not connected."""
        password = "TestPass123!"
        self.mock_connection_manager.connected = False
        
        # Should raise ConfigurationError for not being connected
        with pytest.raises(ConfigurationError, match="Prerequisites not met"):
            self.initial_setup.set_expert_password(password)
    
    def test_expert_password_setup_wrong_state(self):
        """Test expert password setup in wrong state."""
        password = "TestPass123!"
        self.mock_connection_manager.current_state = CheckPointState.FULLY_CONFIGURED
        
        # Should raise ConfigurationError for wrong state
        with pytest.raises(ConfigurationError, match="Prerequisites not met"):
            self.initial_setup.set_expert_password(password)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration
        valid_config = {"expert_password": "TestPass123!"}
        assert self.initial_setup.validate_config(valid_config) is True
        
        # Invalid configuration - missing password
        invalid_config = {}
        assert self.initial_setup.validate_config(invalid_config) is False
        
        # Invalid configuration - weak password
        weak_config = {"expert_password": "weak"}
        assert self.initial_setup.validate_config(weak_config) is False
    
    def test_get_current_config(self):
        """Test getting current configuration state."""
        config = self.initial_setup.get_current_config()
        
        expected = {
            "state": "fresh",
            "cli_mode": "clish",
            "expert_password_set": False,
            "wizard_completed": False
        }
        
        assert config == expected
    
    def test_password_strength_validation_comprehensive(self):
        """Test comprehensive password strength validation."""
        # Valid passwords
        valid_passwords = [
            "TestPass123!",
            "MySecure@Pass1",
            "Complex#Password9",
            "Strong$Pass123"
        ]
        
        for password in valid_passwords:
            assert self.initial_setup._validate_password_strength(password) is True
        
        # Invalid passwords (only length matters now)
        invalid_passwords = [
            "short",  # Too short (less than 6 characters)
            "tiny",   # Too short
            "",       # Empty
            "12345",  # Exactly 5 characters (too short)
        ]
        
        for password in invalid_passwords:
            assert self.initial_setup._validate_password_strength(password) is False
            
        # Valid passwords (6+ characters)
        more_valid_passwords = [
            "simple",
            "123456",
            "admin15",
            "nouppercase123!",  # Now valid since we only check length
            "NOLOWERCASE123!",  # Now valid
            "NoDigits!",        # Now valid
            "NoSpecialChars123" # Now valid
        ]
        
        for password in more_valid_passwords:
            assert self.initial_setup._validate_password_strength(password) is True

    def test_admin_password_update_integration(self):
        """Test admin password update integration scenario."""
        connection_manager = MockConnectionManager()
        connection_manager.connected = True
        connection_manager.current_state = CheckPointState.EXPERT_PASSWORD_SET
        initial_setup = InitialSetupModule(connection_manager)
        
        # Test admin password update with valid password
        new_password = "NewAdminPass123!"
        
        # Mock the verification method to return True
        with patch.object(initial_setup, '_verify_admin_password_change', return_value=True):
            result = initial_setup.update_admin_password(new_password)
            assert result is True
        
        # Test with weak password
        weak_password = "weak"
        with pytest.raises(ValidationError):
            initial_setup.update_admin_password(weak_password)
        
        # Test when not connected
        connection_manager.connected = False
        with pytest.raises(ConfigurationError):
            initial_setup.update_admin_password(new_password)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])