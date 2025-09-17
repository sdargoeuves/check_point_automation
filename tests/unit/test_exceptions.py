"""
Unit tests for Check Point automation exceptions.
"""

from checkpoint_automation.core.exceptions import (
    AuthenticationError,
    CheckPointError,
    ConfigurationError,
    ConnectionError,
    StateError,
    ValidationError,
)


class TestCheckPointError:
    """Test base CheckPointError exception."""

    def test_basic_exception(self):
        """Test creating basic exception."""
        error = CheckPointError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}

    def test_exception_with_details(self):
        """Test creating exception with details."""
        details = {"host": "192.168.1.100", "command": "test"}
        error = CheckPointError("Test error", details)

        assert error.message == "Test error"
        assert error.details == details
        assert "Details:" in str(error)
        assert "host=192.168.1.100" in str(error)


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_connection_error(self):
        """Test ConnectionError exception."""
        error = ConnectionError("SSH connection failed")
        assert isinstance(error, CheckPointError)
        assert str(error) == "SSH connection failed"

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Invalid configuration")
        assert isinstance(error, CheckPointError)
        assert str(error) == "Invalid configuration"

    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Validation failed")
        assert isinstance(error, CheckPointError)
        assert str(error) == "Validation failed"

    def test_state_error(self):
        """Test StateError exception."""
        error = StateError("Unexpected state")
        assert isinstance(error, CheckPointError)
        assert str(error) == "Unexpected state"

    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        error = AuthenticationError("Authentication failed")
        assert isinstance(error, ConnectionError)
        assert isinstance(error, CheckPointError)
        assert str(error) == "Authentication failed"
