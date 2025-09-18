"""
SSH Connection Manager for Check Point firewalls.
"""

import logging
import logging.handlers
import os
import socket
import time
from typing import Optional

import paramiko

from .config import FirewallConfig

# Define a custom handler that compresses rotated files
class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    A rotating file handler that compresses the rotated log files using gzip.
    """
    def doRollover(self):
        """
        Do a rollover, as described in RotatingFileHandler.
        After the rollover, the newly rotated log file is compressed.
        """
        # Ensure the current stream is closed before rollover
        if self.stream:
            self.stream.close()
            self.stream = None

        # Get the name of the file that is about to be rotated to '.1'
        # This is the 'baseFilename' of the current log file.
        # super().doRollover() will rename this to self.baseFilename + '.1'
        # before shuffling other backups.
        path_to_compress = self.baseFilename

        # Perform the standard rollover using the parent class's method
        # This will rename 'path_to_compress' to 'path_to_compress.1',
        # 'path_to_compress.1' to 'path_to_compress.2', etc., and
        # open a new empty 'path_to_compress' for current logging.
        super().doRollover()

        # The file that was just rotated to .1 needs to be compressed.
        # This is the file that was previously 'path_to_compress'.
        rotated_file_name = self.rotation_filename(path_to_compress + ".1")

        # Check if the file exists and hasn't been compressed yet
        if os.path.exists(rotated_file_name) and not os.path.exists(rotated_file_name + '.gz'):
            try:
                with open(rotated_file_name, 'rb') as f_in:
                    with gzip.open(rotated_file_name + '.gz', 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(rotated_file_name) # Remove the uncompressed file
            except Exception as e:
                # In a real application, you'd want to log this error
                # using a separate logging mechanism or handle it robustly.
                # For simplicity, we'll just print it or pass.
                print(f"Error compressing log file {rotated_file_name}: {e}")
                pass

        # Ensure a new stream is opened for continued logging
        self.mode = 'a'
        self.stream = self._open()

class SSHConnectionManager:
    """Manages SSH connections to Check Point firewalls."""
    
    def __init__(self, config: FirewallConfig, console_log_level: str = "INFO"):
        """Initialize SSH connection manager.
        
        Args:
            config: Firewall configuration containing connection details
            console_log_level: Log level for console output (DEBUG, INFO, WARNING, ERROR)
        """
        self.config = config
        self.client: Optional[paramiko.SSHClient] = None
        self.shell: Optional[paramiko.Channel] = None
        self.console_log_level = console_log_level
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration for SSH interactions."""
        logger = logging.getLogger(f"checkpoint_automation.ssh.{self.config.ip_address}")
        
        # Prevent propagation to root logger to avoid double logging
        logger.propagate = False
        
        # Only add handlers if logger doesn't already have them
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            logs_dir = "logs"
            os.makedirs(logs_dir, exist_ok=True)
            
            log_file = os.path.join(logs_dir, f"checkpoint_{self.config.ip_address.replace('.', '_')}.log")

            # *** CHANGE HERE: Use our custom CompressedRotatingFileHandler ***
            file_handler = CompressedRotatingFileHandler(
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
    
    def _read_initial_output(self, max_wait: int = 5) -> str:
        """Read initial output from shell to verify connection.
        
        Args:
            max_wait: Maximum time to wait for output in seconds
            
        Returns:
            Initial shell output as string
        """
        if not self.shell:
            return ""
            
        output = ""
        start_time = time.time()
        
        try:
            while time.time() - start_time < max_wait:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(1024).decode('utf-8', errors='ignore')
                    output += chunk
                    
                    # Check if we have a complete prompt (common Check Point prompts)
                    if any(prompt in output for prompt in ['> ', '# ', '$ ', 'login: ', 'Password: ']):
                        break
                        
                time.sleep(0.1)
                
        except socket.timeout:
            self.logger.debug("Timeout while reading initial output")
        except Exception as e:
            self.logger.debug(f"Error reading initial output: {e}")
            
        return output.strip()
    
    def connect(self, timeout: int = 30) -> bool:
        """Establish SSH connection to the firewall.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting to connect to {self.config.ip_address}")
            
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the firewall
            self.client.connect(
                hostname=self.config.ip_address,
                username=self.config.username,
                password=self.config.password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )
            
            # Create interactive shell
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(timeout)
            
            # Wait for and capture initial shell output to verify connection
            initial_output = self._read_initial_output()
            if initial_output:
                self.logger.debug(f"Initial shell output from {self.config.ip_address}:\n{initial_output}")
                self.logger.info(f"Successfully connected to {self.config.ip_address}")
                return True
            else:
                self.logger.warning(f"Connected to {self.config.ip_address} but no initial output received")
                return True  # Still consider it successful as shell was created
            
        except (paramiko.AuthenticationException, paramiko.SSHException, 
                socket.error, socket.timeout) as e:
            self.logger.error(f"Failed to connect to {self.config.ip_address}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Close SSH connection and clean up resources."""
        try:
            if self.shell:
                self.shell.close()
                self.shell = None
                self.logger.debug("Shell channel closed")
                
            if self.client:
                self.client.close()
                self.client = None
                self.logger.info(f"Disconnected from {self.config.ip_address}")
                
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
    
    def is_connected(self) -> bool:
        """Check if SSH connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.client or not self.shell:
            return False
            
        try:
            # Send a simple command to test connection
            transport = self.client.get_transport()
            return transport is not None and transport.is_active()
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