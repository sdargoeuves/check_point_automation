#!/usr/bin/env python3
"""
CheckPoint Automation Tasks
Simplified functions for common CheckPoint firewall management operations.
"""

import logging
import traceback

from .command_executor import FirewallMode
from .config import FirewallConfig
from .expert_password import ExpertPasswordManager
from .ssh_connection import SSHConnectionManager
from .user_management import UserManager

logger = logging.getLogger(__name__)

# =============================================================================
# TASK FUNCTIONS
# =============================================================================


def task_set_expert_password(config: FirewallConfig) -> bool:
    """
    Task: Set up expert password on the firewall.

    Args:
        config: Firewall configuration including expert password

    Returns:
        True if task completed successfully, False otherwise
    """
    print("\n" + "=" * 60)
    print("🔐 Task 1: Expert Password Setup")
    print("=" * 60)

    try:
        # Use context manager pattern like fw_set_expert.py
        print(f" □ Connecting to firewall at {config.ip_address}...")
        with SSHConnectionManager(config) as ssh_manager:
            print("   ✓ Connected successfully")

            # Detect initial mode
            initial_mode = ssh_manager.get_current_mode()
            print(f"   ✓ Initial mode detected: {initial_mode.value}")

            # Test expert password setup workflow (exactly like fw_set_expert.py)
            print("\n □ Starting the workflow to setup expert password...")
            expert_mgr = ExpertPasswordManager(ssh_manager)

            setup_success, setup_msg = expert_mgr.setup_expert_password(config.expert_password)
            if setup_success:
                print(f"   ✓ Expert password setup: {setup_msg}")
            else:
                print(f"   ✗ Expert password setup failed: {setup_msg}")
                return False

            print("\n=== Task 1: Expert Password Setup Successful! ===")
            return True

    except Exception as e:
        print(f"\n✗ Task 1: Expert Password Setup failed with exception: {e}")
        traceback.print_exc()
        return False


def task_create_vagrant_user(config: FirewallConfig, username: str = "vagrant", password: str = "vagrant") -> bool:
    """
    Task: Configure vagrant user with SSH access on the firewall.
    Uses the same clean pattern as expert password setup.

    Args:
        config: Firewall configuration including expert password
        username: Username to create (default: vagrant)
        password: Password to set (default: vagrant)

    Returns:
        True if task completed successfully, False otherwise
    """
    print("\n" + "=" * 60)
    print("👤 Task 2: Vagrant User Setup")
    print("=" * 60)
    print(f"Creating user: {username}")
    print(f"Password: {'*' * len(password)}")

    # Vagrant insecure SSH public key
    vagrant_public_key = (
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw"
        "+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEFHzD8+v1I2YJ6oX"
        "evct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4"
        "O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhM"
        "mBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== "
        "vagrant insecure public key"
    )

    try:
        # Use context manager pattern like expert password task
        print(f"\n □ Connecting to firewall at {config.ip_address}...")
        with SSHConnectionManager(config) as ssh_manager:
            print("   ✓ Connected successfully")

            # Ensure we're in clish mode for user operations
            print("\n □ Checking current mode...")
            current_mode = ssh_manager.get_current_mode()
            if current_mode != FirewallMode.CLISH:
                print("   Switching to clish mode...")
                if not ssh_manager.exit_expert_mode():
                    print("   ✗ Failed to switch to clish mode")
                    return False
                print("   ✓ Switched to clish mode")
            else:
                print("   ✓ Already in clish mode")

            # Verify expert password is available
            print("\n □ Verifying expert password access...")
            expert_mgr = ExpertPasswordManager(ssh_manager)
            password_set, status_msg = expert_mgr.is_expert_password_set()
            print(f"   Expert password status: {status_msg}")

            if not password_set:
                print("   ✗ Expert password is not set!")
                print("   Please run Task 1 (Set Expert Password) first")
                return False

            # Check if user already exists (early exit if found)
            print(f"\n □ Checking if {username} user already exists...")
            # Use UserManager to check if user exists
            user_mgr = UserManager(ssh_manager)

            if user_mgr.user_exists(username):
                print(f"   ✓ User {username} already exists and is configured")
                print(f"\n=== Task 2: {username.title()} User Already Configured! ===")
                print(f"User {username} is already present on the firewall.")
                print(
                    f"You should be able to SSH using the password or the private key: {username}@{config.ip_address}"
                )
                return True

            print(f"   ✗ User {username} does not exist - proceeding with creation")

            # Step 3: Configure new user in clish mode
            print(f"\n □ Creating {username} user in clish mode...")

            clish_commands = [
                "set password-controls complexity 1",
                f"add user {username} uid 2000 homedir /home/{username}",
                f"add rba user {username} roles adminRole",
                f"set user {username} shell /bin/bash",
                "save config",
            ]

            for cmd in clish_commands:
                print(f"   Executing: {cmd}")
                result = ssh_manager.execute_command(cmd, timeout=config.timeout)
                if not result.success:
                    print(f"   ✗ Command failed: {cmd}")
                    print(f"     Error: {result.error_message}")
                    return False
                print("   ✓ Command successful")

            # Set user password using UserManager
            print(f"\n □ Setting {username} user password...")
            if not user_mgr.set_user_password(username, password):
                print(f"   ✗ Failed to set {username} user password")
                return False
            print(f"   ✓ Password set for {username} user")

            # Configure SSH keys in expert mode
            print("\n □ Setting up SSH keys in expert mode...")
            if not ssh_manager.enter_expert_mode(config.expert_password):
                print("   ✗ Failed to enter expert mode")
                return False
            print("   ✓ Entered expert mode successfully")

            # Create SSH directory and set up keys using working patterns
            print(f"   Creating SSH directory for {username}...")
            result = ssh_manager.execute_command(f"mkdir -p /home/{username}/.ssh", timeout=config.timeout)
            if not result.success:
                print(f"   ✗ Failed to create SSH directory: {result.error_message}")
                return False
            print("   ✓ SSH directory created")

            # Set up SSH key using UserManager
            print("   Installing SSH public key...")
            if not user_mgr.setup_ssh_key(username, vagrant_public_key):
                print("   ✗ Failed to setup SSH key")
                return False
            print("   ✓ SSH key installed")

            # Set permissions and ownership
            permission_commands = [
                f"chmod 700 /home/{username}/.ssh",
                f"chmod 600 /home/{username}/.ssh/authorized_keys",
                f"chown -R {username}:users /home/{username}/.ssh",
            ]

            for cmd in permission_commands:
                print(f"   Executing: {cmd}")
                result = ssh_manager.execute_command(cmd, timeout=config.timeout)
                if not result.success:
                    print(f"   ✗ Command failed: {cmd}")
                    print(f"     Error: {result.error_message}")
                    return False
                print("   ✓ Command successful")

            # Verify setup
            print(f"\n □ Verifying {username} user setup...")

            # Check user exists
            result = ssh_manager.execute_command(f"grep {username} /etc/passwd", timeout=config.timeout)
            if result.success:
                print(f"   ✓ User entry: {result.output.strip()}")
            else:
                print(f"   ✗ {username} user not found in /etc/passwd")
                return False

            # Check SSH directory
            result = ssh_manager.execute_command(f"ls -la /home/{username}/.ssh/", timeout=config.timeout)
            if result.success:
                print("   ✓ SSH directory contents verified")
            else:
                print("   ✗ SSH directory not accessible")
                return False

            print(f"\n=== Task 2: {username.title()} User Setup Successful! ===")
            print(f"You can now SSH using the password or the private key: {username}@{config.ip_address}")
            return True

    except Exception as e:
        print(f"\n✗ Task 2: Vagrant User Setup failed with exception: {e}")
        traceback.print_exc()
        return False


def task_copy_binary(config: FirewallConfig) -> bool:
    """
    Task: Copy binary files (placeholder for future implementation).

    Args:
        config: Firewall configuration

    Returns:
        False (not implemented yet)
    """
    print("⚠️  Task: Copy Binary Files - Not implemented yet")
    return False
