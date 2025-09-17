#!/usr/bin/env python3
"""
Quick test script to connect to Check Point firewall and explore its state.
"""

import paramiko
import time
import sys
from checkpoint_automation.core.models import ConnectionInfo
from checkpoint_automation.core.logging_config import get_logger

logger = get_logger("test_connection")

def test_checkpoint_connection(host: str, username: str = "admin", password: str = "admin"):
    """Test connection to Check Point firewall and explore its state."""
    
    print(f"Testing connection to Check Point firewall at {host}")
    print("=" * 60)
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect
        print(f"Connecting to {host}...")
        ssh.connect(
            hostname=host,
            port=22,
            username=username,
            password=password,
            timeout=30,
            look_for_keys=False,
            allow_agent=False
        )
        print("✅ SSH connection successful!")
        
        # Create interactive shell
        shell = ssh.invoke_shell()
        time.sleep(2)  # Wait for shell to initialize
        
        # Read initial output
        initial_output = ""
        if shell.recv_ready():
            initial_output = shell.recv(4096).decode('utf-8', errors='ignore')
            print("\n📋 Initial shell output:")
            print("-" * 40)
            print(initial_output)
            print("-" * 40)
        
        # Test basic commands to understand the system state
        commands_to_test = [
            "show version all",
            "show hostname",
            "show interfaces",
            "show configuration"
        ]
        
        for cmd in commands_to_test:
            print(f"\n🔍 Testing command: {cmd}")
            shell.send(f"{cmd}\n")
            time.sleep(3)  # Wait for command to execute
            
            output = ""
            while shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                time.sleep(0.1)
            
            print(f"Output length: {len(output)} characters")
            if output:
                # Show first few lines of output
                lines = output.split('\n')[:10]
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
                if len(output.split('\n')) > 10:
                    print(f"  ... ({len(output.split('\n')) - 10} more lines)")
            else:
                print("  No output received")
        
        # Try to detect CLI mode
        print(f"\n🔍 Detecting CLI mode...")
        shell.send("help\n")
        time.sleep(2)
        
        help_output = ""
        while shell.recv_ready():
            chunk = shell.recv(4096).decode('utf-8', errors='ignore')
            help_output += chunk
            time.sleep(0.1)
        
        if "clish" in help_output.lower():
            print("  Detected: CLISH mode")
        elif "expert" in help_output.lower() or "bash" in help_output.lower():
            print("  Detected: Expert mode")
        else:
            print("  CLI mode unclear")
            print(f"  Help output sample: {help_output[:200]}...")
        
        # Try to get system status
        print(f"\n🔍 Getting system status...")
        shell.send("show asset all\n")
        time.sleep(2)
        
        status_output = ""
        while shell.recv_ready():
            chunk = shell.recv(4096).decode('utf-8', errors='ignore')
            status_output += chunk
            time.sleep(0.1)
        
        if status_output:
            print("  System status retrieved")
            lines = status_output.split('\n')[:5]
            for line in lines:
                if line.strip():
                    print(f"  {line}")
        
        shell.close()
        
    except paramiko.AuthenticationException:
        print("❌ Authentication failed - check credentials")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        ssh.close()
    
    print("\n✅ Connection test completed!")
    return True

if __name__ == "__main__":
    # Test with the provided IP
    host = "10.194.58.200"
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    
    print("Check Point Firewall Connection Test")
    print("====================================")
    
    success = test_checkpoint_connection(host)
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("Next steps: Implement proper connection manager based on findings")
    else:
        print("\n💡 Check network connectivity and credentials")