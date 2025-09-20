"""
Simplified SSH Connection Manager for Check Point firewalls using netmiko.
"""

import logging
import os
import time
from typing import Optional

from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
from netmiko.exceptions import NetmikoBaseException

from .config import FirewallConfig
from .command_executor import CommandResponse, FirewallMode


class SSHConnectionManager:
    """Simplified SSH connection manager using netmiko for Check Point firewalls."""
    
    def __init__(self, config: FirewallConfig, console_log_level: str = "INFO"):
        """Initialize SSH connection manager.
        
        Args:
            config: Firewall configuration containing connection details
            console_log_level: Log level for console output (DEBUG, INFO, WARNING, ERROR)
        """
        self.config = config
        self.connection: Optional[ConnectHandler] = None
        self.console_log_level = console_log_level
        self.logger = self._setup_logging()
        self.current_mode = FirewallMode.UNKNOWN
        
        # Device parameters for netmiko
        self.device_params = {
            'device_type': 'checkpoint_gaia',
            'host': self.config.ip_address,
            'username': self.config.username,
            'password': self.config.password,
            'timeout': 30,
            'session_timeout': 30,
            'read_timeout_override': 30,
            'keepalive': 30,
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Set up simplified logging configuration."""
        logger = logging.getLogger(f"checkpoint_automation.ssh.{self.config.ip_address}")
        
        # Prevent propagation to root logger to avoid double logging
        logger.propagate = False
        
        # Only add handlers if logger doesn't already have them
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            logs_dir = "logs"
            os.makedirs(logs_dir, exist_ok=True)
            
            log_file = os.path.join(logs_dir, f"checkpoint_{self.config.ip_address.replace('.', '_')}.log")
            
            # Use standard rotating file handler (simpler than custom compressed version)
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            
            # Set up console handler for important messages
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.console_log_level.upper()))
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(logging.DEBUG)  # File gets all messages, console filtered above
        
        return logger
    
    def connect(self, timeout: int = 30) -> bool:
        """Establish SSH connection to the firewall using netmiko.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting to connect to {self.config.ip_address}")
            
            # Update timeout in device parameters
            self.device_params.update({
                'timeout': timeout,
                'session_timeout': timeout,
                'read_timeout_override': timeout
            })
            
            # Create netmiko connection
            self.connection = ConnectHandler(**self.device_params)
            
            # Detect initial mode
            self.current_mode = self._detect_current_mode()
            
            self.logger.info(f"Successfully connected to {self.config.ip_address}")
            self.logger.info(f"Initial firewall mode detected: {self.current_mode.value}")
            
            return True
            
        except (NetMikoAuthenticationException, NetMikoTimeoutException, 
                NetmikoBaseException) as e:
            self.logger.error(f"Failed to connect to {self.config.ip_address}: {e}")
            self.disconnect()
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to {self.config.ip_address}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Close SSH connection and clean up resources."""
        try:
            if self.connection:
                self.connection.disconnect()
                self.connection = None
                self.logger.info(f"Disconnected from {self.config.ip_address}")
                
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
    
    def is_connected(self) -> bool:
        """Check if SSH connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.connection:
            return False
            
        try:
            # Test connection with a simple command
            self.connection.send_command("", expect_string=r'[>#]', read_timeout=5)
            return True
        except Exception:
            return False
    
    def wait_for_reconnect(self, max_attempts: int = 30, delay: int = 10) -> bool:
        """Wait for SSH to become available after reboot.
        
        Args:
            max_attempts: Maximum number of connection attempts
            delay: Delay between attempts in seconds
            
        Returns:
            True if reconnection successful, False otherwise
        """
        self.logger.info(f"Waiting for {self.config.ip_address} to become available after reboot")
        
        for attempt in range(max_attempts):
            self.logger.debug(f"Reconnection attempt {attempt + 1}/{max_attempts}")
            
            if self.connect():
                self.logger.info("Reconnection successful")
                return True
                
            time.sleep(delay)
        
        self.logger.error(f"Failed to reconnect after {max_attempts} attempts")
        return False
    
    def __enter__(self):
        """Context manager entry."""
        if not self.connect():
            raise ConnectionError(f"Failed to connect to {self.config.ip_address}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def execute_command(self, command: str, timeout: Optional[int] = None) -> CommandResponse:
        """Execute a command on the firewall using netmiko.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            CommandResponse object with results
            
        Raises:
            ConnectionError: If not connected to firewall
        """
        if not self.connection:
            raise ConnectionError("Not connected to firewall")
        
        self.logger.debug(f"Executing command: {command}")
        
        try:
            # Execute command using netmiko
            output = self.connection.send_command(
                command,
                read_timeout=timeout or 30,
                expect_string=r'[>#]'
            )
            
            # Update current mode after command execution
            self.current_mode = self._detect_current_mode()
            
            # Analyze response for errors
            success, error_message = self._analyze_response(output)
            
            response = CommandResponse(
                command=command,
                output=output,
                success=success,
                error_message=error_message,
                mode=self.current_mode
            )
            
            self.logger.debug(f"Command response - Success: {success}, Mode: {self.current_mode.value}")
            if not success and error_message:
                self.logger.warning(f"Command failed: {error_message}")
                
            return response
            
        except NetMikoTimeoutException:
            error_msg = f"Command '{command}' timed out after {timeout or 30} seconds"
            self.logger.error(error_msg)
            return CommandResponse(
                command=command,
                output="",
                success=False,
                error_message=error_msg,
                mode=self.current_mode
            )
        except Exception as e:
            error_msg = f"Error executing command '{command}': {str(e)}"
            self.logger.error(error_msg)
            return CommandResponse(
                command=command,
                output="",
                success=False,
                error_message=error_msg,
                mode=self.current_mode
            )
    
    def _detect_current_mode(self) -> FirewallMode:
        """Detect current firewall mode using netmiko's find_prompt method.
        
        Returns:
            Detected firewall mode
        """
        if not self.connection:
            return FirewallMode.UNKNOWN
            
        try:
            # Get current prompt using netmiko
            prompt = self.connection.find_prompt()
            
            # Analyze prompt to determine mode
            self.logger.debug(f"Analyzing prompt: '{prompt}'")
            
            if '[Expert@' in prompt and ']#' in prompt:
                self.logger.debug("Detected expert mode")
                return FirewallMode.EXPERT
            elif '>' in prompt:
                self.logger.debug("Detected clish mode")
                return FirewallMode.CLISH
            else:
                self.logger.debug(f"Unknown mode for prompt: '{prompt}'")
                return FirewallMode.UNKNOWN
                
        except Exception as e:
            self.logger.debug(f"Error detecting mode: {e}")
            return FirewallMode.UNKNOWN
    
    def _analyze_response(self, output: str) -> tuple[bool, Optional[str]]:
        """Analyze command response for success/failure indicators.
        
        Args:
            output: Command output to analyze
            
        Returns:
            Tuple of (success, error_message)
        """
        import re
        
        # Common Check Point error patterns
        error_patterns = [
            r'CLINFR\d+\s+(.+)',  # Check Point CLI error codes
            r'Error:\s*(.+)',
            r'Failed:\s*(.+)',
            r'Invalid\s+(.+)',
            r'command not found',
            r'Permission denied',
            r'Access denied',
        ]
        
        # Check for error patterns
        for pattern in error_patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                error_message = match.group(1) if match.groups() else match.group(0)
                return False, error_message.strip()
        
        # If no errors found, consider it successful
        return True, None
    
    def get_current_mode(self) -> FirewallMode:
        """Get current firewall mode.
        
        Returns:
            Current firewall mode
        """
        # Refresh mode detection
        self.current_mode = self._detect_current_mode()
        return self.current_mode
    
    def detect_mode(self) -> FirewallMode:
        """Detect current firewall mode by refreshing prompt.
        
        Returns:
            Detected firewall mode
        """
        return self._detect_current_mode()
    
    def wait_for_prompt(self, expected_prompt: str, timeout: int = 30) -> bool:
        """Wait for a specific prompt pattern using netmiko.
        
        Args:
            expected_prompt: Regex pattern for expected prompt
            timeout: Maximum time to wait
            
        Returns:
            True if prompt detected within timeout
        """
        if not self.connection:
            return False
            
        try:
            # Use netmiko's read_until_prompt with custom pattern
            self.connection.read_until_pattern(
                pattern=expected_prompt,
                read_timeout=timeout
            )
            return True
        except Exception as e:
            self.logger.debug(f"Timeout waiting for prompt '{expected_prompt}': {e}")
            return False
    
    def enter_expert_mode(self, expert_password: str) -> bool:
        """Enter expert mode using netmiko's send_command_timing.
        
        Args:
            expert_password: Expert mode password
            
        Returns:
            True if successfully entered expert mode
        """
        if not self.connection:
            raise ConnectionError("Not connected to firewall")
        
        self.logger.info("Attempting to enter expert mode")
        
        # Check if already in expert mode
        if self.get_current_mode() == FirewallMode.EXPERT:
            self.logger.info("Already in expert mode")
            return True
        
        try:
            # Send expert command and wait for password prompt
            self.logger.debug("Sending expert command")
            output = self.connection.send_command_timing("expert")
            self.logger.debug(f"Expert command output: {output}")
            
            # Check if password prompt appeared
            if "enter expert password:" in output.lower():
                # Send password directly using write_channel (no waiting)
                self.logger.debug("Sending expert password")
                self.connection.write_channel(expert_password + '\n')
                
                # Give it time to process the full expert mode output
                time.sleep(2)
                
                # Read the output to see what happened
                expert_output = self.connection.send_command_timing("")
                self.logger.debug(f"Expert mode output: {expert_output}")
                
                self.logger.debug("Password sent successfully")
                
                # Verify we're in expert mode
                if self._detect_current_mode() == FirewallMode.EXPERT:
                    self.logger.info("Successfully entered expert mode")
                    return True
                else:
                    self.logger.error("Failed to verify expert mode entry")
                    self.logger.debug(f"Current prompt after expert entry: {self.connection.find_prompt()}")
                    return False
            else:
                self.logger.error(f"Unexpected response to expert command: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error entering expert mode: {e}")
            return False
    
    def exit_expert_mode(self) -> bool:
        """Exit expert mode back to clish using netmiko.
        
        Returns:
            True if successfully exited expert mode
        """
        if not self.connection:
            raise ConnectionError("Not connected to firewall")
        
        # Check current mode
        current_mode = self.get_current_mode()
        if current_mode == FirewallMode.CLISH:
            self.logger.debug("Already in clish mode")
            return True
        
        if current_mode != FirewallMode.EXPERT:
            self.logger.debug("Not in expert mode, no need to exit")
            return True
        
        self.logger.info("Attempting to exit expert mode")
        
        try:
            # Send exit command using netmiko
            self.connection.send_command_timing("exit")
            
            # Verify we're back in clish mode
            if self._detect_current_mode() == FirewallMode.CLISH:
                self.logger.info("Successfully exited expert mode to clish")
                return True
            else:
                self.logger.error("Failed to verify exit to clish mode")
                return False
                
        except Exception as e:
            self.logger.error(f"Error exiting expert mode: {e}")
            return False
