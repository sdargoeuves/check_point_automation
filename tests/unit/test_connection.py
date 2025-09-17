"""
Unit tests for CheckPointConnectionManager.
"""

import time
import unittest.mock
from unittest.mock import MagicMock, Mock, patch

import paramiko
import pytest

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.exceptions import AuthenticationError, ConnectionError
from checkpoint_automation.core.models import CheckPointState, CLIMode, ConnectionInfo


class TestCheckPointConnectionManager:
    """Test cases for CheckPointConnectionManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = CheckPointConnectionManager(max_retries=2, base_delay=0.1, max_delay=1.0)
        self.connection_info = ConnectionInfo(
            host="test.example.com",
            username="admin",
            password="admin",
            port=22,
            timeout=30
        )

    def test_init_with_retry_config(self):
        """Test initialization with retry configuration."""
        manager = CheckPointConnectionManager(max_retries=5, base_delay=2.0, max_delay=60.0)
        assert manager._max_retries == 5
        assert manager._base_delay == 2.0
        assert manager._max_delay == 60.0
        assert manager._auto_reconnect is True

    def test_calculate_retry_delay(self):
        """Test retry delay calculation with exponential backoff."""
        # Test exponential backoff
        delay_0 = self.manager._calculate_retry_delay(0)
        delay_1 = self.manager._calculate_retry_delay(1)
        delay_2 = self.manager._calculate_retry_delay(2)
        
        # Should increase exponentially (with jitter, so approximate)
        assert 0.1 <= delay_0 <= 0.2  # base_delay ± jitter
        assert 0.15 <= delay_1 <= 0.3  # 2 * base_delay ± jitter
        assert 0.3 <= delay_2 <= 0.6   # 4 * base_delay ± jitter

    def test_calculate_retry_delay_max_cap(self):
        """Test that retry delay is capped at max_delay."""
        # Large attempt number should be capped
        delay = self.manager._calculate_retry_delay(10)
        assert delay <= self.manager._max_delay * 1.25  # Allow for jitter

    @patch('checkpoint_automation.core.connection.paramiko.SSHClient')
    def test_connect_success(self, mock_ssh_class):
        """Test successful connection."""
        # Mock SSH client and shell
        mock_ssh = Mock()
        mock_shell = Mock()
        mock_ssh.invoke_shell.return_value = mock_shell
        mock_shell.recv_ready.return_value = False
        mock_ssh_class.return_value = mock_ssh

        # Mock CLI mode and state detection
        with patch.object(self.manager, 'get_cli_mode', return_value=CLIMode.CLISH), \
             patch.object(self.manager, 'detect_state', return_value=CheckPointState.FRESH_INSTALL), \
             patch.object(self.manager, '_read_shell_output', return_value="Welcome"):

            result = self.manager.connect(self.connection_info)

            assert result is True
            assert self.manager._connection_info == self.connection_info
            mock_ssh.connect.assert_called_once()

    @patch('checkpoint_automation.core.connection.paramiko.SSHClient')
    def test_connect_authentication_failure(self, mock_ssh_class):
        """Test connection with authentication failure."""
        mock_ssh = Mock()
        mock_ssh.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_class.return_value = mock_ssh

        with pytest.raises(AuthenticationError):
            self.manager.connect(self.connection_info)

    @patch('checkpoint_automation.core.connection.paramiko.SSHClient')
    def test_connect_ssh_failure(self, mock_ssh_class):
        """Test connection with SSH failure."""
        mock_ssh = Mock()
        mock_ssh.connect.side_effect = paramiko.SSHException("SSH failed")
        mock_ssh_class.return_value = mock_ssh

        with pytest.raises(ConnectionError):
            self.manager.connect(self.connection_info)

    def test_is_connected_with_timeout(self):
        """Test connection check with session timeout."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        
        # Set last activity to trigger timeout
        self.manager._last_activity_time = time.time() - 400  # 400 seconds ago
        self.manager._session_timeout = 300  # 5 minutes
        
        with patch.object(self.manager, '_reconnect', return_value=True) as mock_reconnect:
            result = self.manager.is_connected()
            mock_reconnect.assert_called_once()

    def test_set_auto_reconnect(self):
        """Test setting auto-reconnect flag."""
        self.manager.set_auto_reconnect(False)
        assert self.manager._auto_reconnect is False
        
        self.manager.set_auto_reconnect(True)
        assert self.manager._auto_reconnect is True

    def test_set_session_timeout(self):
        """Test setting session timeout."""
        self.manager.set_session_timeout(600)
        assert self.manager._session_timeout == 600

    @patch('checkpoint_automation.core.connection.time.sleep')
    def test_execute_with_retry_success_on_first_attempt(self, mock_sleep):
        """Test retry mechanism when operation succeeds on first attempt."""
        mock_func = Mock(return_value="success")
        
        result = self.manager._execute_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        mock_sleep.assert_not_called()

    @patch('checkpoint_automation.core.connection.time.sleep')
    def test_execute_with_retry_success_on_second_attempt(self, mock_sleep):
        """Test retry mechanism when operation succeeds on second attempt."""
        mock_func = Mock(side_effect=[ConnectionError("Connection lost"), "success"])
        
        with patch.object(self.manager, 'is_connected', return_value=True), \
             patch.object(self.manager, '_reconnect', return_value=True):
            
            result = self.manager._execute_with_retry(mock_func, "arg1")
            
            assert result == "success"
            assert mock_func.call_count == 2
            mock_sleep.assert_called_once()

    @patch('checkpoint_automation.core.connection.time.sleep')
    def test_execute_with_retry_all_attempts_fail(self, mock_sleep):
        """Test retry mechanism when all attempts fail."""
        mock_func = Mock(side_effect=ConnectionError("Persistent error"))
        
        with patch.object(self.manager, 'is_connected', return_value=False), \
             patch.object(self.manager, '_reconnect', return_value=False):
            
            with pytest.raises(ConnectionError, match="Persistent error"):
                self.manager._execute_with_retry(mock_func, "arg1")
            
            assert mock_func.call_count == 3  # Initial + 2 retries
            assert mock_sleep.call_count == 2  # 2 retry delays

    def test_execute_with_retry_non_retryable_error(self):
        """Test that non-retryable errors are not retried."""
        mock_func = Mock(side_effect=ValueError("Invalid argument"))
        
        with pytest.raises(ValueError, match="Invalid argument"):
            self.manager._execute_with_retry(mock_func, "arg1")
        
        mock_func.assert_called_once()

    @patch('checkpoint_automation.core.connection.paramiko.SSHClient')
    def test_reconnect_success(self, mock_ssh_class):
        """Test successful reconnection."""
        # Set up initial connection info
        self.manager._connection_info = self.connection_info
        
        # Mock successful reconnection
        with patch.object(self.manager, 'disconnect') as mock_disconnect, \
             patch.object(self.manager, 'connect', return_value=True) as mock_connect:
            
            result = self.manager._reconnect()
            
            assert result is True
            mock_disconnect.assert_called_once()
            mock_connect.assert_called_once_with(self.connection_info)

    def test_reconnect_no_connection_info(self):
        """Test reconnection when no connection info is stored."""
        self.manager._connection_info = None
        
        result = self.manager._reconnect()
        
        assert result is False

    def test_reconnect_failure(self):
        """Test failed reconnection."""
        self.manager._connection_info = self.connection_info
        
        with patch.object(self.manager, 'disconnect'), \
             patch.object(self.manager, 'connect', return_value=False):
            
            result = self.manager._reconnect()
            
            assert result is False

    def test_execute_command_with_retry(self):
        """Test that execute_command uses retry mechanism."""
        with patch.object(self.manager, '_execute_with_retry') as mock_retry, \
             patch.object(self.manager, '_execute_command_internal', return_value="result") as mock_internal:
            
            result = self.manager.execute_command("test command", CLIMode.CLISH)
            
            mock_retry.assert_called_once_with(mock_internal, "test command", CLIMode.CLISH)

    def test_activity_time_updates(self):
        """Test that activity time is updated during operations."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        
        initial_time = self.manager._last_activity_time
        
        # Mock CLI mode detection to update activity time
        with patch.object(self.manager, '_read_shell_output', return_value="test output"):
            self.manager.get_cli_mode()
        
        # Activity time should be updated
        assert self.manager._last_activity_time > initial_time

    def test_get_cli_mode_clish_detection(self):
        """Test CLI mode detection for CLISH mode."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        
        # Mock bash command returning invalid command error (CLISH mode)
        with patch.object(self.manager, '_read_shell_output', return_value="Invalid command:'bash'"):
            mode = self.manager.get_cli_mode()
            
        assert mode == CLIMode.CLISH
        assert self.manager._current_cli_mode == CLIMode.CLISH

    def test_get_cli_mode_expert_detection(self):
        """Test CLI mode detection for Expert mode."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        
        # Mock bash command working and showing expert prompt
        with patch.object(self.manager, '_read_shell_output', return_value="[Expert@hostname:0]#"):
            mode = self.manager.get_cli_mode()
            
        assert mode == CLIMode.EXPERT
        assert self.manager._current_cli_mode == CLIMode.EXPERT

    def test_get_cli_mode_fallback_to_prompt_detection(self):
        """Test CLI mode detection fallback to prompt pattern."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        
        # Mock bash command with unclear output, then prompt detection
        with patch.object(self.manager, '_read_shell_output', side_effect=["unclear output", "[Expert@hostname:0]#"]):
            mode = self.manager.get_cli_mode()
            
        assert mode == CLIMode.EXPERT
        assert self.manager._current_cli_mode == CLIMode.EXPERT

    def test_get_cli_mode_clish_prompt_detection(self):
        """Test CLI mode detection for CLISH using prompt pattern."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        
        # Mock bash command with unclear output, then CLISH prompt detection
        with patch.object(self.manager, '_read_shell_output', side_effect=["unclear output", "hostname>"]):
            mode = self.manager.get_cli_mode()
            
        assert mode == CLIMode.CLISH
        assert self.manager._current_cli_mode == CLIMode.CLISH

    def test_get_cli_mode_not_connected(self):
        """Test CLI mode detection when not connected."""
        # Ensure not connected
        self.manager._ssh_client = None
        self.manager._shell = None
        
        with pytest.raises(ConnectionError, match="Not connected to Check Point VM"):
            self.manager.get_cli_mode()

    def test_switch_to_expert_success(self):
        """Test successful switch to expert mode."""
        # Mock connected state in CLISH mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        # Mock password prompt and successful switch
        with patch.object(self.manager, '_read_shell_output', return_value="Password:"), \
             patch.object(self.manager, 'get_cli_mode', return_value=CLIMode.EXPERT):
            
            result = self.manager.switch_to_expert("expert_password")
            
        assert result is True
        self.manager._shell.send.assert_any_call("expert\n")
        self.manager._shell.send.assert_any_call("expert_password\n")

    def test_switch_to_expert_already_in_expert(self):
        """Test switch to expert when already in expert mode."""
        # Mock connected state in expert mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.EXPERT
        
        result = self.manager.switch_to_expert("expert_password")
        
        assert result is True
        # Should not send any commands
        self.manager._shell.send.assert_not_called()

    def test_switch_to_expert_no_password_prompt(self):
        """Test switch to expert when no password prompt appears."""
        # Mock connected state in CLISH mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        # Mock no password prompt
        with patch.object(self.manager, '_read_shell_output', return_value="No password prompt"):
            
            result = self.manager.switch_to_expert("expert_password")
            
        assert result is False

    def test_switch_to_expert_failed_authentication(self):
        """Test switch to expert with failed authentication."""
        # Mock connected state in CLISH mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        # Mock password prompt but failed switch
        with patch.object(self.manager, '_read_shell_output', return_value="Password:"), \
             patch.object(self.manager, 'get_cli_mode', return_value=CLIMode.CLISH):
            
            result = self.manager.switch_to_expert("wrong_password")
            
        assert result is False

    def test_switch_to_expert_not_connected(self):
        """Test switch to expert when not connected."""
        # Ensure not connected
        self.manager._ssh_client = None
        self.manager._shell = None
        
        with pytest.raises(ConnectionError, match="Not connected to Check Point VM"):
            self.manager.switch_to_expert("expert_password")

    def test_switch_to_clish_success(self):
        """Test successful switch to CLISH mode."""
        # Mock connected state in expert mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.EXPERT
        
        # Mock successful switch
        with patch.object(self.manager, 'get_cli_mode', return_value=CLIMode.CLISH):
            
            result = self.manager.switch_to_clish()
            
        assert result is True
        self.manager._shell.send.assert_called_once_with("exit\n")

    def test_switch_to_clish_already_in_clish(self):
        """Test switch to CLISH when already in CLISH mode."""
        # Mock connected state in CLISH mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        result = self.manager.switch_to_clish()
        
        assert result is True
        # Should not send any commands
        self.manager._shell.send.assert_not_called()

    def test_switch_to_clish_failed(self):
        """Test failed switch to CLISH mode."""
        # Mock connected state in expert mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.EXPERT
        
        # Mock failed switch (still in expert mode)
        with patch.object(self.manager, 'get_cli_mode', return_value=CLIMode.EXPERT):
            
            result = self.manager.switch_to_clish()
            
        assert result is False

    def test_switch_to_clish_not_connected(self):
        """Test switch to CLISH when not connected."""
        # Ensure not connected
        self.manager._ssh_client = None
        self.manager._shell = None
        
        with pytest.raises(ConnectionError, match="Not connected to Check Point VM"):
            self.manager.switch_to_clish()

    def test_execute_command_with_mode_switching_to_expert(self):
        """Test command execution with automatic mode switching to expert."""
        # Mock connected state in CLISH mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        # Mock successful mode switch and command execution
        with patch.object(self.manager, 'switch_to_expert', return_value=True) as mock_switch, \
             patch.object(self.manager, '_read_shell_output', return_value="Command output"), \
             patch.object(self.manager, 'is_connected', return_value=True):
            
            result = self.manager._execute_command_internal("test command", CLIMode.EXPERT)
            
        assert result.success is True
        assert result.command == "test command"
        assert "Command output" in result.output
        mock_switch.assert_called_once()

    def test_execute_command_with_mode_switching_to_clish(self):
        """Test command execution with automatic mode switching to CLISH."""
        # Mock connected state in expert mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.EXPERT
        
        # Mock successful mode switch and command execution
        with patch.object(self.manager, 'switch_to_clish', return_value=True) as mock_switch, \
             patch.object(self.manager, '_read_shell_output', return_value="Command output"), \
             patch.object(self.manager, 'is_connected', return_value=True):
            
            result = self.manager._execute_command_internal("test command", CLIMode.CLISH)
            
        assert result.success is True
        assert result.command == "test command"
        assert "Command output" in result.output
        mock_switch.assert_called_once()

    def test_execute_command_mode_switch_failure(self):
        """Test command execution when mode switching fails."""
        # Mock connected state in CLISH mode
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        # Mock failed mode switch
        with patch.object(self.manager, 'switch_to_expert', return_value=False), \
             patch.object(self.manager, 'is_connected', return_value=True):
            
            result = self.manager._execute_command_internal("test command", CLIMode.EXPERT)
            
        assert result.success is False
        assert result.error == "Failed to switch to expert mode"

    def test_command_execution_handles_check_point_syntax(self):
        """Test that command execution properly handles Check Point specific syntax and responses."""
        # Mock connected state
        self.manager._ssh_client = Mock()
        self.manager._shell = Mock()
        self.manager._shell.closed = False
        self.manager._connection_info = self.connection_info
        self.manager._current_cli_mode = CLIMode.CLISH
        
        # Test various Check Point specific responses
        test_cases = [
            ("show version", "R81.20", True),  # Successful command
            ("invalid_command", "Invalid command:'invalid_command'", False),  # Invalid command
            ("show interfaces", "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>", True),  # Interface info
            ("set hostname test", "Failed to set hostname", False),  # Failed configuration
        ]
        
        for command, output, expected_success in test_cases:
            with patch.object(self.manager, '_read_shell_output', return_value=output), \
                 patch.object(self.manager, 'is_connected', return_value=True):
                
                result = self.manager._execute_command_internal(command)
                
                assert result.success == expected_success
                assert result.command == command
                assert output in result.output

    def test_execute_clish_command_convenience_method(self):
        """Test the convenience method for executing CLISH commands."""
        with patch.object(self.manager, 'execute_command') as mock_execute:
            mock_execute.return_value = Mock()
            
            self.manager.execute_clish_command("show version")
            
            mock_execute.assert_called_once_with("show version", CLIMode.CLISH)

    def test_execute_expert_command_convenience_method(self):
        """Test the convenience method for executing Expert commands."""
        with patch.object(self.manager, 'execute_command') as mock_execute:
            mock_execute.return_value = Mock()
            
            self.manager.execute_expert_command("ls -la")
            
            mock_execute.assert_called_once_with("ls -la", CLIMode.EXPERT)