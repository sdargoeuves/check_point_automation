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
        self.ssh_manager = ssh_manager
        logger.debug("UserManager initialized")

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
            logger.debug(f"Setting password for user: {username}")

            # Use write_channel approach that works reliably
            self.ssh_manager.connection.write_channel(f"set user {username} password\n")
            time.sleep(1)

            # Read initial output
            output = self.ssh_manager.connection.read_channel()
            logger.debug(f"Password prompt output: {output}")

            # Check for password prompt
            if "new password:" in output.lower() or "password:" in output.lower():
                # Send first password
                self.ssh_manager.connection.write_channel(f"{password}\n")
                time.sleep(1)

                # Send confirmation password
                self.ssh_manager.connection.write_channel(f"{password}\n")
                time.sleep(2)

                # Read final result
                final_output = self.ssh_manager.connection.read_channel()
                logger.debug(f"Password setting result: {final_output}")

                # Check for errors
                combined_output = output + final_output
                if "error" in combined_output.lower() or "failed" in combined_output.lower():
                    logger.error(f"Error setting password for {username}: {combined_output}")
                    return False

                logger.info(f"Password set successfully for user: {username}")
                return True
            else:
                logger.error(f"No password prompt detected for {username}: {output}")
                return False

        except Exception:
            logger.exception(f"Exception setting password for {username}")
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
            logger.debug(f"Setting up SSH key for user: {username}")

            # Use heredoc approach that works reliably (from vagrant script)
            self.ssh_manager.connection.write_channel(f"cat > /home/{username}/.ssh/authorized_keys << 'EOF'\n")
            time.sleep(0.5)
            self.ssh_manager.connection.write_channel(f"{public_key}\n")
            time.sleep(0.5)
            self.ssh_manager.connection.write_channel("EOF\n")
            time.sleep(1)

            # Read output to check for errors
            output = self.ssh_manager.connection.read_channel()
            logger.debug(f"SSH key setup output: {output}")

            if "error" in output.lower() or "failed" in output.lower():
                logger.error(f"Error setting up SSH key for {username}: {output}")
                return False

            logger.info(f"SSH key configured successfully for user: {username}")
            return True

        except Exception:
            logger.exception(f"Exception setting up SSH key for {username}")
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
            logger.debug(f"Checking if user exists: {username}")

            # Use the SSH manager's execute_command method
            command = f"show user {username}"
            logger.debug(f"Executing user check command: {command}")

            result = self.ssh_manager.execute_command(command, timeout=15)

            if not result.success:
                logger.error(f"Command failed: {result.error_message}")
                return False

            output = result.output
            logger.debug(f"User check raw output length: {len(output)} chars")
            logger.debug(f"User check output: '{output}'")

            # Check if user exists based on output content
            # Look for the user's home directory pattern which indicates user exists
            home_dir_pattern = f"/home/{username}"
            logger.debug(f"Looking for home directory pattern: '{home_dir_pattern}'")

            if home_dir_pattern in output:
                # User exists - found home directory pattern
                logger.info(f"✓ User {username} EXISTS - found home directory pattern: {home_dir_pattern}")
                # Additional user details could be extracted here if needed
                return True
            elif "No database items for user" in output:
                # User does not exist - explicit message
                logger.info(f"∅ User {username} does NOT exist - output contains 'No database items for user'")
                return False
            elif output.strip() == "":
                # Empty output also means user doesn't exist
                logger.info(f"∅ User {username} does NOT exist - empty output")
                return False
            else:
                # Unclear output - assume user doesn't exist for safety
                logger.warning(f"⚠️ Unclear output for user {username} check: '{output}' - assuming user does not exist")
                return False

        except Exception:
            logger.exception(f"Exception checking user existence for {username}")
            return False, ""
