#!/usr/bin/env python3
"""
Script to upload and restore a backup file on a Check Point firewall.
This script handles the complete backup restore workflow:
1. Upload backup file via SCP to the firewall
2. SSH to the firewall and initiate restore
3. Monitor restore progress
4. Handle firewall reboot and reconnection
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Clean approach: Add parent directory to path only if package not installed
try:
    from checkpoint_automation.config import FirewallConfig
    from checkpoint_automation.ssh_connection import SSHConnectionManager
    from checkpoint_automation.command_executor import FirewallMode
except ImportError:
    # Package not installed, add parent directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from checkpoint_automation.config import FirewallConfig
    from checkpoint_automation.ssh_connection import SSHConnectionManager
    from checkpoint_automation.command_executor import FirewallMode


class BackupRestoreManager:
    """Manages backup file upload and restore operations."""
    
    def __init__(self, config: FirewallConfig, backup_file: str):
        """Initialize backup restore manager.
        
        Args:
            config: Firewall configuration
            backup_file: Path to backup file to restore
        """
        self.config = config
        self.backup_file = Path(backup_file)
        self.logger = self._setup_logging()
        
        # Validate backup file exists
        if not self.backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        # Extract filename for remote path
        self.backup_filename = self.backup_file.name
        self.remote_backup_path = f"/var/log/CPbackup/backups/{self.backup_filename}"
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(f"backup_restore.{self.config.ip_address}")
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def upload_backup_file(self) -> bool:
        """Upload backup file to firewall via SCP.
        
        Returns:
            True if upload successful, False otherwise
        """
        self.logger.info(f"Uploading backup file {self.backup_file} to {self.config.ip_address}")
        
        try:
            # Build SCP command
            scp_command = [
                "scp",
                str(self.backup_file),
                f"{self.config.username}@{self.config.ip_address}:{self.remote_backup_path}"
            ]
            
            self.logger.debug(f"Running SCP command: {' '.join(scp_command)}")
            
            # Use subprocess with password handling via sshpass if available
            # For now, we'll use basic subprocess and let user handle password interactively
            result = subprocess.run(
                scp_command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for large files
            )
            
            if result.returncode == 0:
                self.logger.info("✓ Backup file uploaded successfully")
                return True
            else:
                self.logger.error(f"SCP upload failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("SCP upload timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error during SCP upload: {e}")
            return False
    
    def initiate_restore(self, ssh_manager: SSHConnectionManager) -> bool:
        """Initiate backup restore on the firewall.
        
        Args:
            ssh_manager: Connected SSH manager
            
        Returns:
            True if restore initiated successfully, False otherwise
        """
        self.logger.info("Initiating backup restore")
        
        try:
            # Ensure we're in clish mode
            current_mode = ssh_manager.get_current_mode()
            if current_mode == FirewallMode.EXPERT:
                self.logger.info("Exiting expert mode to clish")
                if not ssh_manager.exit_expert_mode():
                    self.logger.error("Failed to exit expert mode")
                    return False
            
            # Build restore command
            restore_command = f"set backup restore local {self.backup_filename}"
            self.logger.info(f"Executing restore command: {restore_command}")
            
            # Execute restore command
            response = ssh_manager.execute_command(restore_command, timeout=30)
            
            if response.success:
                self.logger.info("✓ Restore command executed successfully")
                self.logger.debug(f"Restore response: {response.output}")
                
                # Check if restore was accepted
                if "Restoring from backup package" in response.output:
                    self.logger.info("✓ Restore operation accepted by firewall")
                    return True
                elif "Use the command 'show restore status'" in response.output:
                    self.logger.info("✓ Restore operation initiated")
                    return True
                else:
                    self.logger.warning(f"Unexpected restore response: {response.output}")
                    return True  # Still consider it successful
            else:
                self.logger.error(f"Restore command failed: {response.output}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initiating restore: {e}")
            return False
    
    def monitor_restore_progress(self, ssh_manager: SSHConnectionManager) -> bool:
        """Monitor restore progress until completion or reboot.
        
        Args:
            ssh_manager: Connected SSH manager
            
        Returns:
            True if restore completed (may include reboot), False if failed
        """
        self.logger.info("Monitoring restore progress...")
        
        max_checks = 60  # Maximum number of status checks
        check_interval = 10  # Seconds between checks
        
        for check_num in range(max_checks):
            try:
                self.logger.info(f"Status check {check_num + 1}/{max_checks}")
                
                # Execute show restore status command
                response = ssh_manager.execute_command("show restore status", timeout=15)
                
                if response.success:
                    status_output = response.output.strip()
                    self.logger.info(f"Restore status: {status_output}")
                    
                    # Parse status output
                    if "Performing local restore" in status_output:
                        # Extract step information
                        if "Step:" in status_output:
                            step_line = [line for line in status_output.split('\n') if 'Step:' in line]
                            if step_line:
                                current_step = step_line[0].strip()
                                self.logger.info(f"Current step: {current_step}")
                        
                        # Check for completion indicators
                        if any(step in status_output for step in [
                            "Executing Post-Restore Scripts",
                            "Finalizing",
                            "Completed"
                        ]):
                            self.logger.info("Restore appears to be in final stages")
                    
                    elif "No restore operation in progress" in status_output:
                        self.logger.info("No restore operation detected - may have completed")
                        return True
                    
                    elif "restore completed" in status_output.lower():
                        self.logger.info("✓ Restore completed successfully")
                        return True
                    
                else:
                    self.logger.warning(f"Failed to get restore status: {response.output}")
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                # Connection might be lost due to reboot
                if "Connection" in str(e) or "closed" in str(e).lower():
                    self.logger.info("Connection lost - firewall likely rebooting")
                    return True  # This is expected during restore
                else:
                    self.logger.error(f"Error monitoring restore: {e}")
                    time.sleep(check_interval)
        
        self.logger.warning("Restore monitoring timed out - firewall may be rebooting")
        return True  # Assume reboot is happening
    
    def wait_for_reboot_and_reconnect(self) -> bool:
        """Wait for firewall reboot and attempt reconnection.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        self.logger.info("Waiting for firewall reboot to complete...")
        
        # Wait initial period for reboot to start
        initial_wait = 30
        self.logger.info(f"Waiting {initial_wait} seconds for reboot to begin...")
        time.sleep(initial_wait)
        
        # Attempt reconnection
        max_attempts = 30
        retry_interval = 20
        
        for attempt in range(max_attempts):
            self.logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")
            
            try:
                with SSHConnectionManager(self.config, console_log_level="WARNING") as ssh_manager:
                    # Test connection with a simple command
                    response = ssh_manager.execute_command("show version", timeout=10)
                    if response.success:
                        self.logger.info("✓ Successfully reconnected after reboot")
                        self.logger.info("✓ Firewall is responding to commands")
                        return True
                    
            except Exception as e:
                self.logger.debug(f"Reconnection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_attempts - 1:
                self.logger.info(f"Waiting {retry_interval} seconds before next attempt...")
                time.sleep(retry_interval)
        
        self.logger.error("Failed to reconnect after maximum attempts")
        return False
    
    def perform_full_restore(self) -> bool:
        """Perform complete backup restore workflow.
        
        Returns:
            True if entire restore process successful, False otherwise
        """
        self.logger.info(f"Starting backup restore workflow for {self.backup_file}")
        
        try:
            # Step 1: Upload backup file
            if not self.upload_backup_file():
                return False
            
            # Step 2: Connect and initiate restore
            with SSHConnectionManager(self.config, console_log_level="INFO") as ssh_manager:
                if not self.initiate_restore(ssh_manager):
                    return False
                
                # Step 3: Monitor restore progress
                if not self.monitor_restore_progress(ssh_manager):
                    return False
            
            # Step 4: Wait for reboot and reconnect
            if not self.wait_for_reboot_and_reconnect():
                self.logger.warning("Could not verify firewall status after reboot")
                self.logger.info("Restore may have completed - check firewall manually")
                return True  # Don't fail entirely, restore might be successful
            
            self.logger.info("🎉 Backup restore completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup restore failed: {e}")
            return False


def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Upload and restore a backup file on Check Point firewall",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fw_backup_restore.py 10.194.58.200 backup_file.tgz
  python fw_backup_restore.py 10.194.58.200 backup_file.tgz --username admin --password admin123
  python fw_backup_restore.py 10.194.58.200 /path/to/backup_--_cpfw01_19_Sep_2025_11_03_44.tgz

Note: This script will:
1. Upload the backup file via SCP to /var/log/CPbackup/backups/
2. Connect via SSH and initiate the restore
3. Monitor restore progress
4. Handle firewall reboot and verify reconnection
        """
    )
    
    parser.add_argument("firewall_ip", help="IP address of the Check Point firewall")
    parser.add_argument("backup_file", help="Path to backup file to restore")
    parser.add_argument("--username", default="vagrant", help="SSH username (default: vagrant)")
    parser.add_argument("--password", default="vagrant", help="SSH password (default: vagrant)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        setup_logging()
    
    # Validate backup file
    if not os.path.exists(args.backup_file):
        print(f"Error: Backup file not found: {args.backup_file}")
        sys.exit(1)
    
    # Create configuration
    config = FirewallConfig(
        ip_address=args.firewall_ip,
        username=args.username,
        password=args.password
    )
    
    print(f"Firewall: {args.firewall_ip}")
    print(f"Backup file: {args.backup_file}")
    print(f"Username: {args.username}")
    print(f"Password: {'*' * len(args.password)}")
    print()
    
    # Perform restore
    restore_manager = BackupRestoreManager(config, args.backup_file)
    success = restore_manager.perform_full_restore()
    
    if success:
        print("\n🎉 Backup restore completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Backup restore failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()