"""
Simple expert password manag        try:
            # Try the expert command - use send_command_timing to handle different responses
            output = self.ssh.connection.send_command_timing("expert")
            
            if "enter expert password:" in output.lower():
                self.logger.info("Expert password is already set")
                # Cancel the password prompt with Ctrl+C
                self.ssh.connection.write_channel('\x03\n')
                return True, "Expert password is already set"
            elif "expert password has not been defined" in output.lower():
                self.logger.info("Expert password is not set")
                return False, "Expert password has not been defined"
            else:
                # Might already be in expert mode or other state
                self.logger.debug(f"Unexpected expert command output: {output}")
                return False, f"Could not determine expert password status from output: {output}"Point firewalls using netmiko.
Clean, focused implementation without legacy complexity.
"""

import logging
from typing import Tuple

from .ssh_connection import SSHConnectionManager
from .command_executor import FirewallMode


class ExpertPasswordManager:
    """Simple expert password manager using only netmiko methods."""
    
    def __init__(self, ssh_manager: SSHConnectionManager):
        """Initialize with SSH connection manager."""
        self.ssh = ssh_manager
        self.logger = ssh_manager.logger
    
    def is_expert_password_set(self) -> Tuple[bool, str]:
        """Check if expert password is already set.
        
        Returns:
            Tuple of (password_is_set, status_message)
        """
        self.logger.info("Checking if expert password is set")
        
        # Make sure we're in clish mode
        if self.ssh.get_current_mode() == FirewallMode.EXPERT:
            self.ssh.exit_expert_mode()
        
        try:
            # Try the expert command - use faster timing for responsiveness
            output = self.ssh.connection.send_command_timing(
                "expert", 
                last_read=1,
                read_timeout=self.ssh.config.read_timeout,
            )
            
            if "enter expert password:" in output.lower():
                message = "Expert password is already set"
                self.logger.info(message)
                # Cancel the password prompt with Ctrl+C
                self.ssh.connection.write_channel('\x03\n')
                return True, message
            elif "expert password has not been defined" in output.lower():
                message = "Expert password is not set"
                self.logger.info(message)
                return False, message
            else:
                # Might already be in expert mode or other state
                self.logger.debug(f"Unexpected expert command output: {output}")
                return False, "Could not determine expert password status"
                
        except Exception as e:
            self.logger.error(f"Error checking expert password status: {e}")
            return False, f"Error checking status: {str(e)}"
    
    def set_expert_password(self, password: str) -> bool:
        """
        Set the expert password, by sending the command `set expert-password` and entering the password twice.
        
        Args:
            password: New expert password to set
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Setting expert password")
        
        if len(password) < 6:
            self.logger.error("Password must be at least 6 characters")
            return False
        
        # Make sure we're in clish mode
        if self.ssh.get_current_mode() == FirewallMode.EXPERT:
            self.ssh.exit_expert_mode()
        
        try:
            # Step 1: Lock database
            self.logger.debug("Locking database")
            try:
                output_lock = self.ssh.connection.send_command_timing(
                    "lock database override",
                    last_read=1,
                    read_timeout=self.ssh.config.read_timeout
                )
                if "error" not in output_lock.lower():
                    self.logger.debug("Database lock acquired")
                else:
                    self.logger.warning("Database lock failed, continuing anyway")
            except Exception as e:
                self.logger.warning(f"Database lock command failed: {e}, continuing anyway")
            
            # Step 2: Start password setup using write_channel approach
            self.logger.debug("Starting set expert-password")
            import time
            
            self.ssh.connection.write_channel("set expert-password\n")
            time.sleep(0.5)
            output = self.ssh.connection.read_channel()
            
            # Check if we're being asked for current password (means password already exists)
            if "enter current expert password:" in output.lower():
                self.logger.warning("Expert password is already set")
                # Send Ctrl+C to abort
                self.ssh.connection.write_channel('\x03\n')
                return False
            
            # Check if we get the "Enter new expert password:" prompt (password not set)
            if "enter new expert password:" in output.lower():
                self.logger.debug("Got 'Enter new expert password' prompt - proceeding")
                
                # Step 3: Send first password
                self.logger.debug("Sending first password")
                self.ssh.connection.write_channel(f"{password}\n")
                time.sleep(0.5)
                
                # Step 4: Send confirmation password  
                self.logger.debug("Sending confirmation password")
                self.ssh.connection.write_channel(f"{password}\n")
                time.sleep(1)
                
                # Read final output
                final_output = self.ssh.connection.read_channel()
                output += final_output
            else:
                self.logger.error(f"Unexpected response to set expert-password: {output}")
                return False
            
            # Step 5: Check result
            if "error" in output.lower() or "failed" in output.lower():
                self.logger.error(f"Password setup failed: {output}")
                return False
            
            self.logger.info("Expert password set successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting expert password: {e}")
            return False
    
    def verify_expert_password(self, password: str) -> bool:
        """Verify expert password works by entering expert mode.
        
        Args:
            password: Password to verify
            
        Returns:
            True if password works, False otherwise
        """
        self.logger.info("Verifying expert password")
        
        try:
            # Try to enter expert mode
            if self.ssh.enter_expert_mode(password):
                self.logger.info("Expert password verified successfully")
                # Exit back to clish
                self.ssh.exit_expert_mode()
                return True
            else:
                self.logger.error("Expert password verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying expert password: {e}")
            return False
    
    def setup_expert_password(self, password: str) -> Tuple[bool, str]:
        """Complete expert password setup workflow.
        
        Args:
            password: Expert password to set
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info("Starting expert password setup workflow")
        
        try:
            # Check if expert password is already set
            is_set, status_msg = self.is_expert_password_set()
            if is_set:
                # It is already set, check it works
                if not self.verify_expert_password(password):
                    return False, "Expert password was already set but verification failed"
                return True, status_msg
            
            # Set the password
            if not self.set_expert_password(password):
                return False, "Failed to set expert password"
            
            # 3: Verify it works
            if not self.verify_expert_password(password):
                return False, "Expert password was set but verification failed"
            
            return True, "Expert password setup completed successfully"
            
        except Exception as e:
            error_msg = f"Expert password setup failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg