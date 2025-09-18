#!/usr/bin/env python3
"""
Test script for expert password setup workflow.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checkpoint_automation import FirewallConfig, SSHConnectionManager, ExpertPasswordManager


def test_expert_password_workflow():
    """Test the expert password setup workflow."""
    
    # Configuration - replace with your test firewall details
    config = FirewallConfig(
        ip_address="10.194.59.200",  # Replace with your test firewall IP
        username="admin",
        password="admin",
        expert_password="admin15"  # Test expert password
    )
    
    print(f"Testing expert password workflow on {config.ip_address}")
    
    try:
        # Create SSH connection
        with SSHConnectionManager(config, console_log_level="DEBUG") as ssh_manager:
            print("✓ SSH connection established")
            
            # Create expert password manager
            expert_mgr = ExpertPasswordManager(ssh_manager)
            
            # Test expert password workflow
            print("\n--- Testing Expert Password Setup Workflow ---")
            
            success, message = expert_mgr.setup_expert_password_workflow(config.expert_password)
            
            if success:
                print(f"✓ Expert password workflow completed: {message}")
                
                # Additional verification - try to enter expert mode
                print("\n--- Additional Verification ---")
                if ssh_manager.enter_expert_mode(config.expert_password):
                    print("✓ Successfully entered expert mode with new password")
                    
                    if ssh_manager.exit_expert_mode():
                        print("✓ Successfully exited expert mode")
                    else:
                        print("⚠ Warning: Failed to exit expert mode")
                else:
                    print("✗ Failed to enter expert mode with new password")
                    
            else:
                print(f"✗ Expert password workflow failed: {message}")
                return False
                
        print("\n✓ All tests completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        return False


if __name__ == "__main__":
    print("Expert Password Setup Test")
    print("=" * 50)
    
    success = test_expert_password_workflow()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)