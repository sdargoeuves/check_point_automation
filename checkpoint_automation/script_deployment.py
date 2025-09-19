"""
Script deployment and execution for Check Point firewalls.
"""

import logging
import time
import base64
import os
from typing import Tuple, Optional

from .ssh_connection import SSHConnectionManager
from .command_executor import CommandResponse, FirewallMode


class ScriptDeploymentManager:
    """Manages script deployment and execution for Check Point firewalls."""
    
    def __init__(self, ssh_manager: SSHConnectionManager):
        """Initialize script deployment manager.
        
        Args:
            ssh_manager: Active SSH connection manager
        """
        self.ssh_manager = ssh_manager
        self.logger = ssh_manager.logger
        self.script_path = "/home/admin/initial_config.sh"
        
    def deploy_and_execute_script(self, script_content: str) -> Tuple[bool, str]:
        """Deploy bash script content to firewall filesystem and execute it.
        
        This function implements requirements 2.1-2.4:
        - 2.1: Create a new file on the firewall filesystem
        - 2.2: Copy the entire content of the provided bash script
        - 2.3: Make the file executable using chmod +x
        - 2.4: Execute the bash script
        
        IMPORTANT: All operations are performed in expert mode as it's the only mode
        with access to the bash shell and filesystem operations.
        
        Args:
            script_content: Content of the bash script to deploy and execute
            
        Returns:
            Tuple of (success, output_or_error_message)
        """
        self.logger.info("Starting script deployment and execution in expert mode")
        
        if not script_content or not script_content.strip():
            return False, "Script content is empty"
        
        try:
            # Ensure we're in expert mode for filesystem operations
            if not self._ensure_expert_mode():
                return False, "Failed to enter expert mode for script deployment"
            
            # Verify we're still in expert mode before each step
            self.logger.debug("Verifying expert mode before script deployment")
            if not self._verify_expert_mode():
                return False, "Lost expert mode access during script deployment"
            
            # Step 1: Deploy script content to filesystem
            deploy_success, deploy_message = self._deploy_script_content(script_content)
            if not deploy_success:
                return False, f"Script deployment failed: {deploy_message}"
            
            # Verify expert mode again
            if not self._verify_expert_mode():
                return False, "Lost expert mode access after script deployment"
            
            # Step 2: Make script executable
            chmod_success, chmod_message = self._make_script_executable()
            if not chmod_success:
                return False, f"Failed to make script executable: {chmod_message}"
            
            # Verify expert mode before execution
            if not self._verify_expert_mode():
                return False, "Lost expert mode access before script execution"
            
            # Step 3: Execute script and capture output
            exec_success, exec_output = self._execute_script()
            if not exec_success:
                return False, f"Script execution failed: {exec_output}"
            
            self.logger.info("Script deployment and execution completed successfully")
            return True, exec_output
            
        except Exception as e:
            error_message = f"Script deployment and execution failed: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _ensure_expert_mode(self) -> bool:
        """Ensure we're in expert mode for filesystem operations.
        
        Script deployment MUST be done in expert mode as it's the only mode
        with access to the bash shell and filesystem operations.
        
        Returns:
            True if in expert mode, False otherwise
        """
        self.logger.info("Ensuring we're in expert mode for script operations")
        
        current_mode = self.ssh_manager.get_current_mode()
        
        if current_mode == FirewallMode.EXPERT:
            self.logger.debug("Already in expert mode")
            return True
        
        # Try to detect mode if unknown
        if current_mode == FirewallMode.UNKNOWN:
            current_mode = self.ssh_manager.detect_mode()
            if current_mode == FirewallMode.EXPERT:
                self.logger.debug("Already in expert mode (detected)")
                return True
        
        # Need to enter expert mode
        if not hasattr(self.ssh_manager.config, 'expert_password') or not self.ssh_manager.config.expert_password:
            self.logger.error("Expert password not configured, cannot enter expert mode")
            self.logger.error("Script deployment requires expert mode access to bash shell")
            return False
        
        self.logger.info("Entering expert mode for script deployment (required for bash access)")
        success = self.ssh_manager.enter_expert_mode(self.ssh_manager.config.expert_password)
        
        if success:
            self.logger.info("Successfully entered expert mode")
        else:
            self.logger.error("Failed to enter expert mode - script deployment cannot proceed")
        
        return success
    
    def _verify_expert_mode(self) -> bool:
        """Verify we're currently in expert mode.
        
        Returns:
            True if in expert mode, False otherwise
        """
        current_mode = self.ssh_manager.get_current_mode()
        
        if current_mode == FirewallMode.EXPERT:
            return True
        
        # Try to detect mode if unknown
        if current_mode == FirewallMode.UNKNOWN:
            detected_mode = self.ssh_manager.detect_mode()
            if detected_mode == FirewallMode.EXPERT:
                return True
        
        self.logger.error(f"Not in expert mode (current mode: {current_mode.value})")
        return False
    
    def _deploy_script_content(self, script_content: str) -> Tuple[bool, str]:
        """Deploy bash script content to firewall filesystem using cat with EOF.
        
        This implements requirement 2.2: Copy the entire content of the provided bash script.
        Uses cat with EOF to write script content to /home/admin/initial_config.sh.
        
        IMPORTANT: This operation requires expert mode for filesystem access.
        
        Args:
            script_content: Content of the bash script
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info(f"Deploying script content to {self.script_path} (expert mode required)")
        
        try:
            # Prepare the cat command with EOF delimiter
            # Using a unique EOF delimiter to avoid conflicts with script content
            eof_delimiter = "SCRIPT_CONTENT_EOF_DELIMITER"
            
            # Ensure the delimiter doesn't exist in the script content
            if eof_delimiter in script_content:
                eof_delimiter = "UNIQUE_EOF_DELIMITER_12345"
                if eof_delimiter in script_content:
                    return False, "Script content contains reserved EOF delimiter"
            
            # Build the complete cat command
            cat_command = f"cat > {self.script_path} << '{eof_delimiter}'"
            
            self.logger.debug(f"Sending cat command: {cat_command}")
            
            # Send the cat command
            self.ssh_manager.shell.send(cat_command + '\n')
            time.sleep(0.5)
            
            # Send the script content line by line to avoid buffer issues
            lines = script_content.split('\n')
            for line in lines:
                self.ssh_manager.shell.send(line + '\n')
                time.sleep(0.1)  # Small delay to prevent buffer overflow
            
            # Send the EOF delimiter to close the cat command
            self.ssh_manager.shell.send(eof_delimiter + '\n')
            
            # Wait for command completion and read response
            time.sleep(1)
            output = ""
            read_attempts = 0
            max_attempts = 10
            
            while read_attempts < max_attempts:
                if self.ssh_manager.shell.recv_ready():
                    chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    self.logger.debug(f"Cat command output: '{chunk}'")
                    
                    # Check if we're back to a prompt
                    if "]#" in chunk or "Expert@" in chunk:
                        break
                else:
                    time.sleep(0.2)
                    read_attempts += 1
            
            # Verify the file was created by checking if it exists
            verify_success, verify_message = self._verify_file_exists()
            if not verify_success:
                return False, f"File creation verification failed: {verify_message}"
            
            self.logger.info("Script content deployed successfully")
            return True, "Script content deployed successfully"
            
        except Exception as e:
            error_message = f"Error deploying script content: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _verify_file_exists(self) -> Tuple[bool, str]:
        """Verify that the script file was created successfully.
        
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.debug(f"Verifying file exists: {self.script_path}")
        
        try:
            # Use ls command to check if file exists
            response = self.ssh_manager.execute_command(f"ls -la {self.script_path}", timeout=5)
            
            if response.success and self.script_path in response.output:
                self.logger.debug("File exists verification passed")
                return True, "File exists"
            else:
                self.logger.error(f"File does not exist. ls output: {response.output}")
                return False, f"File does not exist: {response.output}"
                
        except Exception as e:
            error_message = f"Error verifying file existence: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _make_script_executable(self) -> Tuple[bool, str]:
        """Make the deployed script executable using chmod +x.
        
        This implements requirement 2.3: Make the file executable using chmod +x.
        
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info(f"Making script executable: {self.script_path}")
        
        try:
            # Execute chmod +x command
            response = self.ssh_manager.execute_command(f"chmod +x {self.script_path}", timeout=5)
            
            if response.success:
                # Verify the file is now executable by checking permissions
                verify_response = self.ssh_manager.execute_command(f"ls -la {self.script_path}", timeout=5)
                
                if verify_response.success and "x" in verify_response.output:
                    self.logger.info("Script made executable successfully")
                    return True, "Script made executable successfully"
                else:
                    return False, f"Failed to verify executable permissions: {verify_response.output}"
            else:
                return False, f"chmod command failed: {response.error_message}"
                
        except Exception as e:
            error_message = f"Error making script executable: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _execute_script(self) -> Tuple[bool, str]:
        """Execute the deployed script and capture output.
        
        This implements requirement 2.4: Execute the bash script.
        Also handles potential reboot scenarios as mentioned in requirements 2.5-2.6.
        
        IMPORTANT: Script execution requires expert mode for bash shell access.
        
        Returns:
            Tuple of (success, script_output)
        """
        self.logger.info(f"Executing script: {self.script_path} (in expert mode)")
        
        try:
            # Execute the script with extended timeout for long-running operations
            # Use bash explicitly to ensure proper execution
            script_command = f"bash {self.script_path}"
            
            self.logger.debug(f"Executing command: {script_command}")
            
            # Send the command
            self.ssh_manager.shell.send(script_command + '\n')
            
            # Read output with extended timeout for script execution and detect disconnection
            output, connection_lost = self._read_script_output_with_disconnect_detection(timeout=300)
            
            # Check for reboot indicators in the output or connection loss
            reboot_detected = self._check_for_reboot_indicators(output) or connection_lost
            
            if reboot_detected:
                if connection_lost:
                    self.logger.info("Connection lost during script execution - firewall likely rebooted")
                    return True, f"Script executed successfully. Connection lost (firewall rebooted).\n\nScript output:\n{output}"
                else:
                    self.logger.info("Reboot detected in script output")
                    return True, f"Script executed successfully. Reboot detected.\n\nScript output:\n{output}"
            else:
                self.logger.info("Script execution completed")
                return True, f"Script executed successfully.\n\nScript output:\n{output}"
                
        except Exception as e:
            error_message = f"Error executing script: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
            return False, error_message
    
    def _read_script_output_with_disconnect_detection(self, timeout: int = 300) -> Tuple[str, bool]:
        """Read script output with extended timeout and detect connection loss.
        
        This method specifically handles cases where the script causes a reboot
        (like config_system -f first_wizard.conf) which terminates the SSH connection.
        
        Args:
            timeout: Maximum time to wait for script completion
            
        Returns:
            Tuple of (complete_script_output, connection_lost_flag)
        """
        output = ""
        start_time = time.time()
        last_activity = start_time
        inactivity_timeout = 30  # 30 seconds of no output indicates completion
        connection_lost = False
        
        self.logger.debug(f"Reading script output with {timeout}s timeout and disconnect detection")
        
        while time.time() - start_time < timeout:
            try:
                if self.ssh_manager.shell.recv_ready():
                    try:
                        chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                        if chunk:
                            output += chunk
                            last_activity = time.time()
                            
                            # Log chunk for debugging (truncate if too long)
                            log_chunk = chunk[:200] + "..." if len(chunk) > 200 else chunk
                            self.logger.debug(f"Script output chunk: '{log_chunk}'")
                            
                            # Check for prompt indicating script completion
                            if self._is_script_complete(chunk):
                                self.logger.debug("Script completion detected from prompt")
                                break
                                
                    except Exception as e:
                        self.logger.debug(f"Error reading script output (possible connection loss): {e}")
                        # Check if this is a connection loss
                        if "Socket is closed" in str(e) or "Connection reset" in str(e) or not self.ssh_manager.is_connected():
                            self.logger.info("Connection lost during script execution - likely due to reboot")
                            connection_lost = True
                            break
                        else:
                            break
                else:
                    # Check for connection loss when no data is ready
                    if not self.ssh_manager.is_connected():
                        self.logger.info("SSH connection lost during script execution")
                        connection_lost = True
                        break
                    
                    # Check for inactivity timeout
                    if time.time() - last_activity > inactivity_timeout:
                        self.logger.debug("Script execution completed (inactivity timeout)")
                        break
                        
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.debug(f"Exception during script output reading: {e}")
                # Check if this indicates connection loss
                if "Socket is closed" in str(e) or "Connection reset" in str(e):
                    self.logger.info("Connection lost during script execution (exception caught)")
                    connection_lost = True
                    break
                else:
                    break
        
        # Try to get any remaining output if connection is still active
        if not connection_lost:
            final_attempts = 0
            while final_attempts < 5:
                try:
                    if self.ssh_manager.shell.recv_ready():
                        chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                        if chunk:
                            output += chunk
                    else:
                        break
                    final_attempts += 1
                except:
                    break
        
        return output.strip(), connection_lost
    
    def _is_script_complete(self, chunk: str) -> bool:
        """Check if the script execution is complete based on output chunk.
        
        Args:
            chunk: Output chunk to analyze
            
        Returns:
            True if script appears to be complete
        """
        # Look for expert mode prompt indicating return to shell
        if "[Expert@" in chunk and "]#" in chunk:
            return True
        
        # Look for common script completion indicators
        completion_indicators = [
            "script completed",
            "execution finished",
            "done",
        ]
        
        chunk_lower = chunk.lower()
        for indicator in completion_indicators:
            if indicator in chunk_lower:
                return True
        
        return False
    
    def _check_for_reboot_indicators(self, output: str) -> bool:
        """Check script output for reboot indicators.
        
        This supports requirements 2.5-2.6 for reboot handling.
        Includes Check Point specific reboot indicators.
        
        Args:
            output: Script output to analyze
            
        Returns:
            True if reboot indicators are found
        """
        reboot_indicators = [
            "reboot",
            "restart",
            "rebooting",
            "system will restart",
            "shutdown -r",
            "init 6",
            "systemctl reboot",
            "config_system",  # Check Point specific - config_system often causes reboot
            "configuring products",  # Check Point first time wizard
            "connection.*closed",  # SSH connection closed unexpectedly
            "connection.*reset",
            "connection.*lost",
        ]
        
        output_lower = output.lower()
        for indicator in reboot_indicators:
            if indicator in output_lower:
                self.logger.info(f"Reboot indicator detected: '{indicator}'")
                return True
        
        return False
    
    def handle_reboot_scenario(self, max_wait_time: int = 600) -> Tuple[bool, str]:
        """Handle firewall reboot scenario by waiting for reconnection.
        
        This implements requirements 2.5-2.6:
        - 2.5: Handle firewall reboot scenarios
        - 2.6: Wait for SSH to become available again
        
        Args:
            max_wait_time: Maximum time to wait for reboot completion in seconds
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info("Handling reboot scenario - waiting for firewall to come back online")
        
        try:
            # Disconnect current connection
            self.ssh_manager.disconnect()
            
            # Wait for the firewall to reboot and become available
            success = self.ssh_manager.wait_for_reconnect(
                max_attempts=max_wait_time // 10,  # Attempt every 10 seconds
                delay=10
            )
            
            if success:
                self.logger.info("Successfully reconnected after reboot")
                return True, "Reconnected successfully after reboot"
            else:
                return False, f"Failed to reconnect within {max_wait_time} seconds"
                
        except Exception as e:
            error_message = f"Error handling reboot scenario: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def deploy_binary_file(self, local_file_path: str, remote_file_path: Optional[str] = None) -> Tuple[bool, str]:
        """Deploy a binary file to the firewall filesystem using base64 encoding.
        
        This method transfers binary files (like Check Point configuration backups)
        to the firewall without requiring SCP or additional user accounts.
        
        Args:
            local_file_path: Path to the local binary file to transfer
            remote_file_path: Remote path where file should be saved (defaults to /home/admin/filename)
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info(f"Starting binary file deployment: {local_file_path}")
        
        # Validate local file exists
        if not os.path.exists(local_file_path):
            return False, f"Local file does not exist: {local_file_path}"
        
        if not os.path.isfile(local_file_path):
            return False, f"Path is not a file: {local_file_path}"
        
        # Determine remote file path
        if remote_file_path is None:
            filename = os.path.basename(local_file_path)
            remote_file_path = f"/home/admin/{filename}"
        
        try:
            # Ensure we're in expert mode for filesystem operations
            if not self._ensure_expert_mode():
                return False, "Failed to enter expert mode for binary file deployment"
            
            # Read and encode the binary file
            encode_success, encoded_data = self._encode_binary_file(local_file_path)
            if not encode_success:
                return False, f"Failed to encode binary file: {encoded_data}"
            
            # Transfer the encoded data
            transfer_success, transfer_message = self._transfer_encoded_file(encoded_data, remote_file_path)
            if not transfer_success:
                return False, f"Failed to transfer file: {transfer_message}"
            
            # Verify the file was transferred correctly
            verify_success, verify_message = self._verify_binary_file_transfer(local_file_path, remote_file_path)
            if not verify_success:
                return False, f"File transfer verification failed: {verify_message}"
            
            self.logger.info(f"Binary file deployed successfully to {remote_file_path}")
            return True, f"Binary file deployed successfully to {remote_file_path}"
            
        except Exception as e:
            error_message = f"Error deploying binary file: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _encode_binary_file(self, file_path: str) -> Tuple[bool, str]:
        """Encode a binary file to base64 for transfer.
        
        Args:
            file_path: Path to the binary file to encode
            
        Returns:
            Tuple of (success, encoded_data_or_error_message)
        """
        try:
            self.logger.debug(f"Encoding binary file: {file_path}")
            
            with open(file_path, 'rb') as f:
                binary_data = f.read()
            
            # Get file size for logging
            file_size = len(binary_data)
            self.logger.debug(f"File size: {file_size} bytes")
            
            # Check for reasonable file size (limit to 100MB for safety)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                return False, f"File too large ({file_size} bytes). Maximum size is {max_size} bytes."
            
            # Encode to base64
            encoded_data = base64.b64encode(binary_data).decode('ascii')
            
            self.logger.debug(f"File encoded successfully. Encoded size: {len(encoded_data)} characters")
            return True, encoded_data
            
        except Exception as e:
            error_message = f"Error encoding binary file: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _transfer_encoded_file(self, encoded_data: str, remote_file_path: str) -> Tuple[bool, str]:
        """Transfer base64 encoded data to the firewall and decode it.
        
        Args:
            encoded_data: Base64 encoded file data
            remote_file_path: Remote path where file should be saved
            
        Returns:
            Tuple of (success, status_message)
        """
        try:
            self.logger.info(f"Transferring encoded file to {remote_file_path}")
            
            # Create a temporary base64 file on the firewall
            temp_b64_file = f"{remote_file_path}.b64"
            
            # Use the same method as script deployment but for base64 data
            deploy_success, deploy_message = self._deploy_text_content(encoded_data, temp_b64_file)
            if not deploy_success:
                return False, f"Failed to deploy base64 data: {deploy_message}"
            
            # Decode the base64 file to create the binary file
            decode_command = f"base64 -d {temp_b64_file} > {remote_file_path}"
            self.logger.debug(f"Decoding with command: {decode_command}")
            
            response = self.ssh_manager.execute_command(decode_command, timeout=30)
            if not response.success:
                return False, f"Failed to decode base64 file: {response.error_message}"
            
            # Remove the temporary base64 file
            cleanup_response = self.ssh_manager.execute_command(f"rm -f {temp_b64_file}", timeout=5)
            if not cleanup_response.success:
                self.logger.warning(f"Failed to cleanup temporary file {temp_b64_file}: {cleanup_response.error_message}")
            
            self.logger.info("File transfer and decoding completed successfully")
            return True, "File transferred and decoded successfully"
            
        except Exception as e:
            error_message = f"Error transferring encoded file: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _deploy_text_content(self, content: str, remote_file_path: str) -> Tuple[bool, str]:
        """Deploy text content to firewall filesystem using cat with EOF.
        
        This is a generalized version of _deploy_script_content for any text content.
        
        Args:
            content: Text content to deploy
            remote_file_path: Remote path where content should be saved
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.debug(f"Deploying text content to {remote_file_path}")
        
        try:
            # Prepare the cat command with EOF delimiter
            eof_delimiter = "TEXT_CONTENT_EOF_DELIMITER"
            
            # Ensure the delimiter doesn't exist in the content
            if eof_delimiter in content:
                eof_delimiter = "UNIQUE_TEXT_EOF_DELIMITER_54321"
                if eof_delimiter in content:
                    return False, "Content contains reserved EOF delimiter"
            
            # Build the complete cat command
            cat_command = f"cat > {remote_file_path} << '{eof_delimiter}'"
            
            self.logger.debug(f"Sending cat command: {cat_command}")
            
            # Send the cat command
            self.ssh_manager.shell.send(cat_command + '\n')
            time.sleep(0.5)
            
            # Send the content in chunks to avoid buffer issues
            chunk_size = 1024
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                self.ssh_manager.shell.send(chunk)
                time.sleep(0.1)  # Small delay to prevent buffer overflow
            
            # Ensure we end with a newline and send the EOF delimiter
            self.ssh_manager.shell.send('\n' + eof_delimiter + '\n')
            
            # Wait for command completion
            time.sleep(1)
            output = ""
            read_attempts = 0
            max_attempts = 10
            
            while read_attempts < max_attempts:
                if self.ssh_manager.shell.recv_ready():
                    chunk = self.ssh_manager.shell.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    self.logger.debug(f"Cat command output: '{chunk}'")
                    
                    # Check if we're back to a prompt
                    if "]#" in chunk or "Expert@" in chunk:
                        break
                else:
                    time.sleep(0.2)
                    read_attempts += 1
            
            self.logger.debug("Text content deployed successfully")
            return True, "Text content deployed successfully"
            
        except Exception as e:
            error_message = f"Error deploying text content: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def _verify_binary_file_transfer(self, local_file_path: str, remote_file_path: str) -> Tuple[bool, str]:
        """Verify that the binary file was transferred correctly by comparing checksums.
        
        Args:
            local_file_path: Path to the original local file
            remote_file_path: Path to the transferred remote file
            
        Returns:
            Tuple of (success, status_message)
        """
        try:
            self.logger.debug("Verifying binary file transfer with checksum comparison")
            
            # Calculate local file checksum
            import hashlib
            with open(local_file_path, 'rb') as f:
                local_checksum = hashlib.md5(f.read()).hexdigest()
            
            self.logger.debug(f"Local file MD5: {local_checksum}")
            
            # Calculate remote file checksum
            checksum_command = f"md5sum {remote_file_path}"
            response = self.ssh_manager.execute_command(checksum_command, timeout=10)
            
            if not response.success:
                return False, f"Failed to calculate remote checksum: {response.error_message}"
            
            # Extract checksum from md5sum output (format: "checksum filename")
            remote_output = response.output.strip()
            if not remote_output:
                return False, "Empty checksum response from remote system"
            
            remote_checksum = remote_output.split()[0]
            self.logger.debug(f"Remote file MD5: {remote_checksum}")
            
            # Compare checksums
            if local_checksum.lower() == remote_checksum.lower():
                self.logger.info("File transfer verification successful - checksums match")
                return True, "File transfer verified successfully"
            else:
                return False, f"Checksum mismatch - Local: {local_checksum}, Remote: {remote_checksum}"
                
        except Exception as e:
            error_message = f"Error verifying file transfer: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def deploy_checkpoint_backup(self, backup_file_path: str, restore_script_content: Optional[str] = None) -> Tuple[bool, str]:
        """Deploy a Check Point configuration backup and optionally create a restore script.
        
        This is a convenience method specifically for Check Point backup files.
        
        Args:
            backup_file_path: Path to the Check Point backup file (.tgz typically)
            restore_script_content: Optional script content for restoring the backup
            
        Returns:
            Tuple of (success, status_message)
        """
        self.logger.info(f"Deploying Check Point backup: {backup_file_path}")
        
        try:
            # Deploy the backup file
            backup_success, backup_message = self.deploy_binary_file(backup_file_path)
            if not backup_success:
                return False, f"Failed to deploy backup file: {backup_message}"
            
            # If restore script is provided, deploy it as well
            if restore_script_content:
                script_success, script_message = self.deploy_and_execute_script(restore_script_content)
                if not script_success:
                    return False, f"Backup deployed but restore script failed: {script_message}"
                
                return True, f"Check Point backup and restore script deployed successfully. {script_message}"
            else:
                backup_filename = os.path.basename(backup_file_path)
                return True, f"Check Point backup deployed successfully to /home/admin/{backup_filename}"
                
        except Exception as e:
            error_message = f"Error deploying Check Point backup: {str(e)}"
            self.logger.error(error_message)
            return False, error_message