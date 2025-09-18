#!/usr/bin/env python3
"""
Test the exit behavior from expert mode to clish mode.
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


def main():
    """Test exit behavior."""
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    connection_info = ConnectionInfo(
        host="10.194.58.200",
        port=22,
        username="admin",
        password="admin",
        timeout=30
    )
    
    connection_manager = CheckPointConnectionManager()
    
    try:
        logger.info("Connecting to Check Point device...")
        if not connection_manager.connect(connection_info):
            logger.error("Failed to connect")
            return 1
        
        logger.info("Connected successfully!")
        
        # Switch to expert mode
        expert_password = "admin15"
        logger.info("Switching to expert mode...")
        
        success = connection_manager.switch_to_expert(expert_password)
        if not success:
            logger.error("Failed to switch to expert mode")
            return 1
            
        logger.info("✅ In expert mode")
        
        # Check current mode
        mode = connection_manager.get_cli_mode()
        logger.info(f"Current CLI mode: {mode.value}")
        
        # Now test the exit behavior manually
        logger.info("Testing manual exit...")
        shell = connection_manager._shell
        
        # Send first exit command
        logger.info("Sending first 'exit' command...")
        shell.send("exit\n")
        time.sleep(2)
        
        if shell.recv_ready():
            output1 = shell.recv(1024).decode('utf-8', errors='ignore')
            logger.info(f"Output after first exit: {repr(output1)}")
        
        # Send second exit command
        logger.info("Sending second 'exit' command...")
        shell.send("exit\n")
        time.sleep(2)
        
        if shell.recv_ready():
            output2 = shell.recv(1024).decode('utf-8', errors='ignore')
            logger.info(f"Output after second exit: {repr(output2)}")
        
        # Wait a bit more and check for any additional output
        time.sleep(2)
        if shell.recv_ready():
            output3 = shell.recv(1024).decode('utf-8', errors='ignore')
            logger.info(f"Additional output: {repr(output3)}")
        
        # Check final mode
        final_mode = connection_manager.get_cli_mode()
        logger.info(f"Final CLI mode: {final_mode.value}")
        
        # Test the switch_to_clish method
        logger.info("Testing switch_to_clish method...")
        clish_success = connection_manager.switch_to_clish()
        logger.info(f"switch_to_clish result: {clish_success}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())