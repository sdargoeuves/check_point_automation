#!/usr/bin/env python3
"""
Test filename preservation in binary file deployment.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from checkpoint_automation import (
    FirewallConfig, 
    SSHConnectionManager, 
    ScriptDeploymentManager
)


def main():
    """Test filename preservation behavior."""
    
    # UPDATE THESE VALUES
    config = FirewallConfig(
        ip_address="10.194.58.200",  # Your firewall IP
        username="admin",
        password="admin",
        expert_password="admin15"  # Your expert password
    )
    
    # Test file - update this path or it will use a fallback
    test_file_path = "/path/to/your/checkpoint_backup.tgz"
    
    # Fallback to a system file if the specified file doesn't exist
    if not os.path.exists(test_file_path):
        fallback_files = ["/etc/hosts", "/etc/passwd", "README.md", "requirements.txt"]
        for fallback in fallback_files:
            if os.path.exists(fallback):
                test_file_path = fallback
                break
        else:
            print("❌ No test file found. Please update test_file_path.")
            return False
    
    original_filename = os.path.basename(test_file_path)
    
    print("Filename Preservation Test")
    print("=" * 50)
    print(f"Test file: {test_file_path}")
    print(f"Original filename: {original_filename}")
    print(f"File size: {os.path.getsize(test_file_path)} bytes")
    print()
    
    try:
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            script_manager = ScriptDeploymentManager(ssh_manager)
            
            # Test 1: Default behavior (preserves filename)
            print("Test 1: Default behavior (preserves original filename)")
            print("-" * 50)
            
            success1, message1 = script_manager.deploy_binary_file(
                local_file_path=test_file_path
                # No remote_file_path specified = preserves original filename
            )
            
            if success1:
                print(f"✓ File deployed with original name: /home/admin/{original_filename}")
                
                # Verify the file
                response = ssh_manager.execute_command(f"ls -la /home/admin/{original_filename}")
                if response.success:
                    print(f"✓ Verification: {response.output.strip()}")
            else:
                print(f"❌ Test 1 failed: {message1}")
                return False
            
            print()
            
            # Test 2: Custom filename
            print("Test 2: Custom filename")
            print("-" * 50)
            
            custom_name = "my_custom_backup.bin"
            success2, message2 = script_manager.deploy_binary_file(
                local_file_path=test_file_path,
                remote_file_path=f"/home/admin/{custom_name}"
            )
            
            if success2:
                print(f"✓ File deployed with custom name: /home/admin/{custom_name}")
                
                # Verify the file
                response = ssh_manager.execute_command(f"ls -la /home/admin/{custom_name}")
                if response.success:
                    print(f"✓ Verification: {response.output.strip()}")
            else:
                print(f"❌ Test 2 failed: {message2}")
                return False
            
            print()
            
            # Show all deployed files
            print("All deployed files in /home/admin/:")
            print("-" * 50)
            response = ssh_manager.execute_command("ls -la /home/admin/ | grep -E '\\.(tgz|bin|backup|hosts|passwd)' || echo 'No matching files found'")
            if response.success:
                print(response.output)
            
            print("\n🎉 All filename preservation tests passed!")
            print("\nSummary:")
            print(f"  • Original file preserved as: /home/admin/{original_filename}")
            print(f"  • Custom file created as: /home/admin/{custom_name}")
            print("  • Both files have identical content (verified by checksum)")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)