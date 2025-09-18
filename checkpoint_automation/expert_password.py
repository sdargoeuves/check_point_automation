"""
Expert password setup workflow for Check Point firewalls.
"""

import logging
import time
from typing import Tuple, Optional

from .ssh_connection import SSHConnectionManager
from .command_executor import CommandResponse, FirewallMode


class ExpertPasswordManager:
    """Manages expert password setup workflow for Check Point firewalls."""
    
    def __init__(self, ssh_manager: SSHConnectionManager):
        """Initialize expert password manager.
        
        Args:
            ssh_manager: Active SSH connection manager
        """
        self.ssh_manager = ssh_manager
        self.logger = ssh_manager.logger
        
    def check_expert_password_status(self) -> Tuple[bool, str]:
        """Check if expert password is already set by parsing 'expert' command output.
        
        Returns:
            Tuple of (password_is_set, status_message)
        """
        self.logger.info("Checking expert password status")
        
        # Ensure we're in clish mode
        current_mode = self.ssh_manager.get_current_mode()
        if current_mode == FirewallMode.EXPERT:
            self.logger.debug("Currently in expert mode, exiting to clish first")
            if not self.ssh_manager.exit_expert_mode():
                return False, "Failed to exit expert mode to check password status"
        
        # Send expert command to check status
        response = self.ssh_manager.execute_command("expert", timeout=5)
        
        if not response.success:
            return False, f"Failed to execute expert command: {response.error_message}"
        
        output = response.output.lower()
        
        # Check for password not set indicator
        if "expert password has not been defined" in output:
            self.logger.info("Expert password is not set")
            return False, "Expert password has not been defined"
        
        # Check for password prompt (indicates password is set)
        if "enter expert password:" in output:
            self.logger.info("Expert password is already set")
            # Send Ctrl+C to cancel the password prompt
            self.ssh_manager.shell.send('\x03')  # Ctrl+C
            time.sleep(0.5)
            # Send newline to get back to prompt
            self.ssh_manager.shell.send('\n')
            time.sleep(0.5)
            return True, "Expert password is already set"
        
        # Check if we're already in expert mode (shouldn't happen but handle it)
        if response.mode == FirewallMode.EXPERT:
            self.logger.info("Already in expert mode, password was set")
            return True, "Already in expert mode"
        
        # If we can't determine status, assume not set
        self.logger.warning(f"Could not determine expert password status from output: {output[:200]}")
        return False, "Could not determine expert password status"
    
    def set_expert_password(self, new_password: str) -> Tuple[bool, str]:
        """Set expert password using 'set expert-password' command.
        
        Args:
            new_password: New expert password to set
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info("Setting expert password")
        
        # Validate password length
        if len(new_password) < 6:
            return False, "Expert password must be at least 6 characters long"
        
        # Ensure we're in clish mode
        current_mode = self.ssh_manager.get_current_mode()
        if current_mode == FirewallMode.EXPERT:
            self.logger.debug("Currently in expert mode, exiting to clish first")
            if not self.ssh_manager.exit_expert_mode():
                return False, "Failed to exit expert mode"
        
        # Acquire database lock first (always do this to be safe)
        self.logger.info("Acquiring database lock before setting expert password")
        lock_success, lock_message = self._acquire_database_lock()
        if not lock_success:
            return False, f"Failed to acquire database lock: {lock_message}"
        
        # Send the set expert-password command and handle the interactive prompts
        self.logger.debug("Sending set expert-password command")
        self.ssh_manager.shell.send("set expert-password\n")
        
        # Handle password prompts
        success, message = self._handle_password_prompts(new_password)
        if not success:
            return False, message
        
        self.logger.info("Expert password set successfully")
        return True, "Expert password set successfully"
    
    def _acquire_database_lock(self) -> Tuple[bool, str]:
        """Acquire database lock using 'lock database override' command.
        
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.debug("Acquiring database lock")
        
        response = self.ssh_manager.execute_command("lock database override", timeout=5)
        
        if response.success:
            self.logger.debug("Database lock acquired successfully")
            return True, "Database lock acquired"
        else:
            self.logger.error(f"Failed to acquire database lock: {response.error_message}")
            return False, response.error_message or "Failed to acquire database lock"
    
    def _handle_password_prompts(self, password: str) -> Tuple[bool, str]:
        """Handle password entry and confirmation prompts - bulletproof approach.
        
        Args:
            password: Password to enter
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.debug("Handling password prompts - bulletproof approach")
        
        try:
            all_output = ""
            
            # Step 1: Wait for first password prompt and send password
            self.logger.debug("Step 1: Waiting for first password prompt")
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.ssh_manager.shell.recv_ready():
                    chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                    all_output += chunk
                    self.logger.debug(f"Received: '{chunk}'")
                    
                    if "password" in chunk.lower() and ":" in chunk:
                        self.logger.debug("First password prompt detected, sending password")
                        self.ssh_manager.shell.send(password + '\n')
                        break
                else:
                    time.sleep(0.1)
            
            # Step 2: IGNORE PROMPT DETECTION - just send password again after a moment
            self.logger.debug("Step 2: Sending password again (ignoring prompt detection)")
            time.sleep(0.5)  # Brief pause
            self.ssh_manager.shell.send(password + '\n')
            
            # Step 3: Read all output and if nothing immediate, press enter
            self.logger.debug("Step 3: Reading output, will press enter if needed")
            time.sleep(0.5)  # Brief pause to let output come
            
            # Read whatever is available
            read_start = time.time()
            while time.time() - read_start < 2:
                if self.ssh_manager.shell.recv_ready():
                    chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                    all_output += chunk
                    self.logger.debug(f"Additional output: '{chunk}'")
                else:
                    break
            
            # If we don't see a prompt, press enter to get one
            if ">" not in all_output and "#" not in all_output:
                self.logger.debug("No prompt seen, pressing enter")
                self.ssh_manager.shell.send('\n')
                time.sleep(0.5)
                
                # Read final output
                if self.ssh_manager.shell.recv_ready():
                    chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                    all_output += chunk
                    self.logger.debug(f"Final output after enter: '{chunk}'")
            
            self.logger.debug(f"Complete session output: '{all_output}'")
            
            # Check for errors
            if "error" in all_output.lower() or "failed" in all_output.lower():
                return False, f"Password setup failed: {all_output}"
            
            # If we got this far, assume success
            return True, "Password setup completed"
            
        except Exception as e:
            self.logger.error(f"Error handling password prompts: {e}")
            return False, f"Error handling password prompts: {str(e)}"
    
    def setup_expert_password_workflow(self, expert_password: str) -> Tuple[bool, str]:
        """Complete expert password setup workflow.
        
        This is the main function that orchestrates the entire expert password setup process:
        1. Check if expert password is already set
        2. If not set, set the expert password
        3. Verify the password was set correctly
        
        Args:
            expert_password: Expert password to set
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info("Starting expert password setup workflow")
        
        try:
            # Step 1: Check current expert password status
            password_set, status_message = self.check_expert_password_status()
            
            if password_set:
                self.logger.info("Expert password is already set, no action needed")
                return True, "Expert password is already set"
            
            # Step 2: Set expert password
            self.logger.info("Expert password not set, proceeding to set it")
            set_success, set_message = self.set_expert_password(expert_password)
            
            if not set_success:
                return False, f"Failed to set expert password: {set_message}"
            
            # Step 3: Verify password was set by trying to enter expert mode
            self.logger.info("Verifying expert password was set correctly")
            verify_success, verify_message = self._verify_expert_password(expert_password)
            
            if not verify_success:
                return False, f"Expert password verification failed: {verify_message}"
            
            self.logger.info("Expert password setup workflow completed successfully")
            return True, "Expert password setup completed successfully"
            
        except Exception as e:
            error_message = f"Expert password setup workflow failed: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _verify_expert_password(self, expert_password: str) -> Tuple[bool, str]:
        """Verify expert password was set correctly by attempting to enter expert mode.
        
        Args:
            expert_password: Expert password to verify
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.debug("Verifying expert password by entering expert mode")
        
        try:
            # Ensure we're in clish mode first
            current_mode = self.ssh_manager.get_current_mode()
            if current_mode == FirewallMode.EXPERT:
                if not self.ssh_manager.exit_expert_mode():
                    return False, "Failed to exit expert mode for verification"
            
            # Try to enter expert mode with the password
            if self.ssh_manager.enter_expert_mode(expert_password):
                self.logger.debug("Successfully entered expert mode, password verification passed")
                
                # Exit back to clish mode
                if self.ssh_manager.exit_expert_mode():
                    return True, "Expert password verified successfully"
                else:
                    return True, "Expert password verified (but failed to exit expert mode)"
            else:
                return False, "Failed to enter expert mode with provided password"
                
        except Exception as e:
            self.logger.error(f"Error verifying expert password: {e}")
            return False, f"Error during password verification: {str(e)}"