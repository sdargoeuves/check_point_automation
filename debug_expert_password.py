#!/usr/bin/env python3
"""
Debug script to understand expert password behavior on real device.
"""

import sys
import logging
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo, CLIMode


def setup_logging():
    """Configure logging for detailed output."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Debug expert password functionality."""
    logger = setup_logging()
    logger.info("🔍 Debugging Expert Password Functionality")
    
    # Connection details
    connection_info = ConnectionInfo(
        host="10.194.58.200",
        port=22,
        username="admin",
        password="admin",
        timeout=30
    )
    
    connection_manager = None
    
    try:
        # Create connection manager
        connection_manager = CheckPointConnectionManager()
        
        # Connect to device
        logger.info("Connecting to Check Point device...")
        if not connection_manager.connect(connection_info):
            logger.error("❌ Failed to connect to device")
            return 1
        
        logger.info("✅ Connected successfully!")
        
        # Check current state
        state = connection_manager.detect_state()
        logger.info(f"Current state: {state.value}")
        
        # Check current CLI mode
        mode = connection_manager.get_cli_mode()
        logger.info(f"Current CLI mode: {mode.value}")
        
        # Test expert command to see what happens
        logger.info("Testing 'expert' command...")
        result = connection_manager.execute_command("expert", CLIMode.CLISH)
        logger.info(f"Expert command result:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Output: '{result.output}'")
        logger.info(f"  Error: '{result.error}'")
        
        # Test set expert-password command
        logger.info("Testing 'set expert-password' command...")
        result = connection_manager.execute_command("set expert-password", CLIMode.CLISH)
        logger.info(f"Set expert-password result:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Output: '{result.output}'")
        logger.info(f"  Error: '{result.error}'")
        
        # If we see a password prompt, let's manually handle it
        if "password" in result.output.lower():
            logger.info("Password prompt detected, sending password...")
            password = "admin15"  # Same password as the test
            
            # Send password
            password_result = connection_manager.execute_command(password, CLIMode.CLISH)
            logger.info(f"Password entry result:")
            logger.info(f"  Success: {password_result.success}")
            logger.info(f"  Output: '{password_result.output}'")
            logger.info(f"  Error: '{password_result.error}'")
            
            # Wait a bit and check for more output
            logger.info("Waiting for potential confirmation prompt...")
            time.sleep(3)
            
            # Try to read more output by sending a simple command
            newline_result = connection_manager.execute_command("show hostname", CLIMode.CLISH)
            logger.info(f"Additional output check:")
            logger.info(f"  Success: {newline_result.success}")
            logger.info(f"  Output: '{newline_result.output}'")
            logger.info(f"  Error: '{newline_result.error}'")
            
            # Check for confirmation prompt in either result
            combined_output = password_result.output + newline_result.output
            if "again" in combined_output.lower() or "confirm" in combined_output.lower():
                logger.info("Confirmation prompt detected, sending password again...")
                confirm_result = connection_manager.execute_command(password, CLIMode.CLISH)
                logger.info(f"Confirmation result:")
                logger.info(f"  Success: {confirm_result.success}")
                logger.info(f"  Output: '{confirm_result.output}'")
                logger.info(f"  Error: '{confirm_result.error}'")
            else:
                logger.info("No confirmation prompt detected, assuming password is set")
                
            # Now test if expert password works
            logger.info("Testing expert mode access with new password...")
            expert_result = connection_manager.execute_command("expert", CLIMode.CLISH)
            logger.info(f"Expert access test:")
            logger.info(f"  Success: {expert_result.success}")
            logger.info(f"  Output: '{expert_result.output}'")
            logger.info(f"  Error: '{expert_result.error}'")
            
            if "password:" in expert_result.output.lower():
                logger.info("Password prompt for expert mode, sending password...")
                expert_pass_result = connection_manager.execute_command(password, CLIMode.CLISH)
                logger.info(f"Expert password entry:")
                logger.info(f"  Success: {expert_pass_result.success}")
                logger.info(f"  Output: '{expert_pass_result.output}'")
                logger.info(f"  Error: '{expert_pass_result.error}'")
                
                # Check if we're now in expert mode
                time.sleep(2)
                current_mode = connection_manager.get_cli_mode()
                logger.info(f"Current CLI mode after expert: {current_mode.value}")
            else:
                logger.info("No password prompt - expert password may not be set correctly")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        return 1
        
    finally:
        # Clean up
        if connection_manager:
            logger.info("Disconnecting from device...")
            connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())