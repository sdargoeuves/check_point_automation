#!/usr/bin/env python3
"""
Example script demonstrating admin password update functionality.

This script shows how to use the InitialSetupModule to update the admin
password on a Check Point VM after the initial setup is complete.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo
from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError


def main():
    """Main function demonstrating admin password update."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Check Point VM connection details
    # Note: These should be updated to match your actual VM
    connection_info = ConnectionInfo(
        host="192.168.1.100",  # Replace with your Check Point VM IP
        port=22,
        username="admin",
        password="admin",  # Default password
        timeout=30
    )
    
    try:
        logger.info("Starting admin password update example")
        
        # Create connection manager
        logger.info(f"Connecting to Check Point VM at {connection_info.host}")
        connection_manager = CheckPointConnectionManager(connection_info)
        
        # Connect to the VM
        if not connection_manager.connect():
            logger.error("Failed to connect to Check Point VM")
            return 1
            
        logger.info("Successfully connected to Check Point VM")
        
        # Create initial setup module
        initial_setup = InitialSetupModule(connection_manager)
        
        # Check current system state
        current_config = initial_setup.get_current_config()
        logger.info(f"Current system state: {current_config}")
        
        # Validate prerequisites for admin password update
        if not initial_setup.validate_prerequisites():
            logger.error("Prerequisites not met for admin password update")
            return 1
            
        # Define new admin password
        # Note: This should be a strong password meeting Check Point requirements
        new_admin_password = "NewSecureAdminPass123!"
        
        logger.info("Updating admin password...")
        
        # Update admin password
        success = initial_setup.update_admin_password(new_admin_password)
        
        if success:
            logger.info("Admin password updated successfully!")
            logger.info("You can now use the new password to connect to the Check Point VM")
        else:
            logger.error("Failed to update admin password")
            return 1
            
    except ValidationError as e:
        logger.error(f"Password validation error: {e}")
        return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        # Clean up connection
        if 'connection_manager' in locals():
            connection_manager.disconnect()
            logger.info("Disconnected from Check Point VM")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())