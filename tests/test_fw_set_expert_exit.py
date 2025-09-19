#!/usr/bin/env python3
"""
Test script for expert mode entry/exit and password setup on a real Check Point firewall.
"""

import logging
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from checkpoint_automation.config import FirewallConfig
from checkpoint_automation.ssh_connection import SSHConnectionManager
from checkpoint_automation.expert_password import ExpertPasswordManager

def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_expert_mode_functionality(ip_address: str, username: str = "admin", password: str = "admin", expert_password: str = "CheckPoint123!"):
    """Test expert mode functionality on a real firewall.
    
    Args:
        ip_address: IP address of the firewall
        username: SSH username (default: admin)
        password: SSH password (default: admin)
        expert_password: Expert password to set/use
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
            
            # Test multiple transitions
            print("\n5. Testing multiple mode transitions...")
            for i in range(3):
                print(f"   Transition {i+1}/3:")
                
                # Enter expert mode
                if not ssh_manager.enter_expert_mode(expert_password):
                    print(f"   ✗ Failed to enter expert mode on attempt {i+1}")
                    return False
                print(f"     ✓ Entered expert mode")
                
                # Exit expert mode
                if not ssh_manager.exit_expert_mode():
                    print(f"   ✗ Failed to exit expert mode on attempt {i+1}")
                    return False
                print(f"     ✓ Exited to clish mode")
            
            print("\n6. Testing edge cases...")
            
            # Test entering expert mode when already in expert mode
            ssh_manager.enter_expert_mode(expert_password)
            print("   Testing entry when already in expert mode...")
            entry_result = ssh_manager.enter_expert_mode(expert_password)
            if entry_result:
                print("   ✓ Handled already-in-expert-mode case correctly")
            else:
                print("   ✗ Failed to handle already-in-expert-mode case")
                return False
            
            # Test exiting clish mode when already in clish mode
            ssh_manager.exit_expert_mode()
            print("   Testing exit when already in clish mode...")
            exit_result = ssh_manager.exit_expert_mode()
            if exit_result:
                print("   ✓ Handled already-in-clish-mode case correctly")
            else:
                print("   ✗ Failed to handle already-in-clish-mode case")
                return False
            
            print("\n=== All Tests Passed Successfully! ===")
            return True
            
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the test."""
    setup_logging()
    
    if len(sys.argv) < 2:
        print("Usage: python test_expert_mode_real.py <firewall_ip> [username] [password] [expert_password]")
        print("Example: python test_expert_mode_real.py 10.194.59.200")
        print("Example: python test_expert_mode_real.py 10.194.59.200 admin admin CheckPoint123!")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"
    password = sys.argv[3] if len(sys.argv) > 3 else "admin"
    expert_password = sys.argv[4] if len(sys.argv) > 4 else "CheckPoint123!"
    
    print(f"Testing firewall: {ip_address}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print(f"Expert password: {'*' * len(expert_password)}")
    
    success = test_expert_mode_functionality(ip_address, username, password, expert_password)
    
    if success:
        print("\n🎉 All expert mode functionality tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()