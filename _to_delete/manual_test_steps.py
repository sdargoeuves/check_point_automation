#!/usr/bin/env python3
"""
Manual step-by-step testing of script deployment.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from checkpoint_automation import (
    FirewallConfig, 
    SSHConnectionManager, 
    ExpertPasswordManager,
    ScriptDeploymentManager
)

# UPDATE THESE VALUES
FIREWALL_IP = "YOUR_FIREWALL_IP"
USERNAME = "admin" 
PASSWORD = "admin"
EXPERT_PASSWORD = "YOUR_EXPERT_PASSWORD"

def test_connection():
    """Test basic SSH connection."""
    print("Step 1: Testing SSH connection...")
    
    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD
    )
    
    ssh_manager = SSHConnectionManager(config, console_log_level="DEBUG")
    
    if ssh_manager.connect():
        print("✓ SSH connection successful")
        
        # Test basic command
        response = ssh_manager.execute_command("show version")
        if response.success:
            print("✓ Basic command execution works")
            print(f"Firewall version info: {response.output[:100]}...")
        else:
            print(f"✗ Command execution failed: {response.error_message}")
        
        ssh_manager.disconnect()
        return True
    else:
        print("✗ SSH connection failed")
        return False

def test_expert_mode():
    """Test expert mode entry."""
    print("\nStep 2: Testing expert mode...")
    
    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD
    )
    
    with SSHConnectionManager(config) as ssh_manager:
        # Setup expert password if needed
        expert_manager = ExpertPasswordManager(ssh_manager)
        success, message = expert_manager.setup_expert_password_workflow(EXPERT_PASSWORD)
        
        if success:
            print("✓ Expert password setup successful")
            
            # Test entering expert mode
            if ssh_manager.enter_expert_mode(EXPERT_PASSWORD):
                print("✓ Successfully entered expert mode")
                
                # Test a simple command in expert mode
                response = ssh_manager.execute_command("pwd")
                if response.success:
                    print(f"✓ Expert mode command works: {response.output}")
                
                # Exit expert mode
                if ssh_manager.exit_expert_mode():
                    print("✓ Successfully exited expert mode")
                    return True
                else:
                    print("✗ Failed to exit expert mode")
            else:
                print("✗ Failed to enter expert mode")
        else:
            print(f"✗ Expert password setup failed: {message}")
    
    return False

def test_script_deployment():
    """Test actual script deployment."""
    print("\nStep 3: Testing script deployment...")
    
    simple_script = """#!/bin/bash
echo "Hello from deployed script!"
echo "Current time: $(date)"
echo "Script location: $0"
"""
    
    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD
    )
    
    with SSHConnectionManager(config) as ssh_manager:
        script_manager = ScriptDeploymentManager(ssh_manager)
        
        success, output = script_manager.deploy_and_execute_script(simple_script)
        
        if success:
            print("✓ Script deployment and execution successful!")
            print("Script output:")
            print(output)
            return True
        else:
            print(f"✗ Script deployment failed: {output}")
            return False

def main():
    """Run all tests step by step."""
    print("Manual Testing of Script Deployment")
    print("=" * 50)
    print(f"Target firewall: {FIREWALL_IP}")
    print()
    
    # Test each step
    if not test_connection():
        print("❌ Connection test failed - check IP, username, password")
        return
    
    if not test_expert_mode():
        print("❌ Expert mode test failed - check expert password")
        return
    
    if not test_script_deployment():
        print("❌ Script deployment test failed")
        return
    
    print("\n🎉 All tests passed! Script deployment is working correctly.")

if __name__ == "__main__":
    main()