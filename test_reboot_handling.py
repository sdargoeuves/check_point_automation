#!/usr/bin/env python3
"""Test script deployment with reboot handling - specifically for config_system scenarios."""

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

import time

from checkpoint_automation import (
    FirewallConfig,
    ScriptDeploymentManager,
    SSHConnectionManager,
)

# UPDATE THESE VALUES FOR YOUR FIREWALL
FIREWALL_IP = "YOUR_FIREWALL_IP"
USERNAME = "admin"
PASSWORD = "admin"
EXPERT_PASSWORD = "YOUR_EXPERT_PASSWORD"

# Test script that simulates what happens with config_system
TEST_SCRIPT_WITH_REBOOT = """#!/bin/bash
echo "=== Starting Configuration Script ==="
echo "This script will demonstrate reboot handling"
echo "Current time: $(date)"
echo "Current user: $(whoami)"

# Simulate some configuration work
echo "Performing configuration tasks..."
sleep 2

# This is what your actual script might do - uncomment to test real reboot
# echo "Running config_system command (this will cause reboot)..."
# config_system -f first_wizard.conf

# For testing without actual reboot, simulate the output
echo "dos2unix: converting file first_wizard.conf to Unix format ..."
echo "Validating configuration file:	Done"
echo "Configuring OS parameters:	Done"
echo "Configuring products:		\\"

# Simulate connection loss (comment this out if testing real reboot)
echo "Simulating connection loss..."
echo "Connection to firewall will be lost here in real scenario"
"""


def test_with_reboot_simulation():
    """Test script deployment with simulated reboot scenario."""

    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD,
    )

    print("Testing Script Deployment with Reboot Handling")
    print("=" * 60)
    print(f"Target firewall: {FIREWALL_IP}")
    print()

    try:
        print("Step 1: Connecting to firewall...")
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            print("✓ Connected successfully")

            print("\nStep 2: Deploying and executing script...")
            script_manager = ScriptDeploymentManager(ssh_manager)

            # Execute script and capture results
            success, output = script_manager.deploy_and_execute_script(TEST_SCRIPT_WITH_REBOOT)

            print(f"\nStep 3: Script execution result: {'SUCCESS' if success else 'FAILED'}")
            print("\nScript Output:")
            print("-" * 60)
            print(output)
            print("-" * 60)

            # Check if reboot was detected
            if "reboot" in output.lower() or "connection lost" in output.lower():
                print("\n🔄 Reboot scenario detected!")
                print("In a real scenario, you would now:")
                print("1. Wait for the firewall to reboot")
                print("2. Attempt to reconnect")
                print("3. Verify the configuration was applied")

                # Demonstrate reboot handling (optional)
                user_input = input("\nWould you like to test reconnection? (y/n): ")
                if user_input.lower() == "y":
                    print("\nStep 4: Testing reconnection after reboot...")

                    # Disconnect current connection
                    ssh_manager.disconnect()

                    # Wait a bit and try to reconnect
                    print("Waiting 10 seconds before reconnection attempt...")
                    time.sleep(10)

                    if ssh_manager.connect():
                        print("✓ Reconnection successful!")

                        # Test a simple command to verify firewall is responsive
                        response = ssh_manager.execute_command("show version")
                        if response.success:
                            print("✓ Firewall is responsive after reconnection")
                        else:
                            print("⚠️  Firewall connected but not fully responsive yet")
                    else:
                        print("✗ Reconnection failed - firewall may still be rebooting")

            return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_actual_config_system():
    """Test with actual config_system command (USE WITH CAUTION!)."""

    print("\n" + "=" * 60)
    print("WARNING: ACTUAL REBOOT TEST")
    print("=" * 60)
    print("This will run 'config_system -f first_wizard.conf' which WILL reboot your firewall!")
    print("Make sure you have:")
    print("1. A first_wizard.conf file on the firewall")
    print("2. Permission to reboot the firewall")
    print("3. Time to wait for reboot completion")

    confirm = input("\nAre you sure you want to proceed? Type 'YES' to continue: ")
    if confirm != "YES":
        print("Test cancelled.")
        return False

    # Script that actually runs config_system
    actual_config_script = """#!/bin/bash
echo "=== Running Actual Configuration ==="
echo "Current time: $(date)"
echo "About to run config_system..."

# Check if first_wizard.conf exists
if [ -f "first_wizard.conf" ]; then
    echo "Found first_wizard.conf, proceeding with configuration..."
    config_system -f first_wizard.conf
else
    echo "ERROR: first_wizard.conf not found!"
    echo "Please create this file first or copy it to the current directory"
    exit 1
fi
"""

    config = FirewallConfig(
        ip_address=FIREWALL_IP,
        username=USERNAME,
        password=PASSWORD,
        expert_password=EXPERT_PASSWORD,
    )

    try:
        print("\nConnecting to firewall...")
        ssh_manager = SSHConnectionManager(config, console_log_level="INFO")

        if not ssh_manager.connect():
            print("Failed to connect")
            return False

        print("✓ Connected")

        script_manager = ScriptDeploymentManager(ssh_manager)

        print("Executing config_system script...")
        success, output = script_manager.deploy_and_execute_script(actual_config_script)

        print(f"\nExecution result: {'SUCCESS' if success else 'FAILED'}")
        print("\nOutput:")
        print("-" * 60)
        print(output)
        print("-" * 60)

        if success and ("connection lost" in output.lower() or "reboot" in output.lower()):
            print("\n🔄 Firewall is rebooting...")
            print("Attempting to handle reboot scenario...")

            reboot_success, reboot_message = script_manager.handle_reboot_scenario(max_wait_time=600)

            if reboot_success:
                print("✓ Successfully reconnected after reboot!")
                print(f"Status: {reboot_message}")
            else:
                print(f"⚠️  Reboot handling issue: {reboot_message}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main test function."""

    print("Script Deployment Reboot Handling Test")
    print("=" * 50)

    # Test 1: Simulated reboot
    print("Test 1: Simulated reboot scenario")
    test_with_reboot_simulation()

    # Test 2: Actual reboot (optional)
    print("\n" + "=" * 50)
    print("Test 2: Actual config_system reboot (OPTIONAL)")
    user_choice = input("Would you like to test actual reboot with config_system? (y/n): ")

    if user_choice.lower() == "y":
        test_actual_config_system()
    else:
        print("Skipping actual reboot test.")

    print("\n✅ Testing completed!")


if __name__ == "__main__":
    main()
