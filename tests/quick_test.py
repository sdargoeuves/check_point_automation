#!/usr/bin/env python3
"""
Quick interactive test for command execution.
"""

from checkpoint_automation import FirewallConfig, SSHConnectionManager

# Replace with your firewall's IP address
FIREWALL_IP = "10.194.59.200"  # Your firewall IP

def quick_test():
    config = FirewallConfig(ip_address=FIREWALL_IP)
    
    with SSHConnectionManager(config, console_log_level="INFO") as ssh:
        print(f"Connected to {FIREWALL_IP}")
        print(f"Current mode: {ssh.get_current_mode().value}")
        
        # Test a few commands
        commands = ["whoami", "show version all", "expert"]
        
        for cmd in commands:
            print(f"\n--- Executing: {cmd} ---")
            response = ssh.execute_command(cmd, timeout=5)
            print(f"Success: {response.success}")
            print(f"Output: {response.output[:200]}...")  # First 200 chars

if __name__ == "__main__":
    quick_test()