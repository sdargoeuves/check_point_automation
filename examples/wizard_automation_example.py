#!/usr/bin/env python3
"""
Example script demonstrating Check Point first-time wizard automation.

This script shows how to use the InitialSetupModule to automate
the first-time wizard configuration on a fresh Check Point VM.
"""

import sys
import logging
from checkpoint_automation.core.models import WizardConfig, ConnectionInfo
from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.connection_manager import CheckPointConnectionManager
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main function demonstrating wizard automation."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Configuration for the Check Point VM
    connection_info = ConnectionInfo(
        host="192.168.1.100",  # Replace with your Check Point VM IP
        username="admin",
        password="admin"  # Default password for fresh installation
    )
    
    # Wizard configuration
    wizard_config = WizardConfig(
        hostname="cp-gateway-01",
        timezone="America/New_York",
        ntp_servers=["pool.ntp.org", "time.nist.gov"],
        dns_servers=["8.8.8.8", "8.8.4.4", "1.1.1.1"],
        domain_name="example.com"
    )
    
    # Expert password for the system
    expert_password = "SecureExpertPass123!"
    
    try:
        logger.info("Starting Check Point VM automation")
        
        # Initialize connection manager
        connection_manager = CheckPointConnectionManager()
        
        # Connect to the Check Point VM
        logger.info(f"Connecting to Check Point VM at {connection_info.host}")
        if not connection_manager.connect(connection_info):
            raise ConfigurationError("Failed to connect to Check Point VM")
            
        # Initialize the setup module
        initial_setup = InitialSetupModule(connection_manager)
        
        # Step 1: Set expert password
        logger.info("Setting expert password")
        if not initial_setup.set_expert_password(expert_password):
            raise ConfigurationError("Failed to set expert password")
        logger.info("Expert password set successfully")
        
        # Step 2: Run first-time wizard
        logger.info("Running first-time wizard automation")
        if not initial_setup.run_first_time_wizard(wizard_config):
            raise ConfigurationError("Failed to complete first-time wizard")
        logger.info("First-time wizard completed successfully")
        
        # Step 3: Verify setup completion
        logger.info("Verifying initial setup completion")
        current_config = initial_setup.get_current_config()
        logger.info(f"Current system state: {current_config}")
        
        if current_config.get("wizard_completed", False):
            logger.info("✅ Check Point VM automation completed successfully!")
            logger.info(f"Hostname: {wizard_config.hostname}")
            logger.info(f"Timezone: {wizard_config.timezone}")
            logger.info(f"DNS Servers: {', '.join(wizard_config.dns_servers)}")
            logger.info(f"NTP Servers: {', '.join(wizard_config.ntp_servers)}")
        else:
            logger.warning("⚠️  Wizard may not have completed fully. Check system status.")
            
    except (ConfigurationError, ValidationError) as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Clean up connection
        if 'connection_manager' in locals():
            connection_manager.disconnect()
            logger.info("Disconnected from Check Point VM")


if __name__ == "__main__":
    main()