#!/usr/bin/env python3
"""
Debug the clish mode switching issue.
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
    """Debug clish switching."""
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
        
        # Now manually test the exit sequence
        logger.info("Manually testing exit sequence...")
        
        # Get direct shell access
        shell = connection_manager._shell
        
        # Send exit command
        logger.info("Sending 'exit' command...")
        shell.send("exit\n")
        time.sleep(2)
        
        # Read output
        output = ""
        start_time = time.time()
        while time.time() - start_time < 5:
            if shell.recv_ready():
                chunk = shell.recv(1024).decode('utf-8', errors='ignore')
                output += chunk
                logger.info(f"Received chunk: {repr(chunk)}")
                if ">" in chunk and "[" not in chunk:  # CLISH prompt
                    break
            time.sleep(0.1)
        
        logger.info(f"Full exit output: {repr(output)}")
        
        # Test current mode detection
        logger.info("Testing mode detection after exit...")
        mode = connection_manager.get_cli_mode()
        logger.info(f"Detected mode: {mode.value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())