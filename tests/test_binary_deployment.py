#!/usr/bin/env python3
"""
Test binary file deployment functionality.

USAGE:
1. Update the firewall IP and credentials in the test functions
2. Update the file path in get_test_file_path() to point to your test file
   (e.g., a Check Point backup file, or any existing file)
3. Run: python tests/test_binary_deployment.py
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from checkpoint_automation import FirewallConfig, SSHConnectionManager, ScriptDeploymentManager


def get_test_file_path():
    """Get path to an existing file for testing binary deployment."""
    
    # List of potential test files (in order of preference)
    potential_files = [
        # User-specified test file (update this path)
        "/path/to/your/checkpoint_backup.tgz",  # UPDATE THIS PATH
        
        # Files in current directory
        # "README.md",
        "requirements.txt",
        # "test.zip",
        
        # Python files in the project
        "checkpoint_automation/__init__.py",
        "tests/test_script_deployment.py",
    ]
    
    for file_path in potential_files:
        if os.path.exists(file_path):
            print(f"found the file: {file_path}")
            return file_path
    
    return None


def test_binary_deployment():
    """Test binary file deployment functionality."""
    
    # Configuration - update as needed
    config = FirewallConfig(
        ip_address="10.194.58.200",  # Replace with your firewall IP
        username="admin",
        password="admin",
        expert_password="admin15"  # Replace with your expert password
    )
    
    print(f"Testing binary file deployment to {config.ip_address}")
    
    # Get an existing test file
    test_file_path = get_test_file_path()
    
    if not test_file_path:
        print("❌ No suitable test file found!")
        print("Please update the file path in get_test_file_path() function")
        print("Suggestions:")
        print("  - Update '/path/to/your/checkpoint_backup.tgz' with your actual backup file")
        print("  - Or use any existing file you want to test with")
        return False
    
    print(f"Using test file: {test_file_path}")
    print(f"File size: {os.path.getsize(test_file_path)} bytes")
    
    try:
        # Create SSH connection
        with SSHConnectionManager(config, console_log_level="DEBUG") as ssh_manager:
            print("✓ SSH connection established")
            
            # Create script deployment manager
            script_manager = ScriptDeploymentManager(ssh_manager)
            print("✓ Script deployment manager created")
            
            # Deploy the test binary file (preserving original filename)
            original_filename = os.path.basename(test_file_path)
            
            print(f"Deploying test binary file: {original_filename}")
            print("(Using default remote path to preserve original filename)")
            
            # Don't specify remote_file_path to use default behavior (preserves filename)
            success, message = script_manager.deploy_binary_file(
                local_file_path=test_file_path
                # remote_file_path not specified = defaults to /home/admin/original_filename
            )
            
            # Set the expected remote path for verification
            remote_path = f"/home/admin/{original_filename}"
            
            if success:
                print("✓ Binary file deployment successful!")
                print(f"Status: {message}")
                
                # Verify the file exists and has correct content
                print("Verifying deployed file...")
                response = ssh_manager.execute_command(f"ls -la {remote_path}")
                if response.success:
                    print(f"✓ File exists: {response.output}")
                    
                    # Also show the file type and any additional info
                    file_response = ssh_manager.execute_command(f"file {remote_path}")
                    if file_response.success:
                        print(f"✓ File type: {file_response.output}")
                else:
                    print(f"✗ File verification failed: {response.error_message}")
                
            else:
                print(f"✗ Binary file deployment failed: {message}")
                return False
            
            print("\n✓ All binary deployment tests passed!")
            return True
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False


def test_checkpoint_backup_deployment():
    """Test Check Point backup deployment with restore script."""
    
    # Configuration
    config = FirewallConfig(
        ip_address="10.194.58.200",
        username="admin", 
        password="admin",
        expert_password="admin15"
    )
    
    # Use an existing file as mock backup
    backup_path = get_test_file_path()
    
    if not backup_path:
        print("❌ No test file available for backup deployment test")
        return False
    
    # Sample restore script
    restore_script = """#!/bin/bash
# Check Point Backup Restore Script
echo "Starting Check Point backup restore..."

BACKUP_FILE="/home/admin/$(basename {backup_file})"

if [ -f "$BACKUP_FILE" ]; then
    echo "Backup file found: $BACKUP_FILE"
    echo "File size: $(ls -lh $BACKUP_FILE | awk '{{print $5}}')"
    
    # In a real scenario, you would use:
    # migrate import $BACKUP_FILE
    # Or other Check Point restore commands
    
    echo "Backup restore simulation completed"
else
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi
""".format(backup_file=os.path.basename(backup_path))
    
    print(f"Testing Check Point backup deployment to {config.ip_address}")
    
    try:
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            script_manager = ScriptDeploymentManager(ssh_manager)
            
            # Deploy backup with restore script
            success, message = script_manager.deploy_checkpoint_backup(
                backup_file_path=backup_path,
                restore_script_content=restore_script
            )
            
            if success:
                print("✓ Check Point backup deployment successful!")
                print(f"Result: {message}")
            else:
                print(f"✗ Check Point backup deployment failed: {message}")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    print("Binary File Deployment Tests")
    print("=" * 50)
    
    print("\n1. Testing basic binary file deployment...")
    test1_success = test_binary_deployment()
    
    print("\n2. Testing Check Point backup deployment...")
    test2_success = test_checkpoint_backup_deployment()
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)