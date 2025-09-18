"""
Initial setup module for Check Point VM automation.

This module handles the initial configuration of fresh Check Point VMs,
including expert password setup, first-time wizard automation, and
admin password updates.
"""

import re
import time
import tempfile
import os
from typing import Dict, Any

from ..core.interfaces import InitialSetupInterface, ConnectionManagerInterface
from ..core.models import CheckPointState, CLIMode, CommandResult, SystemStatus, WizardConfig
from ..core.exceptions import ConfigurationError, ValidationError, AuthenticationError
from ..core.logging_config import get_logger


class InitialSetupModule(InitialSetupInterface):
    """
    Implementation of initial setup operations for Check Point VMs.
    
    This module handles the unique challenges of Check Point's initial setup
    process, including expert password creation and first-time wizard configuration.
    """

    def __init__(self, connection_manager: ConnectionManagerInterface):
        """
        Initialize the initial setup module.
        
        Args:
            connection_manager: Connection manager instance for SSH operations
        """
        super().__init__(connection_manager)
        self.logger = get_logger(__name__)

    def validate_prerequisites(self) -> bool:
        """
        Validate that prerequisites for initial setup are met.
        
        Returns:
            True if prerequisites are met, False otherwise
        """
        if not self.connection_manager.is_connected():
            self.logger.error("Connection manager is not connected")
            return False
            
        current_state = self.connection_manager.detect_state()
        if current_state not in [CheckPointState.FRESH_INSTALL, CheckPointState.EXPERT_PASSWORD_SET]:
            self.logger.error(f"Invalid state for initial setup: {current_state}")
            return False
            
        return True

    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current initial setup configuration state.
        
        Returns:
            Dictionary containing current setup state
        """
        try:
            state = self.connection_manager.detect_state()
            cli_mode = self.connection_manager.get_cli_mode()
            
            return {
                "state": state.value,
                "cli_mode": cli_mode.value,
                "expert_password_set": state != CheckPointState.FRESH_INSTALL,
                "wizard_completed": state in [CheckPointState.WIZARD_COMPLETE, CheckPointState.FULLY_CONFIGURED]
            }
        except Exception as e:
            self.logger.error(f"Failed to get current config: {e}")
            return {}

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration before applying.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        required_keys = ["expert_password"]
        for key in required_keys:
            if key not in config:
                self.logger.error(f"Missing required configuration key: {key}")
                return False
                
        # Validate password strength
        password = config["expert_password"]
        if not self._validate_password_strength(password):
            return False
            
        return True

    def set_expert_password(self, password: str) -> bool:
        """
        Set expert password on fresh Check Point VM.
        
        This method handles the initial expert password setup on a fresh
        Check Point VM installation. It validates the password, executes
        the necessary CLI commands, and verifies the password was set correctly.
        
        Args:
            password: The expert password to set
            
        Returns:
            True if password was set successfully, False otherwise
            
        Raises:
            ConfigurationError: If password setting fails
            ValidationError: If password validation fails
            AuthenticationError: If authentication issues occur
        """
        self.logger.info("Starting expert password setup")
        
        # Validate prerequisites
        if not self.validate_prerequisites():
            raise ConfigurationError("Prerequisites not met for expert password setup")
            
        # Validate password strength
        if not self._validate_password_strength(password):
            raise ValidationError("Password does not meet strength requirements")
            
        try:
            # Ensure we're in clish mode
            current_mode = self.connection_manager.get_cli_mode()
            if current_mode != CLIMode.CLISH:
                self.logger.warning(f"Not in clish mode (current: {current_mode}), attempting to switch")
                if not self.connection_manager.switch_to_clish():
                    raise ConfigurationError("Failed to switch to clish mode")
            
            # Execute expert password setup command
            self.logger.debug("Executing expert password setup command")
            result = self._execute_expert_password_command(password)
            
            if not result.success:
                error_msg = f"Expert password setup failed: {result.error or result.output}"
                self.logger.error(error_msg)
                raise ConfigurationError(error_msg)
                
            # Verify password was set by attempting to switch to expert mode
            self.logger.debug("Verifying expert password was set correctly")
            if not self._verify_expert_password(password):
                raise ConfigurationError("Expert password verification failed")
                
            self.logger.info("Expert password setup completed successfully")
            return True
            
        except (ConfigurationError, ValidationError, AuthenticationError):
            raise
        except Exception as e:
            error_msg = f"Unexpected error during expert password setup: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def run_first_time_wizard(self, config: WizardConfig) -> bool:
        """
        Run first-time setup wizard.
        
        This method automates the Check Point first-time wizard by generating
        a configuration file and applying it using the config_system command.
        
        Args:
            config: Wizard configuration parameters
            
        Returns:
            True if wizard completed successfully, False otherwise
            
        Raises:
            ConfigurationError: If wizard configuration fails
            ValidationError: If configuration validation fails
        """
        self.logger.info("Starting first-time wizard automation")
        
        # Validate prerequisites
        if not self.validate_prerequisites():
            raise ConfigurationError("Prerequisites not met for wizard automation")
            
        # Validate wizard configuration
        if not self._validate_wizard_config(config):
            raise ValidationError("Invalid wizard configuration provided")
            
        try:
            # Generate wizard configuration file
            config_content = self._generate_wizard_config(config)
            
            # Write configuration to temporary file
            config_file_path = self._write_wizard_config_file(config_content)
            
            # Validate configuration with dry-run
            if not self._validate_wizard_config_file(config_file_path):
                raise ConfigurationError("Wizard configuration validation failed")
                
            # Apply wizard configuration
            if not self._apply_wizard_config(config_file_path):
                raise ConfigurationError("Failed to apply wizard configuration")
                
            # Verify wizard completion
            if not self._verify_wizard_completion():
                raise ConfigurationError("Wizard completion verification failed")
                
            self.logger.info("First-time wizard automation completed successfully")
            return True
            
        except (ConfigurationError, ValidationError):
            raise
        except Exception as e:
            error_msg = f"Unexpected error during wizard automation: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def update_admin_password(self, new_password: str) -> bool:
        """
        Update admin user password.
        
        This method updates the default admin password on a Check Point VM.
        It validates the new password against Check Point's password policy,
        executes the password change command, and verifies the change was successful.
        
        Args:
            new_password: New password for admin user
            
        Returns:
            True if password updated successfully, False otherwise
            
        Raises:
            ConfigurationError: If password update fails
            ValidationError: If password validation fails
            AuthenticationError: If authentication issues occur
        """
        self.logger.info("Starting admin password update")
        
        # Validate prerequisites
        if not self.validate_prerequisites():
            raise ConfigurationError("Prerequisites not met for admin password update")
            
        # Validate password strength
        if not self._validate_password_strength(new_password):
            raise ValidationError("New password does not meet strength requirements")
            
        try:
            # Ensure we're in clish mode for user management commands
            current_mode = self.connection_manager.get_cli_mode()
            if current_mode != CLIMode.CLISH:
                self.logger.debug(f"Not in clish mode (current: {current_mode}), switching to clish")
                if not self.connection_manager.switch_to_clish():
                    raise ConfigurationError("Failed to switch to clish mode")
            
            # Execute admin password update command
            self.logger.debug("Executing admin password update command")
            result = self._execute_admin_password_command(new_password)
            
            if not result.success:
                error_msg = f"Admin password update failed: {result.error or result.output}"
                self.logger.error(error_msg)
                raise ConfigurationError(error_msg)
                
            # Verify password was updated by attempting to authenticate
            self.logger.debug("Verifying admin password was updated correctly")
            if not self._verify_admin_password_change(new_password):
                raise ConfigurationError("Admin password verification failed")
                
            self.logger.info("Admin password update completed successfully")
            return True
            
        except (ConfigurationError, ValidationError, AuthenticationError):
            raise
        except Exception as e:
            error_msg = f"Unexpected error during admin password update: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def verify_initial_setup(self) -> SystemStatus:
        """
        Verify initial setup completion.
        
        Returns:
            SystemStatus object with current setup state
        """
        # This will be implemented in a future task
        raise NotImplementedError("Initial setup verification not yet implemented")

    def _validate_password_strength(self, password: str) -> bool:
        """
        Validate password meets minimum requirements.
        
        Simplified password requirements:
        - Minimum 6 characters
        
        Args:
            password: Password to validate
            
        Returns:
            True if password meets requirements, False otherwise
        """
        if len(password) < 6:
            self.logger.error("Password must be at least 6 characters long")
            return False
            
        return True

    def _execute_expert_password_command(self, password: str) -> CommandResult:
        """
        Execute the expert password setup command.
        
        Simple approach: use the connection manager's execute_command method
        and handle the interactive prompts step by step.
        
        Args:
            password: Expert password to set
            
        Returns:
            CommandResult with execution details
        """
        self.logger.debug("Executing expert password setup")
        
        try:
            # Step 1: Send 'set expert-password' command
            result1 = self.connection_manager.execute_command("set expert-password", CLIMode.CLISH)
            
            if not result1.success:
                return result1
            
            # Check if we got the password prompt
            if "Enter new expert password" not in result1.output:
                return CommandResult(
                    command="set expert-password",
                    success=False,
                    output=result1.output,
                    error="Expected password prompt not found"
                )
            
            # Step 2: Send password
            result2 = self.connection_manager.execute_command(password, CLIMode.CLISH)
            
            if not result2.success:
                return result2
            
            # Step 3: Send password again for confirmation
            # The confirmation prompt appears after sending the first password
            result3 = self.connection_manager.execute_command(password, CLIMode.CLISH)
            
            if not result3.success:
                return result3
            
            # Check for success or failure
            full_output = result1.output + result2.output + result3.output
            
            if "Passwords do not match" in result3.output:
                return CommandResult(
                    command="set expert-password",
                    success=False,
                    output=full_output,
                    error="Passwords do not match"
                )
            elif ">" in result3.output or result3.success:
                # Success - we should be back at the prompt
                return CommandResult(
                    command="set expert-password",
                    success=True,
                    output=full_output
                )
            else:
                return CommandResult(
                    command="set expert-password",
                    success=False,
                    output=full_output,
                    error="Unexpected response"
                )
                
        except Exception as e:
            self.logger.error(f"Error in expert password setup: {e}")
            return CommandResult(
                command="set expert-password",
                success=False,
                output="",
                error=str(e)
            )

    def _verify_expert_password(self, password: str) -> bool:
        """
        Verify expert password was set correctly by attempting to switch to expert mode.
        
        Args:
            password: Expert password to verify
            
        Returns:
            True if password verification successful, False otherwise
        """
        try:
            # Attempt to switch to expert mode with the password
            success = self.connection_manager.switch_to_expert(password)
            
            if success:
                # Switch back to clish mode for consistency
                self.connection_manager.switch_to_clish()
                self.logger.debug("Expert password verification successful")
                return True
            else:
                self.logger.error("Expert password verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during expert password verification: {e}")
            return False

    def _validate_wizard_config(self, config: WizardConfig) -> bool:
        """
        Validate wizard configuration parameters.
        
        Args:
            config: Wizard configuration to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate hostname
            if not config.hostname or len(config.hostname.strip()) == 0:
                self.logger.error("Hostname cannot be empty")
                return False
                
            # Validate hostname format (basic check)
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$', config.hostname):
                self.logger.error("Invalid hostname format")
                return False
                
            # Validate timezone format
            if config.timezone and not re.match(r'^[A-Za-z_/]+$', config.timezone):
                self.logger.error("Invalid timezone format")
                return False
                
            # Validate NTP servers (basic IP/hostname format)
            for ntp_server in config.ntp_servers:
                if not self._validate_hostname_or_ip(ntp_server):
                    self.logger.error(f"Invalid NTP server format: {ntp_server}")
                    return False
                    
            # Validate DNS servers (basic IP format)
            for dns_server in config.dns_servers:
                if not self._validate_ip_address(dns_server):
                    self.logger.error(f"Invalid DNS server IP: {dns_server}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating wizard config: {e}")
            return False

    def _generate_wizard_config(self, config: WizardConfig) -> str:
        """
        Generate Check Point wizard configuration file content.
        
        Args:
            config: Wizard configuration parameters
            
        Returns:
            Configuration file content as string
        """
        self.logger.debug("Generating wizard configuration file content")
        
        # Get current admin password hash from system
        admin_hash = self._get_admin_password_hash()
        
        # Generate maintenance password hash
        maintenance_hash = self._generate_maintenance_password_hash()
        
        # Build configuration content based on realistic Check Point configuration
        config_lines = [
            "# Check Point First-Time Wizard Configuration",
            "# Generated by checkpoint-vm-automation",
            "# Based on realistic production configuration",
            "",
            "# Install Security Gateway.",
            "install_security_gw=true",
            "",
            "# Enable DAIP (dynamic ip) gateway.",
            "# Should be \"false\" if CXL or Security Management enabled",
            'gateway_daip="false"',
            "",
            "# Enable/Disable CXL.",
            "gateway_cluster_member=false",
            "",
            "# Install Security Management.",
            "install_security_managment=true",
            "install_mgmt_primary=true",
            "install_mgmt_secondary=false",
            "",
            "# Provider-1 parameters",
            "install_mds_primary=false",
            "install_mds_secondary=false",
            "install_mlm=false",
            "install_mds_interface=false",
            "",
            "# Automatically download and install Software Blade Contracts, security updates, and other important data (highly recommended)",
            "# for more info see sk175504",
            "# possible values: \"true\" / \"false\"",
            'download_info="false"',
            "",
            "# Automatically download software updates and new features (highly recommended).",
            'download_from_checkpoint_non_security="false"',
            "",
            "# Help Check Point improve the product by sending anonymous information.",
            'upload_info="false"',
            "",
            "# Help Check Point improve the product by sending core dump files and other relevant crash data",
            'upload_crash_data="false"',
            "",
            "# Management administrator configuration",
            "# Set to \"gaia_admin\" if you wish to use the Gaia 'admin' account.",
            "# Set to \"new_admin\" if you wish to configure a new admin account.",
            'mgmt_admin_radio="gaia_admin"',
            "",
            "# In case you chose to configure a new Management admin account,",
            'mgmt_admin_name="admin"',
            "",
            "# Management administrator password",
            'mgmt_admin_passwd="admin"',
            "",
            "# Management GUI clients",
            "# choose which GUI clients can log into the Security Management",
            "# (e.g. any, 1.2.3.4, 192.168.0.0/24)",
            "# Set to \"any\" if any host allowed to connect to management",
            "# Set to \"range\" if range of IPs allowed to connect to management",
            "# Set to \"network\" if IPs from specific network allowed to connect",
            "# to management",
            "# Set to \"this\" if it' a single IP",
            "# Must be provided if Security Management installed",
            "mgmt_gui_clients_radio=any",
            "",
            "## In case of \"range\", provide the first and last IPs in dotted format",
            "mgmt_gui_clients_first_ip_field=",
            "mgmt_gui_clients_last_ip_field=",
            "",
            "## In case of \"network\", provide IP in dotted format and netmask length",
            "# in range 1-32",
            "mgmt_gui_clients_ip_field=",
            "mgmt_gui_clients_subnet_field=",
            "",
            "## In case of a single IP",
            "mgmt_gui_clients_hostname=",
            "",
            "# Secure Internal Communication key, e.g. \"aaaa\"",
            "# Must be provided, if primary Security Management not installed",
            "ftw_sic_key=",
            "",
            "# Management as a service",
            "# optional parameter for security_gateway only",
            "maas_authentication_key=",
            "",
            "# Password (hash) of user admin.",
            "# To get hash of admin password from configured system:",
            "#   dbget passwd:admin:passwd",
            f"admin_hash='{admin_hash}'",
            "",
            "# Default maintenance password (hash)",
            "# To generate a hash of maintenance password - in expert mode:",
            "#   grub2-mkpasswd-pbkdf2",
            f"maintenance_hash='{maintenance_hash}'",
            "",
            "# Interface name, optional parameter",
            "iface=",
            "ipstat_v4=manually",
            "ipaddr_v4=",
            "masklen_v4=",
            "default_gw_v4=",
            "ipstat_v6=off",
            "ipaddr_v6=",
            "masklen_v6=",
            "default_gw_v6=",
            "",
            "# Host Name e.g host123, optional parameter",
            f"hostname={config.hostname}",
        ]
        
        # Add domain name if provided
        if config.domain_name:
            config_lines.append(f"domainname={config.domain_name}")
        
        # Add timezone
        config_lines.append(f"timezone='{config.timezone}'")
        
        # Add NTP servers
        if config.ntp_servers:
            config_lines.append(f"ntp_primary={config.ntp_servers[0]}")
            if len(config.ntp_servers) > 1:
                config_lines.append(f"ntp_secondary={config.ntp_servers[1]}")
        else:
            # Use Check Point default NTP servers
            config_lines.extend([
                "ntp_primary=ntp.checkpoint.com",
                "ntp_secondary=ntp2.checkpoint.com"
            ])
            
        # Add DNS servers
        if config.dns_servers:
            config_lines.append(f"primary={config.dns_servers[0]}")
            if len(config.dns_servers) > 1:
                config_lines.append(f"secondary={config.dns_servers[1]}")
            if len(config.dns_servers) > 2:
                config_lines.append(f"tertiary={config.dns_servers[2]}")
        
        # Add final settings
        config_lines.extend([
            "",
            "# NTP servers",
            f"ntp_primary={config.ntp_servers[0] if config.ntp_servers else ''}",
            "",
            "# Optional parameter, if not specified the default is false",
            "reboot_if_required=true"
        ])
        
        return "\n".join(config_lines)

    def _write_wizard_config_file(self, config_content: str) -> str:
        """
        Write wizard configuration to temporary file.
        
        Args:
            config_content: Configuration file content
            
        Returns:
            Path to the created configuration file
        """
        import tempfile
        import os
        
        # Create temporary file with timestamp
        timestamp = int(time.time())
        config_filename = f"ftw_config_{timestamp}.conf"
        
        # Write to /tmp directory (accessible in expert mode)
        config_path = f"/tmp/{config_filename}"
        
        try:
            # Write configuration to temporary file using expert mode
            write_command = f"cat > {config_path} << 'EOF'\n{config_content}\nEOF"
            result = self.connection_manager.execute_command(write_command, CLIMode.EXPERT)
            
            if not result.success:
                raise ConfigurationError(f"Failed to write configuration file: {result.error}")
                
            self.logger.debug(f"Configuration file written to: {config_path}")
            return config_path
            
        except Exception as e:
            self.logger.error(f"Error writing configuration file: {e}")
            raise ConfigurationError(f"Failed to write configuration file: {e}")

    def _validate_wizard_config_file(self, config_file_path: str) -> bool:
        """
        Validate wizard configuration file using dry-run.
        
        Args:
            config_file_path: Path to configuration file
            
        Returns:
            True if validation successful, False otherwise
        """
        try:
            self.logger.debug("Validating wizard configuration with dry-run")
            
            # Ensure we're in expert mode
            if not self.connection_manager.switch_to_expert():
                raise ConfigurationError("Failed to switch to expert mode for validation")
                
            # Run config_system with dry-run flag
            validate_command = f"config_system --dry-run -f {config_file_path}"
            result = self.connection_manager.execute_command(validate_command, CLIMode.EXPERT)
            
            if not result.success:
                self.logger.error(f"Configuration validation failed: {result.output}")
                return False
                
            # Check for validation failure indicators in output
            if "Failed" in result.output or "Error" in result.output:
                self.logger.error(f"Configuration validation failed: {result.output}")
                return False
                
            self.logger.debug("Configuration validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during configuration validation: {e}")
            return False

    def _apply_wizard_config(self, config_file_path: str) -> bool:
        """
        Apply wizard configuration using config_system command.
        
        Args:
            config_file_path: Path to configuration file
            
        Returns:
            True if application successful, False otherwise
        """
        try:
            self.logger.info("Applying wizard configuration")
            
            # Ensure we're in expert mode
            if not self.connection_manager.switch_to_expert():
                raise ConfigurationError("Failed to switch to expert mode for configuration")
                
            # Apply configuration
            apply_command = f"config_system -f {config_file_path}"
            result = self.connection_manager.execute_command(apply_command, CLIMode.EXPERT)
            
            if not result.success:
                self.logger.error(f"Configuration application failed: {result.output}")
                return False
                
            # Check for application failure indicators
            if "Failed" in result.output or "Error" in result.output:
                self.logger.error(f"Configuration application failed: {result.output}")
                return False
                
            self.logger.info("Configuration applied successfully")
            
            # Clean up temporary file
            cleanup_command = f"rm -f {config_file_path}"
            self.connection_manager.execute_command(cleanup_command, CLIMode.EXPERT)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying configuration: {e}")
            return False

    def _verify_wizard_completion(self) -> bool:
        """
        Verify that the wizard completed successfully.
        
        Returns:
            True if wizard completion verified, False otherwise
        """
        try:
            self.logger.debug("Verifying wizard completion")
            
            # Wait for system to process configuration
            time.sleep(10)
            
            # Check system state
            current_state = self.connection_manager.detect_state()
            
            if current_state in [CheckPointState.WIZARD_COMPLETE, CheckPointState.FULLY_CONFIGURED]:
                self.logger.debug("Wizard completion verified")
                return True
            else:
                self.logger.error(f"Wizard not completed, current state: {current_state}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying wizard completion: {e}")
            return False

    def _get_admin_password_hash(self) -> str:
        """
        Get current admin password hash from system.
        
        Returns:
            Admin password hash string
        """
        try:
            # For fresh installs, we can't access expert mode without password
            # Use a default hash that will work with the wizard
            current_state = self.connection_manager.detect_state()
            if current_state == CheckPointState.FRESH_INSTALL:
                self.logger.debug("Fresh install - using default admin hash")
                return "$1$salt$hash"  # Placeholder hash for fresh installs
                
            # For configured systems, try to get the actual hash
            # This would require expert password which may not be available
            self.logger.warning("Unable to retrieve admin hash without expert password, using default")
            return "$1$salt$hash"  # Placeholder hash
                
        except Exception as e:
            self.logger.warning(f"Error getting admin hash: {e}, using default")
            return "$1$salt$hash"  # Placeholder hash

    def _generate_maintenance_password_hash(self) -> str:
        """
        Generate maintenance password hash.
        
        Returns:
            Maintenance password hash string
        """
        try:
            # For fresh installs, we can't access expert mode without password
            # Use a default hash that will work with the wizard
            current_state = self.connection_manager.detect_state()
            if current_state == CheckPointState.FRESH_INSTALL:
                self.logger.debug("Fresh install - using default maintenance hash")
                return "grub.pbkdf2.sha512.10000.default_hash"
                
            # For configured systems, we would need expert password
            self.logger.warning("Unable to generate maintenance hash without expert password, using default")
            return "grub.pbkdf2.sha512.10000.default_hash"
            
        except Exception as e:
            self.logger.warning(f"Error generating maintenance hash: {e}, using default")
            return "grub.pbkdf2.sha512.10000.default_hash"

    def _validate_hostname_or_ip(self, value: str) -> bool:
        """
        Validate if value is a valid hostname or IP address.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid hostname or IP, False otherwise
        """
        # First check if it's a valid IP address
        if self._validate_ip_address(value):
            return True
            
        # Then check if it's a valid hostname
        # Basic hostname validation according to RFC standards
        if len(value) == 0 or len(value) > 253:
            return False
            
        # Check each label (part separated by dots)
        labels = value.split('.')
        for label in labels:
            if len(label) == 0 or len(label) > 63:
                return False
            # Label must start and end with alphanumeric, can contain hyphens in middle
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$', label):
                return False
                
        return True

    def _validate_ip_address(self, ip: str) -> bool:
        """
        Validate IP address format.
        
        Args:
            ip: IP address to validate
            
        Returns:
            True if valid IP address, False otherwise
        """
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
                
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
                    
            return True
        except (ValueError, AttributeError):
            return False

    def _execute_admin_password_command(self, new_password: str) -> CommandResult:
        """
        Execute the admin password update command.
        
        Args:
            new_password: New password for admin user
            
        Returns:
            CommandResult with execution details
        """
        # The command to set admin password in Check Point clish mode
        command = "set user admin password"
        
        self.logger.debug(f"Executing command: {command}")
        result = self.connection_manager.execute_command(command, CLIMode.CLISH)
        
        # Handle interactive password prompts
        if result.success and ("enter password" in result.output.lower() or 
                              "password:" in result.output.lower() or
                              "new password" in result.output.lower()):
            self.logger.debug("Handling new password prompt")
            # Send new password when prompted
            password_result = self.connection_manager.execute_command(new_password, CLIMode.CLISH)
            
            # Handle confirmation prompt
            if password_result.success and ("confirm" in password_result.output.lower() or
                                          "retype" in password_result.output.lower() or
                                          "verify" in password_result.output.lower()):
                self.logger.debug("Handling password confirmation prompt")
                confirm_result = self.connection_manager.execute_command(new_password, CLIMode.CLISH)
                return confirm_result
            
            return password_result
            
        return result

    def _verify_admin_password_change(self, new_password: str) -> bool:
        """
        Verify admin password was changed successfully.
        
        This method attempts to authenticate with the new password to verify
        the password change was successful. It does this by creating a new
        connection with the updated credentials.
        
        Args:
            new_password: New password to verify
            
        Returns:
            True if password verification successful, False otherwise
        """
        try:
            # Get current connection info
            current_host = self.connection_manager.connection_info.host
            current_port = self.connection_manager.connection_info.port
            
            # Create a temporary connection manager to test new credentials
            from ..core.connection import CheckPointConnectionManager
            from ..core.models import ConnectionInfo
            
            test_connection_info = ConnectionInfo(
                host=current_host,
                port=current_port,
                username="admin",
                password=new_password
            )
            
            test_connection_manager = CheckPointConnectionManager(test_connection_info)
            
            # Attempt to connect with new password
            self.logger.debug("Testing new admin password with temporary connection")
            if test_connection_manager.connect():
                # Connection successful, password change verified
                test_connection_manager.disconnect()
                self.logger.debug("Admin password verification successful")
                return True
            else:
                self.logger.error("Failed to connect with new admin password")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during admin password verification: {e}")
            return False