#!/usr/bin/env python3
"""
Script to setup the vagrant user on a real Check Point firewall.
Assumes that fw_set_expert.py has been run first to set up expert mode access.
"""

import logging
import sys
import os

# Clean approach: Add parent directory to path only if package not installed
try:
    from checkpoint_automation.config import FirewallConfig
    from checkpoint_automation.ssh_connection import SSHConnectionManager
except ImportError:
    # Package not installed, add parent directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from checkpoint_automation.config import FirewallConfig
    from checkpoint_automation.ssh_connection import SSHConnectionManager

def setup_logging():
    """Set up logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def _acquire_database_lock(ssh_manager) -> bool:
    """Acquire database lock using 'lock database override' command.
    
    Args:
        ssh_manager: SSH connection manager
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("   Acquiring database lock...")
    result = ssh_manager.execute_command("lock database override", timeout=10)
    
    if result.success:
        print("   ✓ Database lock acquired successfully")
        return True
    else:
        print(f"   ✗ Failed to acquire database lock: {result.error_message}")
        return False

def _set_user_password_interactive(ssh_manager, username: str, password: str) -> bool:
    """Set user password interactively using shell commands.
    
    Args:
        ssh_manager: SSH connection manager
        username: Username to set password for
        password: Password to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    import time
    
    try:
        # Send the command
        ssh_manager.shell.send(f"set user {username} password\n")
        
        # Wait for first password prompt and send password
        time.sleep(2)
        ssh_manager.shell.send(f"{password}\n")
        
        # Wait for confirmation prompt and send password again
        time.sleep(1)
        ssh_manager.shell.send(f"{password}\n")
        
        # Wait for command completion
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"   Error setting password: {e}")
        return False

def setup_vagrant_user(ip_address: str, username: str = "admin", password: str = "admin", expert_password: str = "admin15"):
    """Setup vagrant user on a Check Point firewall.
    
    Args:
        ip_address: IP address of the firewall
        username: SSH username (default: admin)
        password: SSH password (default: admin)
        expert_password: Expert password for accessing expert mode (default: admin15)
    """
    print(f"\n=== Setting up Vagrant User on {ip_address} ===")
    
    # Create configuration
    config = FirewallConfig(
        ip_address=ip_address,
        username=username,
        password=password,
        expert_password=expert_password
    )
    
    # Vagrant insecure information (SSH key and user/pwd)
    vagrant_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key"
    vagrant_username = "vagrant"
    vagrant_password = "vagrant"
    
    try:
        # Connect to firewall
        print(f"1. Connecting to firewall at {ip_address}...")
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            print("   ✓ Connected successfully")
            
            # Detect initial mode
            initial_mode = ssh_manager.detect_mode()
            print(f"   ✓ Initial mode detected: {initial_mode.value}")
            
            # Step 1: Configure user in clish mode
            print("\n2. Configuring vagrant user in clish mode...")
            
            # Ensure we're in clish mode
            if initial_mode.value != "clish":
                print("   Switching to clish mode...")
                if not ssh_manager.exit_expert_mode():
                    print("   ✗ Failed to switch to clish mode")
                    return False
            
            # Acquire database lock before making configuration changes
            if not _acquire_database_lock(ssh_manager):
                print("   ✗ Failed to acquire database lock - cannot proceed with configuration changes")
                return False
            
            clish_commands = [
                "set password-controls complexity 1",
                "save config",
                f"add user {vagrant_username} uid 2000 homedir /home/{vagrant_username}",
                f"add rba user {vagrant_username} roles adminRole",
                f"set user {vagrant_username} shell /bin/bash",
                # "set ssh server password-authentication yes",
                # "set ssh server permit-root-login yes",
                "save config"
            ]
            
            for cmd in clish_commands:
                print(f"   Executing: {cmd}")
                result = ssh_manager.execute_command(cmd, timeout=30)
                if not result.success:
                    # Check if failure is due to database lock issue
                    if "lock" in result.error_message.lower() and "database" in result.error_message.lower():
                        print(f"   ⚠ Command failed due to database lock issue, retrying with lock acquisition...")
                        if _acquire_database_lock(ssh_manager):
                            print(f"   Retrying: {cmd}")
                            result = ssh_manager.execute_command(cmd, timeout=30)
                            if not result.success:
                                print(f"   ✗ Command failed even after acquiring lock: {cmd}")
                                print(f"     Error: {result.error_message}")
                                return False
                        else:
                            print(f"   ✗ Could not acquire database lock for retry")
                            return False
                    else:
                        print(f"   ✗ Command failed: {cmd}")
                        print(f"     Error: {result.error_message}")
                        return False
                print(f"   ✓ Command successful")
            
            # Set vagrant user password
            print("\n3. Setting vagrant user password...")
            print("   Executing: set user vagrant password")
            
            # Send the command and handle interactive password prompts
            success = _set_user_password_interactive(ssh_manager, "vagrant", "vagrant")
            if not success:
                print("   ⚠ Password setting failed, trying with database lock acquisition...")
                if _acquire_database_lock(ssh_manager):
                    success = _set_user_password_interactive(ssh_manager, "vagrant", "vagrant")
                    if not success:
                        print("   ✗ Failed to set vagrant user password even after acquiring lock")
                        return False
                else:
                    print("   ✗ Failed to set vagrant user password and could not acquire database lock")
                    return False
            
            print("   ✓ Password set for vagrant user")
            
            # Step 2: Configure SSH keys in expert mode
            print("\n4. Switching to expert mode for SSH key configuration...")
            
            if not ssh_manager.enter_expert_mode(expert_password):
                print("   ✗ Failed to enter expert mode")
                print("   Please ensure fw_set_expert.py has been run first to set up expert mode access")
                return False
            
            print("   ✓ Entered expert mode successfully")
            
            # Create SSH directory and set up keys
            expert_commands = [
                f"mkdir -p /home/{vagrant_username}/.ssh",
                f'echo "{vagrant_public_key}" > /home/{vagrant_username}/.ssh/authorized_keys',
                f"chmod 700 /home/{vagrant_username}/.ssh",
                f"chmod 600 /home/{vagrant_username}/.ssh/authorized_keys"
            ]
            
            for cmd in expert_commands:
                print(f"   Executing: {cmd}")
                result = ssh_manager.execute_command(cmd, timeout=30)
                if not result.success:
                    print(f"   ✗ Command failed: {cmd}")
                    print(f"     Error: {result.error_message}")
                    return False
                print(f"   ✓ Command successful")
            
            # Check user ID to get correct ownership
            print("\n5. Setting correct ownership for SSH files...")
            print(f"   Checking {vagrant_username} user details...")
            result = ssh_manager.execute_command(f"id {vagrant_username}", timeout=10)
            if result.success:
                print(f"   User details: {result.output.strip()}")
                
                # Set ownership (assuming vagrant:users based on typical Check Point setup)
                ownership_cmd = f"chown -R {vagrant_username}:users /home/{vagrant_username}/.ssh"
                print(f"   Executing: {ownership_cmd}")
                result = ssh_manager.execute_command(ownership_cmd, timeout=30)
                if not result.success:
                    print(f"   ✗ Ownership command failed: {ownership_cmd}")
                    print(f"     Error: {result.error_message}")
                    # Try alternative group
                    alt_ownership_cmd = f"chown -R {vagrant_username}:{vagrant_username} /home/{vagrant_username}/.ssh"
                    print(f"   Trying alternative: {alt_ownership_cmd}")
                    result = ssh_manager.execute_command(alt_ownership_cmd, timeout=30)
                    if not result.success:
                        print(f"   ✗ Alternative ownership command also failed")
                        return False
                
                print("   ✓ Ownership set successfully")
            else:
                print(f"   ✗ Failed to check user details: {result.error_message}")
                return False
            
            # Verify setup
            print(f"\n6. Verifying {vagrant_username} user setup...")
            
            # Check if user exists and has correct shell
            result = ssh_manager.execute_command(f"grep {vagrant_username} /etc/passwd", timeout=10)
            if result.success:
                print(f"   ✓ User entry: {result.output.strip()}")
            else:
                print(f"   ✗ {vagrant_username} user not found in /etc/passwd")
                return False
            
            # Check SSH directory
            result = ssh_manager.execute_command(f"ls -la /home/{vagrant_username}/.ssh/", timeout=10)
            if result.success:
                print(f"   ✓ SSH directory contents:")
                for line in result.output.strip().split('\n'):
                    print(f"     {line}")
            else:
                print("   ✗ SSH directory not accessible")
                return False
            
            print(f"\n=== {vagrant_username} User Setup Successful! ===")
            print("You can now SSH to this firewall using:")
            print(f"  ssh -i ~/.vagrant.d/insecure_private_key {vagrant_username}@{ip_address}")
            return True
            
    except Exception as e:
        print(f"\n✗ Setup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the vagrant user setup."""
    setup_logging()
    
    if len(sys.argv) < 2:
        print("Usage: python fw_setup_vagrant.py <firewall_ip> [username] [password] [expert_password]")
        print("Example: python fw_setup_vagrant.py 10.194.59.200")
        print("Example: python fw_setup_vagrant.py 10.194.59.200 admin admin admin15")
        print("\nNote: This script assumes fw_set_expert.py has been run first to set up expert mode access.")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"
    password = sys.argv[3] if len(sys.argv) > 3 else "admin"
    expert_password = sys.argv[4] if len(sys.argv) > 4 else "admin15"
    
    print(f"Setting up vagrant user on firewall: {ip_address}")
    print(f"Admin username: {username}")
    print(f"Admin password: {'*' * len(password)}")
    print(f"Expert password: {'*' * len(expert_password)}")
    
    success = setup_vagrant_user(ip_address, username, password, expert_password)
    
    if success:
        print("\n🎉 Vagrant user setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Vagrant user setup failed. Check the output above for details.")
        print("If expert mode access failed, please run fw_set_expert.py first.")
        sys.exit(1)

if __name__ == "__main__":
    main()