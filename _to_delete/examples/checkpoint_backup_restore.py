#!/usr/bin/env python3
"""
Example: Deploy and restore a Check Point configuration backup.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from checkpoint_automation import (
    FirewallConfig, 
    SSHConnectionManager, 
    ExpertPasswordManager,
    ScriptDeploymentManager
)


def main():
    """Example of deploying and restoring a Check Point backup."""
    
    # Configuration
    config = FirewallConfig(
        ip_address="YOUR_FIREWALL_IP",  # Update this
        username="admin",
        password="admin", 
        expert_password="YOUR_EXPERT_PASSWORD"  # Update this
    )
    
    # Path to your Check Point backup file
    backup_file_path = "/path/to/your/checkpoint_backup.tgz"  # Update this path
    
    # Check Point restore script
    restore_script = """#!/bin/bash
# Check Point Configuration Restore Script
echo "Starting Check Point configuration restore..."

# Variables
BACKUP_FILE="/home/admin/checkpoint_backup.tgz"
RESTORE_LOG="/home/admin/restore.log"

# Function to log messages
log_message() {
    echo "$(date): $1" | tee -a $RESTORE_LOG
}

log_message "=== Check Point Restore Process Started ==="

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_message "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

log_message "Backup file found: $BACKUP_FILE"
log_message "Backup file size: $(ls -lh $BACKUP_FILE | awk '{print $5}')"

# Check available disk space
AVAILABLE_SPACE=$(df /home | tail -1 | awk '{print $4}')
log_message "Available disk space: ${AVAILABLE_SPACE}KB"

# Extract and examine backup (optional)
log_message "Examining backup contents..."
tar -tzf $BACKUP_FILE | head -10 | while read line; do
    log_message "  $line"
done

# Perform the actual restore
log_message "Starting configuration restore..."

# Method 1: Using migrate import (for R80.x and later)
if command -v migrate >/dev/null 2>&1; then
    log_message "Using migrate import command..."
    migrate import $BACKUP_FILE 2>&1 | tee -a $RESTORE_LOG
    RESTORE_EXIT_CODE=${PIPESTATUS[0]}
else
    # Method 2: Using cpconfig restore (for older versions)
    log_message "Using cpconfig restore command..."
    cpconfig restore $BACKUP_FILE 2>&1 | tee -a $RESTORE_LOG
    RESTORE_EXIT_CODE=${PIPESTATUS[0]}
fi

# Check restore result
if [ $RESTORE_EXIT_CODE -eq 0 ]; then
    log_message "Configuration restore completed successfully"
    log_message "System will reboot to apply changes..."
    
    # Schedule reboot after a short delay
    log_message "Rebooting system in 30 seconds..."
    sleep 30
    reboot
else
    log_message "ERROR: Configuration restore failed with exit code $RESTORE_EXIT_CODE"
    log_message "Please check the restore log for details"
    exit 1
fi

log_message "=== Check Point Restore Process Completed ==="
"""
    
    print("Check Point Backup Restore Example")
    print("=" * 50)
    
    # Validate backup file exists
    if not os.path.exists(backup_file_path):
        print(f"❌ Backup file not found: {backup_file_path}")
        print("Please update the backup_file_path variable with the correct path to your backup file.")
        return False
    
    try:
        # Step 1: Connect to firewall
        print(f"Connecting to firewall at {config.ip_address}...")
        ssh_manager = SSHConnectionManager(config, console_log_level="INFO")
        
        if not ssh_manager.connect():
            print("❌ Failed to connect to firewall")
            return False
        
        print("✓ Connected to firewall")
        
        # Step 2: Setup expert password if needed
        print("Setting up expert password...")
        expert_manager = ExpertPasswordManager(ssh_manager)
        
        success, message = expert_manager.setup_expert_password_workflow(config.expert_password)
        if not success:
            print(f"❌ Failed to setup expert password: {message}")
            ssh_manager.disconnect()
            return False
        
        print("✓ Expert password setup completed")
        
        # Step 3: Deploy backup file and restore script
        print("Deploying Check Point backup and restore script...")
        script_manager = ScriptDeploymentManager(ssh_manager)
        
        success, output = script_manager.deploy_checkpoint_backup(
            backup_file_path=backup_file_path,
            restore_script_content=restore_script
        )
        
        if success:
            print("✓ Backup deployment and restore script execution successful!")
            print("\nRestore process output:")
            print("-" * 60)
            print(output)
            print("-" * 60)
            
            # Check if reboot is happening
            if "reboot" in output.lower():
                print("\n⚠️  System reboot detected")
                print("The firewall is rebooting to apply the restored configuration...")
                print("Waiting for system to come back online...")
                
                reboot_success, reboot_message = script_manager.handle_reboot_scenario(max_wait_time=900)  # 15 minutes
                if reboot_success:
                    print("✓ System came back online after configuration restore")
                    
                    # Verify the system is working
                    print("Verifying system status after restore...")
                    status_response = ssh_manager.execute_command("cpstat fw")
                    if status_response.success:
                        print("✓ Firewall services are running")
                    else:
                        print("⚠️  Could not verify firewall status")
                        
                else:
                    print(f"⚠️  System did not come back online: {reboot_message}")
                    print("You may need to check the system manually")
        else:
            print(f"❌ Backup deployment failed: {output}")
            return False
        
        # Step 4: Cleanup
        ssh_manager.disconnect()
        print("\n✓ Check Point backup restore process completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def create_sample_restore_script_only():
    """Create a sample restore script without deploying a backup file."""
    
    config = FirewallConfig(
        ip_address="YOUR_FIREWALL_IP",
        username="admin",
        password="admin",
        expert_password="YOUR_EXPERT_PASSWORD"
    )
    
    # Simple restore script that works with an existing backup
    simple_restore_script = """#!/bin/bash
# Simple Check Point Restore Script
echo "Looking for backup files in /home/admin/..."

# List available backup files
BACKUP_FILES=$(ls /home/admin/*.tgz 2>/dev/null)

if [ -z "$BACKUP_FILES" ]; then
    echo "No backup files found in /home/admin/"
    echo "Please upload a backup file first"
    exit 1
fi

echo "Available backup files:"
ls -la /home/admin/*.tgz

# Use the first backup file found
BACKUP_FILE=$(ls /home/admin/*.tgz | head -1)
echo "Using backup file: $BACKUP_FILE"

# Restore the configuration
echo "Starting restore process..."
migrate import "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Restore completed successfully"
    echo "System will reboot in 30 seconds..."
    sleep 30
    reboot
else
    echo "Restore failed"
    exit 1
fi
"""
    
    try:
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            script_manager = ScriptDeploymentManager(ssh_manager)
            
            success, output = script_manager.deploy_and_execute_script(simple_restore_script)
            
            if success:
                print("✓ Restore script executed successfully")
                print(output)
            else:
                print(f"❌ Restore script failed: {output}")
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("Choose an option:")
    print("1. Deploy backup file and restore (requires backup file)")
    print("2. Deploy restore script only (works with existing backup on firewall)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        success = main()
        sys.exit(0 if success else 1)
    elif choice == "2":
        create_sample_restore_script_only()
    else:
        print("Invalid choice")
        sys.exit(1)