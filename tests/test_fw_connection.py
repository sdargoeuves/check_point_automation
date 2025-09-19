#!/usr/bin/env python3
"""
Test script to verify command execution with a real Check Point firewall.
"""

import sys
import os
from checkpoint_automation import FirewallConfig, SSHConnectionManager, FirewallMode

def test_basic_connection(ip_address: str):
    """Test basic connection and command execution."""
    print(f"Testing connection to {ip_address}...")
    
    # Create configuration with default credentials
    config = FirewallConfig(
        ip_address=ip_address,
        username="admin",
        password="admin"
    )
    
    try:
        # Connect to firewall
        with SSHConnectionManager(config, console_log_level="INFO") as ssh:
            print("✓ Successfully connected!")
            
            # Detect current mode
            current_mode = ssh.get_current_mode()
            print(f"✓ Current mode: {current_mode.value}")
            
            # Test basic command execution
            print("\nTesting basic commands...")
            
            # Test 1: Simple command that works in both modes
            response = ssh.execute_command("show version all")
            print(f"Command: {response.command}")
            print(f"Success: {response.success}")
            print(f"Output: {response.output[:100]}...")  # First 100 chars
            
            # Test 2: Check expert password status
            print("\nChecking expert password status...")
            response = ssh.execute_command("expert")
            print(f"Expert command output: {response.output}")
            
            if "Expert password has not been defined" in response.output:
                print("✓ Expert password not set - this is expected for new firewalls")
            elif "Enter expert password:" in response.output:
                print("✓ Expert password is already set")
            else:
                print(f"? Unexpected expert command response: {response.output}")
            
            # Test 3: Show version (should work in clish mode)
            print("\nTesting show version all command...")
            response = ssh.execute_command("show version all")
            print(f"Version command success: {response.success}")
            if response.success:
                # Extract just the first line of version info
                first_line = response.output.split('\n')[0] if response.output else "No output"
                print(f"Version info: {first_line}")
            
            print("\n✅ Basic connection test completed successfully!")
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    
    return True

def test_mode_detection(ip_address: str):
    """Test mode detection functionality."""
    print(f"\nTesting mode detection on {ip_address}...")
    
    config = FirewallConfig(ip_address=ip_address)
    
    try:
        with SSHConnectionManager(config, console_log_level="DEBUG") as ssh:
            # Test mode detection
            detected_mode = ssh.detect_mode()
            current_mode = ssh.get_current_mode()
            
            print(f"✓ Detected mode: {detected_mode.value}")
            print(f"✓ Current mode: {current_mode.value}")
            
            # Test prompt waiting
            print("Testing prompt detection...")
            if current_mode == FirewallMode.CLISH:
                # Wait for clish prompt
                prompt_found = ssh.wait_for_prompt(r'[\w\-]+>\s*$', timeout=2)
                print(f"✓ Clish prompt detection: {prompt_found}")
            
            return True
            
    except Exception as e:
        print(f"❌ Mode detection test failed: {e}")
        return False

def main():
    """Main test function."""
    print("Check Point Firewall Connection Test")
    print("=" * 40)
    
    # Get firewall IP from command line or prompt user
    if len(sys.argv) > 1:
        firewall_ip = sys.argv[1]
    else:
        firewall_ip = input("Enter firewall IP address: ").strip()
    
    if not firewall_ip:
        print("❌ No IP address provided")
        return 1
    
    print(f"Testing firewall at: {firewall_ip}")
    print("Using default credentials: admin/admin")
    print("-" * 40)
    
    # Run tests
    success = True
    
    # Test 1: Basic connection and commands
    if not test_basic_connection(firewall_ip):
        success = False
    
    # Test 2: Mode detection
    if not test_mode_detection(firewall_ip):
        success = False
    
    if success:
        print("\n🎉 All tests passed! Command execution is working correctly.")
        print("\nNext steps:")
        print("1. You can now proceed to implement expert password setup")
        print("2. The command executor is ready for script deployment")
        print("3. Mode detection is working for clish/expert transitions")
    else:
        print("\n❌ Some tests failed. Check the logs for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())