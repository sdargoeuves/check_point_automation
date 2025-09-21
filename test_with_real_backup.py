#!/usr/bin/env python3
"""Simple test script for deploying a real Check Point backup file."""

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from checkpoint_automation import (
    FirewallConfig,
    ScriptDeploymentManager,
    SSHConnectionManager,
)


def main():
    """Deploy a real Check Point backup file."""

    # UPDATE THESE VALUES
    FIREWALL_IP = "10.194.58.200"  # Your firewall IP
    USERNAME = "admin"
    PASSWORD = "admin"
    EXPERT_PASSWORD = "admin15"  # Your expert password

    # UPDATE THIS PATH to your actual backup file
    BACKUP_FILE_PATH = "/path/to/your/checkpoint_backup.tgz"

    # Verify backup file exists
    if not os.path.exists(BACKUP_FILE_PATH):
        print(f"❌ Backup file not found: {BACKUP_FILE_PATH}")
        print("\nPlease update BACKUP_FILE_PATH with the correct path to your backup file.")
        print("Examples:")
        print("  - /Users/username/Downloads/checkpoint_backup.tgz")
        print("  - /home/user/backups/fw_config_backup.tgz")
        print("  - C:\\Users\\username\\Downloads\\backup.tgz")
        return False

    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD,
    )

    print("Check Point Backup Deployment Test")
    print("=" * 50)
    print(f"Firewall: {FIREWALL_IP}")
    print(f"Backup file: {BACKUP_FILE_PATH}")
    print(f"File size: {os.path.getsize(BACKUP_FILE_PATH)} bytes")
    print()

    try:
        # Connect to firewall
        print("Connecting to firewall...")
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            print("✓ Connected successfully")

            # Create script manager
            script_manager = ScriptDeploymentManager(ssh_manager)

            # Deploy the backup file
            print("Deploying backup file...")
            success, message = script_manager.deploy_binary_file(
                local_file_path=BACKUP_FILE_PATH,
                remote_file_path=f"/home/admin/{os.path.basename(BACKUP_FILE_PATH)}",
            )

            if success:
                print("✓ Backup file deployed successfully!")
                print(f"Remote location: /home/admin/{os.path.basename(BACKUP_FILE_PATH)}")

                # Verify the file on the firewall
                print("Verifying deployed file...")
                response = ssh_manager.execute_command(f"ls -la /home/admin/{os.path.basename(BACKUP_FILE_PATH)}")
                if response.success:
                    print("✓ File verification successful:")
                    print(f"  {response.output}")
                else:
                    print(f"⚠️  File verification failed: {response.error_message}")

                print("\n🎉 Backup deployment completed successfully!")
                print("\nNext steps:")
                print("1. You can now restore this backup using Check Point commands")
                print("2. Or use the checkpoint_backup_restore.py example for automated restore")

            else:
                print(f"❌ Backup deployment failed: {message}")
                return False

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
