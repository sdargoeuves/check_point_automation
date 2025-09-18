#!/usr/bin/env python3
"""
Test expert mode access with the password we set earlier.
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
    """Test expert access."""
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
        
        # Test expert mode access with the password we set
        expert_password = "admin15"
        logger.info(f"Testing expert mode access with password: {expert_password}")
        
        success = connection_manager.switch_to_expert(expert_password)
        if success:
            logger.info("✅ Expert mode access successful!")
            
            # Check current mode
            mode = connection_manager.get_cli_mode()
            logger.info(f"Current CLI mode: {mode.value}")
            
            # Try to switch back to clish
            logger.info("Switching back to clish mode...")
            clish_success = connection_manager.switch_to_clish()
            if clish_success:
                logger.info("✅ Successfully switched back to clish mode")
            else:
                logger.warning("⚠️ Failed to switch back to clish mode")
                
        else:
            logger.error("❌ Expert mode access failed")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())