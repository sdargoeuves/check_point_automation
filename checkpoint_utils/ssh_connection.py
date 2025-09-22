"""Simplified SSH Connection Manager for Check Point firewalls using netmiko."""

import logging
import os
import re
import time
from logging.handlers import RotatingFileHandler
from typing import Optional

from netmiko import (
    ConnectHandler,
    NetMikoAuthenticationException,
    NetMikoTimeoutException,
)
from netmiko.exceptions import NetmikoBaseException

from .command_executor import FirewallMode
from .config import FirewallConfig


class SSHConnectionManager:
    """Simplified SSH connection manager using netmiko for Check Point firewalls."""

    def __init__(self, config: FirewallConfig):
        """Initialize SSH connection manager.

        Args:
            config: Firewall configuration containing connection details and logging level
        """
        self.config = config
        self.connection: Optional[ConnectHandler] = None
        self.logger = self._setup_logging()
        self.current_mode = FirewallMode.UNKNOWN

        # Device parameters for netmiko - only include valid ConnectHandler parameters
        self.device_params = {
            "device_type": "checkpoint_gaia",
            "host": self.config.ip_address,
            "username": self.config.username,
            "password": self.config.password,
            "timeout": self.config.timeout,
            "session_timeout": self.config.timeout,
        }

    def _setup_logging(self) -> logging.Logger:
        """Set up simplified logging configuration."""
        logger = logging.getLogger(f"checkpoint_utils.ssh.{self.config.ip_address}")

        # Prevent propagation to root logger to avoid double logging
        logger.propagate = False

        # Only add handlers if logger doesn't already have them
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            logs_dir = "logs"
            os.makedirs(logs_dir, exist_ok=True)

            log_file = os.path.join(logs_dir, f"checkpoint_{self.config.ip_address.replace('.', '_')}.log")

            # Use standard rotating file handler (simpler than custom compressed version)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=1 * 1024 * 1024,  # 1MB
                backupCount=5,
            )

            # Set up console handler for important messages
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.config.logging_level))

            # Create formatter
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(logging.DEBUG)  # File gets all messages, console filtered above

        return logger

    def connect(self, timeout: Optional[int] = None) -> bool:
        """Establish SSH connection to the firewall using netmiko.

        Args:
            timeout: Connection timeout in seconds (uses config.timeout if None)

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting to connect to {self.config.ip_address}")

            # Use provided timeout or fall back to config timeout
            actual_timeout = timeout or self.config.timeout

            # Update timeout in device parameters
            self.device_params.update(
                {
                    "timeout": actual_timeout,
                    "session_timeout": actual_timeout,
                }
            )

            # Create netmiko connection
            self.connection = ConnectHandler(**self.device_params)

            # Detect initial mode
            self.current_mode = self._detect_current_mode()

            self.logger.info(f"Successfully connected to {self.config.ip_address}")
            self.logger.info(f"Initial firewall mode detected: {self.current_mode.value}")

            return True

        except (
            NetMikoAuthenticationException,
            NetMikoTimeoutException,
            NetmikoBaseException,
        ) as e:
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
            self.connection.send_command("", expect_string=r"[>#]", read_timeout=self.config.read_timeout)
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

            if "[Expert@" in prompt and "]#" in prompt:
                self.logger.debug("Detected expert mode")
                return FirewallMode.EXPERT
            elif ">" in prompt:
                self.logger.debug("Detected clish mode")
                return FirewallMode.CLISH
            else:
                self.logger.debug(f"Unknown mode for prompt: '{prompt}'")
                return FirewallMode.UNKNOWN

        except Exception as e:
            self.logger.debug(f"Error detecting mode: {e}")
            return FirewallMode.UNKNOWN

    def get_current_mode(self) -> FirewallMode:
        """Get current firewall mode.

        Returns:
            Current firewall mode
        """
        # Refresh mode detection
        self.current_mode = self._detect_current_mode()
        return self.current_mode

    def wait_for_prompt(self, expected_prompt: str, timeout: Optional[int] = None) -> bool:
        """Wait for a specific prompt pattern using netmiko.

        Args:
            expected_prompt: Regex pattern for expected prompt
            timeout: Maximum time to wait (uses config.timeout if None)

        Returns:
            True if prompt detected within timeout
        """
        if not self.connection:
            return False

        try:
            # Use netmiko's read_until_prompt with custom pattern
            self.connection.read_until_pattern(pattern=expected_prompt, read_timeout=timeout or self.config.timeout)
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
                self.connection.write_channel(expert_password + "\n")

                # Give it time to process the full expert mode output
                time.sleep(1)

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
            self.connection.send_command_timing("exit", last_read=self.config.last_read, read_timeout=self.config.read_timeout)

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
