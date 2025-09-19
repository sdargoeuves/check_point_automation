#!/usr/bin/env python3
"""
Script to setup the expert password on a real Check Point firewall.
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

def test_expert_mode_functionality(ip_address: str, username: str = "admin", password: str = "admin", expert_password: str = "admin15"):
    """Test expert mode functionality on a real firewall.
    
    Args:
        ip_address: IP address of the firewall
        username: SSH username (default: admin)
        password: SSH password (default: admin)
        expert_password: Expert password to set/use (default: admin15)
    """
    print(f"\n=== Testing Expert Mode Functionality on {ip_address} ===")
    
    # Create configuration
    config = FirewallConfig(
        ip_address=ip_address,
        username=username,
        password=password,
        expert_password=expert_password
    )
    
    try:
        # Connect to firewall
        print(f"1. Connecting to firewall at {ip_address}...")
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            print("   ✓ Connected successfully")
            
            # Detect initial mode
            initial_mode = ssh_manager.detect_mode()
            print(f"   ✓ Initial mode detected: {initial_mode.value}")
            
            # Test expert password setup workflow
            print("\n2. Testing expert password setup workflow...")
            expert_mgr = ExpertPasswordManager(ssh_manager)
            
            # Check current expert password status
            password_set, status_msg = expert_mgr.check_expert_password_status()
            print(f"   Expert password status: {status_msg}")
            
            if not password_set:
                print("   Setting expert password...")
                setup_success, setup_msg = expert_mgr.setup_expert_password_workflow(expert_password)
                if setup_success:
                    print(f"   ✓ Expert password setup: {setup_msg}")
                else:
                    print(f"   ✗ Expert password setup failed: {setup_msg}")
                    return False
            else:
                print("   ✓ Expert password already set")
            
            # Test expert mode entry
            print("\n3. Testing expert mode entry...")
            current_mode = ssh_manager.get_current_mode()
            print(f"   Current mode before entry: {current_mode.value}")
            
            entry_success = ssh_manager.enter_expert_mode(expert_password)
            if entry_success:
                print("   ✓ Successfully entered expert mode")
                
                # Verify we're in expert mode
                current_mode = ssh_manager.get_current_mode()
                print(f"   Current mode after entry: {current_mode.value}")
                
                if current_mode.value == "expert":
                    print("   ✓ Mode verification successful")
                else:
                    print(f"   ✗ Mode verification failed - expected expert, got {current_mode.value}")
                    return False
            else:
                print("   ✗ Failed to enter expert mode")
                return False
            
            # Test expert mode exit
            print("\n4. Testing expert mode exit...")
            exit_success = ssh_manager.exit_expert_mode()
            if exit_success:
                print("   ✓ Successfully exited expert mode")
                
                # Verify we're back in clish mode
                current_mode = ssh_manager.get_current_mode()
                print(f"   Current mode after exit: {current_mode.value}")
                
                if current_mode.value == "clish":
                    print("   ✓ Mode verification successful")
                else:
                    print(f"   ✗ Mode verification failed - expected clish, got {current_mode.value}")
                    return False
            else:
                print("   ✗ Failed to exit expert mode")
                return False
             
            print("\n=== Setup Successful! ===")
            return True
            
    except Exception as e:
        print(f"\n✗ Setup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the test."""
    setup_logging()
    
    if len(sys.argv) < 2:
        print("Usage: python test_expert_mode_real.py <firewall_ip> [username] [password] [expert_password]")
        print("Example: python test_expert_mode_real.py 10.194.59.200")
        print("Example: python test_expert_mode_real.py 10.194.59.200 admin admin admin15")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"
    password = sys.argv[3] if len(sys.argv) > 3 else "admin"
    expert_password = sys.argv[4] if len(sys.argv) > 4 else "admin15"
    
    print(f"Testing firewall: {ip_address}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print(f"Expert password: {'*' * len(expert_password)}")
    
    success = test_expert_mode_functionality(ip_address, username, password, expert_password)
    
    if success:
        print("\n🎉 Setup EXPERT mode completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some steps failed during the setup. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()