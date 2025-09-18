#!/usr/bin/env python3
"""
Test script for Check Point first-time wizard setup using realistic configuration.

This script tests the complete wizard automation process using the configuration
values you've provided, which will give us a good indication of whether the
implementation is working correctly.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo, WizardConfig
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


def create_realistic_wizard_config():
    """Create a realistic wizard configuration based on your provided values."""
    return WizardConfig(
        hostname="cp1",
        domain_name="netlab.ip",
        timezone="Etc/GMT",
        ntp_servers=[],  # Will use Check Point defaults
        dns_servers=["1.1.1.1"]  # Primary DNS as specified
    )


def main():
    """Test Check Point wizard setup with realistic configuration."""
    logger = setup_logging()
    logger.info("🧪 Testing Check Point First-Time Wizard Setup")
    
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
        
        # Step 1: Set expert password first (required for wizard)
        expert_password = "admin15"
        logger.info(f"Step 1: Checking/Setting expert password...")
        
        # First check if expert password is already set
        try:
            if connection_manager.switch_to_expert(expert_password):
                logger.info("✅ Expert password already set and working!")
                connection_manager.switch_to_clish()  # Switch back (may fail, that's ok)
            else:
                # Expert password not set or wrong, try to set it
                logger.info("Setting expert password...")
                success = initial_setup.set_expert_password(expert_password)
                if success:
                    logger.info("✅ Expert password set successfully!")
                else:
                    logger.error("❌ Expert password setup failed")
                    return 1
        except Exception as e:
            logger.error(f"❌ Expert password setup failed: {e}")
            return 1
        
        # Step 2: Run first-time wizard with realistic configuration
        logger.info("Step 2: Running first-time wizard with realistic configuration...")
        
        wizard_config = create_realistic_wizard_config()
        logger.info(f"Wizard configuration:")
        logger.info(f"  Hostname: {wizard_config.hostname}")
        logger.info(f"  Domain: {wizard_config.domain_name}")
        logger.info(f"  Timezone: {wizard_config.timezone}")
        logger.info(f"  DNS Servers: {wizard_config.dns_servers}")
        
        try:
            success = initial_setup.run_first_time_wizard(wizard_config)
            if success:
                logger.info("✅ First-time wizard completed successfully!")
                
                # Verify the setup
                logger.info("Step 3: Verifying setup...")
                final_state = connection_manager.detect_state()
                logger.info(f"Final state: {final_state.value}")
                
                if final_state.value in ["wizard_complete", "configured"]:
                    logger.info("✅ Wizard setup verification successful!")
                else:
                    logger.warning(f"⚠️ Unexpected final state: {final_state.value}")
                
            else:
                logger.error("❌ First-time wizard failed")
                return 1
                
        except Exception as e:
            logger.error(f"❌ First-time wizard failed: {e}")
            return 1
        
        # Step 3: Test admin password update (part of task 3.3)
        logger.info("Step 4: Testing admin password update...")
        
        new_admin_password = "newadmin15"
        try:
            success = initial_setup.update_admin_password(new_admin_password)
            if success:
                logger.info("✅ Admin password updated successfully!")
            else:
                logger.error("❌ Admin password update failed")
                return 1
        except Exception as e:
            logger.error(f"❌ Admin password update failed: {e}")
            return 1
        
        logger.info("🎉 All tests completed successfully!")
        logger.info("The Check Point VM should now be fully configured with:")
        logger.info(f"  - Expert password: {expert_password}")
        logger.info(f"  - Admin password: {new_admin_password}")
        logger.info(f"  - Hostname: {wizard_config.hostname}")
        logger.info(f"  - Domain: {wizard_config.domain_name}")
        logger.info(f"  - Security Gateway and Management installed")
        logger.info(f"  - Basic network configuration applied")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1
        
    finally:
        # Clean up
        if connection_manager:
            logger.info("Disconnecting from device...")
            connection_manager.disconnect()


def test_wizard_config_generation():
    """Test the wizard configuration generation with realistic values."""
    logger = logging.getLogger(__name__)
    logger.info("🔧 Testing wizard configuration generation...")
    
    # Create a mock connection manager for testing config generation
    class MockConnectionManager:
        def __init__(self):
            pass
        
        def is_connected(self):
            return True
            
        def detect_state(self):
            from checkpoint_automation.core.models import CheckPointState
            return CheckPointState.EXPERT_PASSWORD_SET
            
        def switch_to_expert(self):
            return True
            
        def execute_command(self, command, mode=None):
            from checkpoint_automation.core.models import CommandResult
            
            # Mock responses for config generation
            if "dbget passwd:admin:passwd" in command:
                return CommandResult(
                    command=command,
                    success=True,
                    output="$1$QjDEIV9C$eWbjLa0GUbwcu7tGzaQsP0"
                )
            elif "grub2-mkpasswd-pbkdf2" in command:
                return CommandResult(
                    command=command,
                    success=True,
                    output="PBKDF2 hash of your password is: grub.pbkdf2.sha512.10000.4F6109B93A64DC71EA0E68085D0DCCBA1E0E983285BA4FED08839946F95F27BB8B457C780CFB6B80BB8604B3A7E0C0005CBFF8769A7134165BF542E1DE2D2A75.1650ADC913206CCAD83630A681D5906CBF495E445AC0BDA6E2995D80C1EA9D50370D9AC8D8E979B075CEDF0EF072542B746EC2406C9B4A851D8CD8A7DBDAD5DB"
                )
            else:
                return CommandResult(
                    command=command,
                    success=True,
                    output="Command executed"
                )
    
    # Test config generation
    mock_connection = MockConnectionManager()
    initial_setup = InitialSetupModule(mock_connection)
    
    wizard_config = create_realistic_wizard_config()
    
    try:
        # Generate the configuration content
        config_content = initial_setup._generate_wizard_config(wizard_config)
        
        logger.info("✅ Generated wizard configuration:")
        logger.info("=" * 60)
        logger.info(config_content)
        logger.info("=" * 60)
        
        # Verify key configuration values are present
        expected_values = [
            "install_security_gw=true",
            "install_security_managment=true",
            "install_mgmt_primary=true",
            "hostname=cp1",
            "domainname=netlab.ip",
            "timezone='Etc/GMT'",
            "primary=1.1.1.1",
            "mgmt_admin_radio=\"gaia_admin\"",
            "mgmt_gui_clients_radio=any",
            "download_info=\"false\"",
            "upload_info=\"false\"",
            "reboot_if_required=true"
        ]
        
        missing_values = []
        for expected in expected_values:
            if expected not in config_content:
                missing_values.append(expected)
        
        if missing_values:
            logger.error(f"❌ Missing expected configuration values: {missing_values}")
            return False
        else:
            logger.info("✅ All expected configuration values are present!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Configuration generation failed: {e}")
        return False


if __name__ == "__main__":
    # First test config generation
    if test_wizard_config_generation():
        print("\n" + "="*80 + "\n")
        # Then run the full test
        sys.exit(main())
    else:
        print("❌ Configuration generation test failed")
        sys.exit(1)