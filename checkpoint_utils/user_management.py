#!/usr/bin/env python3
"""
CheckPoint User Management Module
Handles user creation, password setting, and SSH key configuration.
"""

import logging
import time

from .ssh_connection import SSHConnectionManager

logger = logging.getLogger(__name__)


class UserManager:
    """
    Manages user operations on CheckPoint firewalls.
    Follows the same pattern as ExpertPasswordManager.
    """

    def __init__(self, ssh_manager: SSHConnectionManager):
        """
        Initialize UserManager with SSH connection.

        Args:
            ssh_manager: Connected SSH manager
        """

        self.ssh = ssh_manager
        self.logger = ssh_manager.logger
        self.logger.debug("UserManager initialized")

    def set_user_password(self, username: str, password: str) -> bool:
        """
        Set user password using interactive command pattern.

        Args:
            username: Username to set password for
            password: Password to set

        Returns:
            True if password was set successfully, False otherwise
        """
        try:
            self.logger.debug(f"Setting password for user: {username}")

            # Use write_channel approach that works reliably
            self.ssh.connection.write_channel(f"set user {username} password\n")
            time.sleep(1)

            # Read initial output
            output = self.ssh.connection.read_channel()
            self.logger.debug(f"Password prompt output: {output}")

            # Check for password prompt
            if "new password:" in output.lower() or "password:" in output.lower():
                # Send first password
                self.ssh.connection.write_channel(f"{password}\n")
                time.sleep(1)

                # Send confirmation password
                self.ssh.connection.write_channel(f"{password}\n")
                time.sleep(2)

                # Read final result
                final_output = self.ssh.connection.read_channel()
                self.logger.debug(f"Password setting result: {final_output}")

                # Check for errors
                combined_output = output + final_output
                if "error" in combined_output.lower() or "failed" in combined_output.lower():
                    self.logger.error(f"Error setting password for {username}: {combined_output}")
                    return False

                self.logger.info(f"Password set successfully for user: {username}")
                return True
            else:
                self.logger.error(f"No password prompt detected for {username}: {output}")
                return False

        except Exception:
            self.logger.exception(f"Exception setting password for {username}")
            return False

    def setup_ssh_key(self, username: str, public_key: str) -> bool:
        """
        Set up SSH public key for user using heredoc pattern.

        Args:
            username: Username to configure SSH key for
            public_key: SSH public key content

        Returns:
            True if SSH key was configured successfully, False otherwise
        """
        try:
            self.logger.debug(f"Setting up SSH key for user: {username}")

            # Use heredoc approach that works reliably (from vagrant script)
            self.ssh.connection.write_channel(f"cat > /home/{username}/.ssh/authorized_keys << 'EOF'\n")
            time.sleep(0.5)
            self.ssh.connection.write_channel(f"{public_key}\n")
            time.sleep(0.5)
            self.ssh.connection.write_channel("EOF\n")
            time.sleep(1)

            # Read output to check for errors
            output = self.ssh.connection.read_channel()
            self.logger.debug(f"SSH key setup output: {output}")

            if "error" in output.lower() or "failed" in output.lower():
                self.logger.error(f"Error setting up SSH key for {username}: {output}")
                return False

            self.logger.info(f"SSH key configured successfully for user: {username}")
            return True

        except Exception:
            self.logger.exception(f"Exception setting up SSH key for {username}")
            return False

    def user_exists(self, username: str) -> bool:
        """
        Check if a user exists on the firewall using direct netmiko approach.

        Args:
            username: Username to check

        Returns:
            Tuple of (exists: bool, info: str)
            - exists: True if user exists, False otherwise
            - info: User information if exists, or empty string if not
        """
        try:
            self.logger.debug(f"Checking if user exists: {username}")

            # Use direct netmiko method for user check
            command = f"show user {username}"
            self.logger.debug(f"Executing user check command: {command}")

            output = self.ssh.connection.send_command_timing(
                command,
                last_read=self.ssh.config.last_read,
                read_timeout=self.ssh.config.read_timeout,
            )
            self.logger.debug(f"User check raw output length: {len(output)} chars")
            self.logger.debug(f"User check output repr: {repr(output)}")

            # Check if output contains only the command echo (indicates incomplete response)
            if output.strip().endswith(command):
                self.logger.warning("Output appears to be just command echo - possibly incomplete response")
                self.logger.warning(f"Expected to see response data after: '{command}'")

            self.logger.debug(f"User check output: '{output}'")

            # Check if user exists based on output content
            # Look for the user's home directory pattern which indicates user exists
            home_dir_pattern = f"/home/{username}"
            self.logger.debug(f"##DEBUG## Looking for home directory pattern: '{home_dir_pattern}'")
            self.logger.debug(f"##DEBUG## in the output:\n{output}")

            if home_dir_pattern in output:
                # User exists - found home directory pattern
                self.logger.info(f"✓ User {username} EXISTS - found home directory pattern: {home_dir_pattern}")
                # Additional user details could be extracted here if needed
                return True
            elif "No database items for user" in output:
                # User does not exist - explicit message
                self.logger.info(f"∅ User {username} does NOT exist - output contains 'No database items for user'")
                return False
            elif output.strip() == "":
                # Empty output also means user doesn't exist
                self.logger.info(f"∅ User {username} does NOT exist - empty output")
                return False
            else:
                # Unclear output - assume user doesn't exist for safety
                self.logger.warning(
                    f"⚠️ Unclear output for user {username} check: '{output}' - assuming user does not exist"
                )
                return False

        except Exception:
            self.logger.exception(f"Exception checking user existence for {username}")
            return False, ""
