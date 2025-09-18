#!/usr/bin/env python3
"""
Test improved mode detection with proper expert mode handling.
"""

import sys
import os

# Add the checkpoint_automation module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from checkpoint_automation import FirewallConfig, SSHConnectionManager, FirewallMode

def test_improved_mode_detection():
    """Test mode detection with improved expert mode handling."""
    print("🔍 Testing Improved Mode Detection")
    print("=" * 40)
    
    config = FirewallConfig(
        ip_address="10.194.58.200",
        username="admin",
        password="admin",
        expert_password="admin15"
    )
    
    try:
        with SSHConnectionManager(config, console_log_level="INFO") as ssh:
            print("✅ Connected to firewall")
            
            # Test 1: Initial mode detection
            print("\n🔍 Test 1: Initial mode detection")
            initial_mode = ssh.detect_mode()
            print(f"   Initial mode: {initial_mode.value}")
            assert initial_mode == FirewallMode.CLISH, f"Expected CLISH, got {initial_mode.value}"
            
            # Test 2: Basic command in clish mode
            print("\n🔍 Test 2: Command execution in clish mode")
            hostname_response = ssh.execute_command("show hostname")
            print(f"   Hostname command success: {hostname_response.success}")
            print(f"   Mode from response: {hostname_response.mode.value}")
            assert hostname_response.mode == FirewallMode.CLISH, f"Expected CLISH, got {hostname_response.mode.value}"
            
            # Test 3: Enter expert mode
            print("\n🔍 Test 3: Enter expert mode")
            expert_success = ssh.enter_expert_mode(config.expert_password)
            print(f"   Expert mode entry: {'SUCCESS' if expert_success else 'FAILED'}")
            
            if expert_success:
                current_mode = ssh.get_current_mode()
                print(f"   Current mode: {current_mode.value}")
                assert current_mode == FirewallMode.EXPERT, f"Expected EXPERT, got {current_mode.value}"
                
                # Test 4: Command in expert mode
                print("\n🔍 Test 4: Command execution in expert mode")
                pwd_response = ssh.execute_command("pwd")
                print(f"   pwd command success: {pwd_response.success}")
                print(f"   pwd output: {pwd_response.output.strip()}")
                print(f"   Mode from response: {pwd_response.mode.value}")
                assert pwd_response.mode == FirewallMode.EXPERT, f"Expected EXPERT, got {pwd_response.mode.value}"
                
                # Test 5: Exit expert mode
                print("\n🔍 Test 5: Exit expert mode")
                exit_success = ssh.exit_expert_mode()
                print(f"   Expert mode exit: {'SUCCESS' if exit_success else 'FAILED'}")
                
                if exit_success:
                    final_mode = ssh.get_current_mode()
                    print(f"   Final mode: {final_mode.value}")
                    assert final_mode == FirewallMode.CLISH, f"Expected CLISH, got {final_mode.value}"
                    
                    # Test 6: Command after returning to clish
                    print("\n🔍 Test 6: Command execution after returning to clish")
                    final_response = ssh.execute_command("show hostname")
                    print(f"   Final command success: {final_response.success}")
                    print(f"   Final mode: {final_response.mode.value}")
                    assert final_response.mode == FirewallMode.CLISH, f"Expected CLISH, got {final_response.mode.value}"
                    
                    print("\n🎯 All mode detection tests PASSED!")
                    print("   ✓ Initial clish mode detection")
                    print("   ✓ Command execution in clish mode")
                    print("   ✓ Expert mode entry with password")
                    print("   ✓ Command execution in expert mode")
                    print("   ✓ Expert mode exit")
                    print("   ✓ Return to clish mode")
                    print("   ✓ Mode tracking throughout session")
                    
                    return True
                else:
                    print("❌ Failed to exit expert mode")
                    return False
            else:
                print("❌ Failed to enter expert mode")
                return False
                
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the improved mode detection test."""
    try:
        success = test_improved_mode_detection()
        
        if success:
            print("\n" + "=" * 50)
            print("🎉 Mode Detection Test PASSED!")
            print("Task 3: Mode detection functionality fully verified!")
            return 0
        else:
            print("\n❌ Mode detection test FAILED")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        return 1

if __name__ == "__main__":
    sys.exit(main())