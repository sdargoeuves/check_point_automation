"""
Simple script deployment for Check Point firewalls using netmiko.
Clean implementation focused on the essential functionality.
"""

import logging
import os
import time
from typing import Tuple, Optional

from .ssh_connection import SSHConnectionManager
from .command_executor import CommandResponse, FirewallMode


class ScriptDeployment:
    """Simple script deployment using netmiko methods."""
    
    def __init__(self, ssh_manager: SSHConnectionManager):
        """Initialize with SSH connection manager."""
        self.ssh = ssh_manager
        self.logger = ssh_manager.logger
    
    def deploy_text_file(self, local_file_path: str, remote_file_path: str) -> Tuple[bool, str]:
        """Deploy a text file using cat with EOF delimiter.
        
        Args:
            local_file_path: Path to local file
            remote_file_path: Path where file should be created on firewall
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Deploying text file {local_file_path} to {remote_file_path}")
        
        # Check if local file exists
        if not os.path.isfile(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        # Make sure we're in expert mode for file operations
        if self.ssh.get_current_mode() != FirewallMode.EXPERT:
            self.logger.error("Must be in expert mode for file deployment")
            return False, "Must be in expert mode for file operations"
        
        try:
            # Read the local file
            with open(local_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Use unique EOF delimiter
            eof_delimiter = f"EOF_{int(time.time())}"
            
            # Create the cat command
            cat_command = f"cat > {remote_file_path} << '{eof_delimiter}'"
            
            # Start the heredoc
            self.logger.debug(f"Starting cat command: {cat_command}")
            self.ssh.connection.write_channel(cat_command + '\n')
            
            # Send the file content
            self.logger.debug("Sending file content")
            self.ssh.connection.write_channel(file_content)
            
            # Close the heredoc
            self.logger.debug("Closing heredoc")
            self.ssh.connection.write_channel(f'\n{eof_delimiter}\n')
            
            # Wait a moment for command to complete
            time.sleep(1)
            
            # Verify file was created
            verify_response = self.ssh.execute_command(f"ls -la {remote_file_path}")
            if verify_response.success and remote_file_path in verify_response.output:
                self.logger.info(f"File deployed successfully to {remote_file_path}")
                return True, "File deployed successfully"
            else:
                return False, "File deployment verification failed"
                
        except Exception as e:
            error_msg = f"Error deploying file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def deploy_binary_file(self, local_file_path: str, remote_file_path: str) -> Tuple[bool, str]:
        """Deploy a binary file using base64 encoding.
        
        Args:
            local_file_path: Path to local binary file
            remote_file_path: Path where file should be created on firewall
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Deploying binary file {local_file_path} to {remote_file_path}")
        
        # Check if local file exists
        if not os.path.isfile(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        # Make sure we're in expert mode
        if self.ssh.get_current_mode() != FirewallMode.EXPERT:
            self.logger.error("Must be in expert mode for file deployment")
            return False, "Must be in expert mode for file operations"
        
        try:
            import base64
            
            # Read and encode the binary file
            with open(local_file_path, 'rb') as f:
                binary_data = f.read()
            
            encoded_data = base64.b64encode(binary_data).decode('ascii')
            
            # Create temporary base64 file
            temp_b64_file = f"{remote_file_path}.b64"
            
            # Deploy the base64 data as text
            success, message = self._deploy_text_content(encoded_data, temp_b64_file)
            if not success:
                return False, f"Failed to deploy base64 data: {message}"
            
            # Decode the base64 file to binary
            decode_cmd = f"base64 -d {temp_b64_file} > {remote_file_path}"
            decode_response = self.ssh.execute_command(decode_cmd)
            
            if not decode_response.success:
                return False, f"Failed to decode base64 file: {decode_response.error_message}"
            
            # Clean up temporary file
            cleanup_response = self.ssh.execute_command(f"rm -f {temp_b64_file}")
            if not cleanup_response.success:
                self.logger.warning(f"Failed to clean up temporary file: {temp_b64_file}")
            
            # Verify binary file
            verify_response = self.ssh.execute_command(f"ls -la {remote_file_path}")
            if verify_response.success and remote_file_path in verify_response.output:
                self.logger.info(f"Binary file deployed successfully to {remote_file_path}")
                return True, "Binary file deployed successfully"
            else:
                return False, "Binary file deployment verification failed"
                
        except Exception as e:
            error_msg = f"Error deploying binary file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _deploy_text_content(self, content: str, remote_file_path: str) -> Tuple[bool, str]:
        """Deploy text content using cat heredoc.
        
        Args:
            content: Text content to deploy
            remote_file_path: Remote file path
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use unique EOF delimiter
            eof_delimiter = f"EOF_{int(time.time())}"
            
            # Create the cat command
            cat_command = f"cat > {remote_file_path} << '{eof_delimiter}'"
            
            # Start the heredoc
            self.ssh.connection.write_channel(cat_command + '\n')
            
            # Send the content
            self.ssh.connection.write_channel(content)
            
            # Close the heredoc
            self.ssh.connection.write_channel(f'\n{eof_delimiter}\n')
            
            # Wait for command to complete
            time.sleep(1)
            
            return True, "Content deployed successfully"
            
        except Exception as e:
            return False, f"Error deploying content: {str(e)}"
    
    def execute_script(self, script_path: str, args: Optional[str] = None) -> Tuple[bool, str]:
        """Execute a script on the firewall.
        
        Args:
            script_path: Path to script on firewall
            args: Optional arguments for the script
            
        Returns:
            Tuple of (success, output)
        """
        self.logger.info(f"Executing script: {script_path}")
        
        # Make sure we're in expert mode
        if self.ssh.get_current_mode() != FirewallMode.EXPERT:
            self.logger.error("Must be in expert mode to execute scripts")
            return False, "Must be in expert mode to execute scripts"
        
        try:
            # Make script executable
            chmod_response = self.ssh.execute_command(f"chmod +x {script_path}")
            if not chmod_response.success:
                self.logger.warning(f"Failed to make script executable: {chmod_response.error_message}")
            
            # Execute the script
            script_command = script_path
            if args:
                script_command += f" {args}"
            
            self.logger.debug(f"Executing: {script_command}")
            response = self.ssh.execute_command(script_command, timeout=60)
            
            if response.success:
                self.logger.info("Script executed successfully")
                return True, response.output
            else:
                return False, response.error_message or "Script execution failed"
                
        except Exception as e:
            error_msg = f"Error executing script: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg