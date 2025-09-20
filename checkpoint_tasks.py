#!/usr/bin/env python3
"""
CheckPoint Automation Tasks
Simplified functions for common CheckPoint firewall management operations.
"""

import logging
from typing import Tuple, Optional

from checkpoint_automation.config import FirewallConfig
from checkpoint_automation.ssh_connection import SSHConnectionManager
from checkpoint_automation.expert_password import ExpertPasswordManager
from checkpoint_automation.command_executor import FirewallMode

logger = logging.getLogger(__name__)

# =============================================================================
# CORE CONNECTION FUNCTIONS
# =============================================================================

def connect(config: FirewallConfig) -> SSHConnectionManager:
    """
    Connect to firewall and return connection manager.
    Uses context manager pattern like the working fw_set_expert.py
    
    Args:
        config: Firewall configuration
        
    Returns:
        Connected SSH manager - use with 'with' statement
        
    Raises:
        ConnectionError: If connection fails
    """
    print(f"🔗 Connecting to {config.ip_address}...")
    
    try:
        ssh_manager = SSHConnectionManager(config, console_log_level="INFO")
        return ssh_manager
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        logger.exception("Connection failed")
        raise ConnectionError(f"Failed to connect to {config.ip_address}: {e}")

# =============================================================================
# UTILITY FUNCTIONS (for future use)
# =============================================================================

def send_command(ssh_manager: SSHConnectionManager, command: str, timeout: int = 30) -> bool:
    """
    Send a command and return success status.
    
    Args:
        ssh_manager: Connected SSH manager
        command: Command to execute
        timeout: Command timeout in seconds
        
    Returns:
        True if command succeeded, False otherwise
    """
    try:
        result = ssh_manager.execute_command(command, timeout=timeout)
        return result.success
    except Exception as e:
        logger.error(f"Command '{command}' failed: {e}")
        return False

# =============================================================================
# TASK FUNCTIONS
# =============================================================================

def task_set_expert_password(config: FirewallConfig) -> bool:
    """
    Task: Set up expert password on the firewall.
    
    Args:
        config: Firewall configuration including expert password
        
    Returns:
        True if task completed successfully, False otherwise
    """
    print("\n" + "="*60)
    print("🔐 Task 1: Expert Password Setup")
    print("="*60)
    
    try:
        # Use context manager pattern like fw_set_expert.py
        print(f"1. Connecting to firewall at {config.ip_address}...")
        with SSHConnectionManager(config, console_log_level="INFO") as ssh_manager:
            print("   ✓ Connected successfully")
            
            # Detect initial mode
            initial_mode = ssh_manager.detect_mode()
            print(f"   ✓ Initial mode detected: {initial_mode.value}")
            
            # Test expert password setup workflow (exactly like fw_set_expert.py)
            print("\n2. Testing expert password setup workflow...")
            expert_mgr = ExpertPasswordManager(ssh_manager)
            
            # Check current expert password status
            password_set, status_msg = expert_mgr.is_expert_password_set()
            print(f"   Expert password status: {status_msg}")
            
            if not password_set:
                print("   Setting expert password...")
                setup_success, setup_msg = expert_mgr.setup_expert_password(config.expert_password)
                if setup_success:
                    print(f"   ✓ Expert password setup: {setup_msg}")
                else:
                    print(f"   ✗ Expert password setup failed: {setup_msg}")
                    return False
            else:
                print("   ✓ Expert password already set")
            
                # Test expert mode entry
                print("\n3. Testing expert password...")
                current_mode = ssh_manager.get_current_mode()
                print(f"   Current mode before entry: {current_mode.value}")
                
                entry_success = ssh_manager.enter_expert_mode(config.expert_password)
                if entry_success:
                    print("   ✓ Successfully entered expert mode")
                    
                    # Verify we're in expert mode
                    current_mode = ssh_manager.get_current_mode()
                    print(f"   Current mode after entry: {current_mode.value}")
                    
                    if current_mode.value == "expert":
                        print("   ✓ Mode verification successful")
                        print("\n=== Task: Expert Password already setup! ===")
                        return True
                    else:
                        print(f"   ✗ Mode verification failed - expected expert, got {current_mode.value}")
                        return False
                else:
                    print("   ✗ Failed to enter expert mode")
                    return False
            
            # # Test expert mode exit
            # print("\n4. Testing expert mode exit...")
            # exit_success = ssh_manager.exit_expert_mode()
            # if exit_success:
            #     print("   ✓ Successfully exited expert mode")
                
            #     # Verify we're back in clish mode
            #     current_mode = ssh_manager.get_current_mode()
            #     print(f"   Current mode after exit: {current_mode.value}")
                
            #     if current_mode.value == "clish":
            #         print("   ✓ Mode verification successful")
            #     else:
            #         print(f"   ✗ Mode verification failed - expected clish, got {current_mode.value}")
            #         return False
            # else:
            #     print("   ✗ Failed to exit expert mode")
            #     return False
             
            print("\n=== Task: Expert Password Setup Successful! ===")
            return True
            
    except Exception as e:
        print(f"\n✗ Task: Expert Password Setup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def task_create_vagrant_user(config: FirewallConfig, username: str='vagrant', password: str='vagrant') -> bool:
    """
    Task: Configure vagrant user (placeholder for future implementation).
    
    Args:
        config: Firewall configuration
        
    Returns:
        False (not implemented yet)
    """
    print("⚠️  Task: Configure Vagrant User - Not implemented yet")
    return False

def task_copy_binary(config: FirewallConfig) -> bool:
    """
    Task: Copy binary files (placeholder for future implementation).
    
    Args:
        config: Firewall configuration
        
    Returns:
        False (not implemented yet)
    """
    print("⚠️  Task: Copy Binary Files - Not implemented yet")
    return False