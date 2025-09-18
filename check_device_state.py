#!/usr/bin/env python3
"""
Simple script to check the current state of the Check Point device.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo, CLIMode


def main():
    """Check device state."""
    logging.basicConfig(level=logging.INFO)
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
        
        # Check current state
        state = connection_manager.detect_state()
        logger.info(f"Current state: {state.value}")
        
        # Check CLI mode
        mode = connection_manager.get_cli_mode()
        logger.info(f"Current CLI mode: {mode.value}")
        
        # Test expert command
        logger.info("Testing 'expert' command...")
        result = connection_manager.execute_command("expert", CLIMode.CLISH)
        logger.info(f"Expert command output: {repr(result.output)}")
        
        # Test set expert-password command
        logger.info("Testing 'set expert-password' command...")
        result = connection_manager.execute_command("set expert-password", CLIMode.CLISH)
        logger.info(f"Set expert-password output: {repr(result.output)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())