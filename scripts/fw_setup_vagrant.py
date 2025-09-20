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
    from checkpoint_automation.expert_password import ExpertPasswordManager
except ImportError:
    # Package not installed, add parent directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from checkpoint_automation.config import FirewallConfig
    from checkpoint_automation.ssh_connection import SSHConnectionManager
    from checkpoint_automation.expert_password import ExpertPasswordManager

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
    
    try:
        # Try with send_command_timing instead of regular execute_command for better timeout handling
        output = ssh_manager.connection.send_command_timing("lock database override", read_timeout=5)
        
        # Check if the command was successful (usually just returns to prompt)
        if "error" not in output.lower() and "failed" not in output.lower():
            print("   ✓ Database lock acquired successfully")
            return True
        else:
            print(f"   ✗ Failed to acquire database lock: {output}")
            return False
            
    except Exception as e:
        print(f"   ⚠ Database lock command had timeout/issues: {e}")
        print("   ℹ Continuing anyway - lock may not be needed if no concurrent access")
        return True  # Continue even if lock fails - it's not always critical

def _set_user_password_interactive(ssh_manager, username: str, password: str) -> bool:
    """Set user password interactively using netmiko with proper write_channel method.
    
    Args:
        ssh_manager: SSH connection manager
        username: Username to set password for
        password: Password to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    import time
    
    try:
        # Send the command using write_channel to avoid timing issues
        ssh_manager.connection.write_channel(f"set user {username} password\n")
        time.sleep(1)
        
        # Read initial output
        output = ssh_manager.connection.read_channel()
        print(f"   Initial output: {output.strip()}")
        
        # Check if we got a password prompt
        if "enter new password:" in output.lower() or "new password:" in output.lower() or "password:" in output.lower():
            # Send first password
            print("   Sending first password...")
            ssh_manager.connection.write_channel(f"{password}\n")
            time.sleep(1)
            
            # Read confirmation prompt
            output = ssh_manager.connection.read_channel()
            print(f"   Confirmation prompt: {output.strip()}")
            
            # Send confirmation password
            print("   Sending confirmation password...")
            ssh_manager.connection.write_channel(f"{password}\n")
            time.sleep(2)
            
            # Read final result
            final_output = ssh_manager.connection.read_channel()
            print(f"   Final output: {final_output.strip()}")
            
            # Check for errors
            combined_output = output + final_output
            if "error" in combined_output.lower() or "failed" in combined_output.lower():
                print(f"   Error in password setting: {combined_output}")
                return False
                
            return True
        else:
            print(f"   Error: No password prompt detected in: {output}")
            return False
        
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
            
            # Step 1: Verify expert password is set up
            print("\n2. Verifying expert password setup...")
            expert_mgr = ExpertPasswordManager(ssh_manager)
            
            password_set, status_msg = expert_mgr.is_expert_password_set()
            print(f"   Expert password status: {status_msg}")
            
            if not password_set:
                print("   ✗ Expert password is not set!")
                print("   Please run fw_set_expert.py first to set up expert mode access")
                return False
            
            # Step 2: Configure user in clish mode
            print("\n3. Configuring vagrant user in clish mode...")
            
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
            print("\n4. Setting vagrant user password...")
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
            
            # Step 3: Configure SSH keys in expert mode
            print("\n5. Switching to expert mode for SSH key configuration...")
            
            if not ssh_manager.enter_expert_mode(expert_password):
                print("   ✗ Failed to enter expert mode")
                return False
            
            print("   ✓ Entered expert mode successfully")
            
            # Create SSH directory and set up keys
            print(f"   Creating SSH directory...")
            result = ssh_manager.execute_command(f"mkdir -p /home/{vagrant_username}/.ssh", timeout=10)
            if not result.success:
                print(f"   ✗ Failed to create SSH directory: {result.error_message}")
                return False
            print(f"   ✓ SSH directory created")
            
            # Write SSH key using a safer method (write to file directly)
            print(f"   Setting up SSH authorized_keys...")
            ssh_key_commands = [
                f"cat > /home/{vagrant_username}/.ssh/authorized_keys << 'EOF'",
                vagrant_public_key,
                "EOF"
            ]
            
            # Execute the heredoc command using write_channel for better control
            import time
            try:
                ssh_manager.connection.write_channel(f"cat > /home/{vagrant_username}/.ssh/authorized_keys << 'EOF'\n")
                time.sleep(0.5)
                ssh_manager.connection.write_channel(f"{vagrant_public_key}\n")
                time.sleep(0.5)
                ssh_manager.connection.write_channel("EOF\n")
                time.sleep(1)
                
                # Read the output to check for errors
                output = ssh_manager.connection.read_channel()
                if "error" in output.lower() or "failed" in output.lower():
                    print(f"   ✗ Error writing SSH key: {output}")
                    return False
                print(f"   ✓ SSH authorized_keys file created")
                
            except Exception as e:
                print(f"   ✗ Error setting up SSH key: {e}")
                return False
            
            # Set permissions
            permission_commands = [
                f"chmod 700 /home/{vagrant_username}/.ssh",
                f"chmod 600 /home/{vagrant_username}/.ssh/authorized_keys"
            ]
            
            for cmd in permission_commands:
                print(f"   Executing: {cmd}")
                result = ssh_manager.execute_command(cmd, timeout=10)
                if not result.success:
                    print(f"   ✗ Command failed: {cmd}")
                    print(f"     Error: {result.error_message}")
                    return False
                print(f"   ✓ Command successful")
            
            # Check user ID to get correct ownership
            print("\n6. Setting correct ownership for SSH files...")
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
            print(f"\n7. Verifying {vagrant_username} user setup...")
            
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