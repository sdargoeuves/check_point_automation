#!/usr/bin/env python3
"""
Quick test for script deployment - easily customizable.
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

# UPDATE THESE VALUES FOR YOUR FIREWALL
FIREWALL_IP = "YOUR_FIREWALL_IP"
USERNAME = "admin"
PASSWORD = "admin"
EXPERT_PASSWORD = "YOUR_EXPERT_PASSWORD"

# Simple test script
TEST_SCRIPT = """#!/bin/bash
echo "=== Script Deployment Test ==="
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Date and time: $(date)"
echo "Firewall hostname: $(hostname)"
echo "Available disk space:"
df -h /home
echo "=== Test Complete ==="
"""

def main():
    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD
    )
    
    print(f"Testing script deployment on {FIREWALL_IP}")
    
    try:
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            print("✓ Connected to firewall")
            
            script_manager = ScriptDeploymentManager(ssh_manager)
            success, output = script_manager.deploy_and_execute_script(TEST_SCRIPT)
            
            if success:
                print("✓ SUCCESS! Script deployed and executed")
                print("\nOutput:")
                print("-" * 50)
                print(output)
                print("-" * 50)
            else:
                print(f"✗ FAILED: {output}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()