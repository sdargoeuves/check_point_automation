#!/usr/bin/env python3
"""
Test script using the actual InitialSetupModule to set expert password.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo
from checkpoint_automation.modules.initial_setup import InitialSetupModule


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
    """Test expert password setup using InitialSetupModule."""
    logger = setup_logging()
    logger.info("🔧 Testing Expert Password Setup with InitialSetupModule")
    
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
        
        # Create initial setup module
        initial_setup = InitialSetupModule(connection_manager)
        
        # Check current state
        state = connection_manager.detect_state()
        logger.info(f"Current state: {state.value}")
        
        # Test expert password setup with a simple password
        test_password = "admin15"  # Simple password that you've used successfully
        logger.info(f"Setting expert password: {test_password}")
        
        try:
            success = initial_setup.set_expert_password(test_password)
            if success:
                logger.info("✅ Expert password set successfully!")
                
                # Test if we can now access expert mode
                logger.info("Testing expert mode access...")
                if connection_manager.switch_to_expert(test_password):
                    logger.info("✅ Expert mode access successful!")
                    connection_manager.switch_to_clish()
                else:
                    logger.error("❌ Expert mode access failed")
            else:
                logger.error("❌ Expert password setup failed")
                
        except Exception as e:
            logger.error(f"❌ Exception during expert password setup: {e}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1
        
    finally:
        # Clean up
        if connection_manager:
            logger.info("Disconnecting from device...")
            connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())