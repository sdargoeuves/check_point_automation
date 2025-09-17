#!/usr/bin/env python3
"""
Test script for CheckPointConnectionManager implementation.
"""

import sys
from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo
from checkpoint_automation.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_level="INFO", console_output=True)
logger = get_logger("test_connection_manager")

def test_connection_manager(host: str):
    """Test the CheckPointConnectionManager with a real firewall."""
    
    print("Check Point Connection Manager Test")
    print("=" * 50)
    
    # Create connection info
    conn_info = ConnectionInfo(
        host=host,
        username="admin",
        password="admin",
        timeout=30
    )
    
    # Create connection manager
    manager = CheckPointConnectionManager()
    
    try:
        # Test connection
        print(f"🔌 Connecting to {host}...")
        success = manager.connect(conn_info)
        
        if not success:
            print("❌ Connection failed")
            return False
        
        print("✅ Connection successful!")
        
        # Test connection status
        print(f"📊 Connection status: {manager.is_connected()}")
        
        # Test CLI mode detection
        print(f"🖥️  CLI Mode: {manager.get_cli_mode().value}")
        
        # Test state detection
        print(f"🔍 System State: {manager.detect_state().value}")
        
        # Test system status
        print("\n📋 Getting comprehensive system status...")
        try:
            status = manager.get_system_status()
            print(f"  Version: {status.version}")
            print(f"  Hostname: {status.hostname}")
            print(f"  CLI Mode: {status.cli_mode.value}")
            print(f"  State: {status.state.value}")
            print(f"  Interfaces Configured: {status.interfaces_configured}")
            print(f"  Policy Installed: {status.policy_installed}")
            print(f"  Expert Password Set: {status.expert_password_set}")
            print(f"  Wizard Completed: {status.wizard_completed}")
        except Exception as e:
            print(f"  ⚠️  Error getting system status: {e}")
        
        # Test command execution
        print("\n🔧 Testing command execution...")
        
        test_commands = [
            "show version all",
            "show hostname",
            "show interfaces"
        ]
        
        for cmd in test_commands:
            print(f"\n  Executing: {cmd}")
            result = manager.execute_command(cmd)
            print(f"    Success: {result.success}")
            print(f"    Execution time: {result.execution_time:.2f}s")
            if result.success:
                # Show first few lines of output
                lines = result.output.strip().split('\n')[:3]
                for line in lines:
                    if line.strip():
                        print(f"    Output: {line.strip()}")
                if len(result.output.strip().split('\n')) > 3:
                    print(f"    ... (truncated)")
            else:
                print(f"    Error: {result.error}")
        
        # Test CLI mode switching (if expert password is available)
        print("\n🔄 Testing CLI mode switching...")
        current_mode = manager.get_cli_mode()
        print(f"  Current mode: {current_mode.value}")
        
        if current_mode.value == "clish":
            print("  Attempting to switch to expert mode...")
            # Note: This will likely fail without the correct expert password
            # but it tests the switching logic
            success = manager.switch_to_expert("admin")  # Default password attempt
            print(f"  Switch to expert: {success}")
            
            if success:
                print(f"  New mode: {manager.get_cli_mode().value}")
                
                # Switch back to clish
                print("  Switching back to clish...")
                success = manager.switch_to_clish()
                print(f"  Switch to clish: {success}")
                print(f"  Final mode: {manager.get_cli_mode().value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        # Always disconnect
        print("\n🔌 Disconnecting...")
        manager.disconnect()
        print(f"📊 Connection status after disconnect: {manager.is_connected()}")

if __name__ == "__main__":
    host = "10.194.58.200"
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    
    success = test_connection_manager(host)
    
    if success:
        print("\n🎉 Connection manager test completed successfully!")
        print("✅ CheckPointConnectionManager is working correctly")
    else:
        print("\n❌ Connection manager test failed")
        print("💡 Check the implementation and try again")