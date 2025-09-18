#!/usr/bin/env python3
"""
Example script demonstrating expert password setup functionality.

This script shows how to use the InitialSetupModule to set an expert
password on a fresh Check Point VM installation.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.models import ConnectionInfo, CheckPointState
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError
from checkpoint_automation.core.logging_config import setup_logging


def main():
    """Main function demonstrating expert password setup."""
    # Setup logging
    setup_logging(log_level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("Check Point Expert Password Setup Example")
    logger.info("=" * 50)
    
    # Note: This is a demonstration with a mock connection manager
    # In real usage, you would use the actual CheckPointConnectionManager
    
    class MockConnectionManager:
        """Mock connection manager for demonstration."""
        
        def __init__(self):
            self.connected = True
            self.state = CheckPointState.FRESH_INSTALL
            self.expert_password = None
            
        def is_connected(self):
            return self.connected
            
        def detect_state(self):
            return self.state
            
        def get_cli_mode(self):
            from checkpoint_automation.core.models import CLIMode
            return CLIMode.CLISH
            
        def switch_to_clish(self):
            return True
            
        def switch_to_expert(self, password):
            return self.expert_password == password
            
        def execute_command(self, command, mode=None):
            from checkpoint_automation.core.models import CommandResult
            
            if command == "set expert-password":
                return CommandResult(
                    command=command,
                    success=True,
                    output="Enter password:"
                )
            elif len(command) >= 8:  # Assume this is a password
                self.expert_password = command
                return CommandResult(
                    command=command,
                    success=True,
                    output="Password set successfully"
                )
            
            return CommandResult(
                command=command,
                success=True,
                output="Command executed"
            )
    
    try:
        # Create connection manager and initial setup module
        connection_manager = MockConnectionManager()
        initial_setup = InitialSetupModule(connection_manager)
        
        logger.info("Initializing connection to Check Point VM...")
        
        # Check prerequisites
        if not initial_setup.validate_prerequisites():
            logger.error("Prerequisites not met for expert password setup")
            return 1
        
        logger.info("Prerequisites validated successfully")
        
        # Get current configuration state
        current_config = initial_setup.get_current_config()
        logger.info(f"Current system state: {current_config}")
        
        # Set expert password
        expert_password = "SecureExpert123!"
        logger.info("Setting expert password...")
        
        # Validate password before setting
        config = {"expert_password": expert_password}
        if not initial_setup.validate_config(config):
            logger.error("Password validation failed")
            return 1
        
        # Set the expert password
        success = initial_setup.set_expert_password(expert_password)
        
        if success:
            logger.info("Expert password set successfully!")
            
            # Verify the password works
            if connection_manager.switch_to_expert(expert_password):
                logger.info("Expert password verification successful")
            else:
                logger.warning("Expert password verification failed")
                
        else:
            logger.error("Failed to set expert password")
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
    
    logger.info("Expert password setup completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())