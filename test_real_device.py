#!/usr/bin/env python3
"""
Test script for real Check Point device at 10.194.58.200

This script tests all implemented functionality against a real Check Point VM
to validate our implementation works correctly with actual hardware.
"""

import sys
import logging
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo, WizardConfig
from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError, AuthenticationError


def setup_logging():
    """Configure logging for detailed output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('test_real_device.log')
        ]
    )
    return logging.getLogger(__name__)


def test_connection_and_state_detection(connection_manager, logger):
    """Test basic connection and state detection."""
    logger.info("=" * 60)
    logger.info("TESTING: Connection and State Detection")
    logger.info("=" * 60)
    
    try:
        # Test connection
        logger.info("Testing connection...")
        if not connection_manager.is_connected():
            logger.error("Connection failed!")
            return False
        logger.info("✅ Connection successful")
        
        # Test state detection
        logger.info("Testing state detection...")
        current_state = connection_manager.detect_state()
        logger.info(f"✅ Detected state: {current_state.value}")
        
        # Test CLI mode detection
        logger.info("Testing CLI mode detection...")
        cli_mode = connection_manager.get_cli_mode()
        logger.info(f"✅ Detected CLI mode: {cli_mode.value}")
        
        # Get system status
        logger.info("Testing system status retrieval...")
        try:
            system_status = connection_manager.get_system_status()
            logger.info(f"✅ System Status:")
            logger.info(f"   - State: {system_status.state.value}")
            logger.info(f"   - Version: {system_status.version}")
            logger.info(f"   - Hostname: {system_status.hostname}")
            logger.info(f"   - CLI Mode: {system_status.cli_mode.value}")
            logger.info(f"   - Expert Password Set: {system_status.expert_password_set}")
            logger.info(f"   - Wizard Completed: {system_status.wizard_completed}")
        except Exception as e:
            logger.warning(f"⚠️  System status retrieval failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection/State test failed: {e}")
        return False


def test_initial_setup_module(connection_manager, logger):
    """Test the initial setup module functionality."""
    logger.info("=" * 60)
    logger.info("TESTING: Initial Setup Module")
    logger.info("=" * 60)
    
    try:
        # Create initial setup module
        initial_setup = InitialSetupModule(connection_manager)
        
        # Test prerequisites validation
        logger.info("Testing prerequisites validation...")
        prereqs_ok = initial_setup.validate_prerequisites()
        logger.info(f"✅ Prerequisites validation: {prereqs_ok}")
        
        # Test current config retrieval
        logger.info("Testing current config retrieval...")
        current_config = initial_setup.get_current_config()
        logger.info(f"✅ Current config: {current_config}")
        
        return initial_setup
        
    except Exception as e:
        logger.error(f"❌ Initial setup module test failed: {e}")
        return None


def test_expert_password_functionality(initial_setup, logger):
    """Test expert password setup functionality."""
    logger.info("=" * 60)
    logger.info("TESTING: Expert Password Functionality")
    logger.info("=" * 60)
    
    try:
        # Test password validation
        logger.info("Testing password validation...")
        
        # Test weak passwords
        weak_passwords = ["weak", "nouppercase123!", "NOLOWERCASE123!", "NoDigits!", "NoSpecialChars123"]
        for weak_pass in weak_passwords:
            is_valid = initial_setup._validate_password_strength(weak_pass)
            logger.info(f"   Password '{weak_pass}': {'❌ Invalid' if not is_valid else '✅ Valid'}")
        
        # Test strong password
        strong_password = "TestExpertPass123!"
        is_valid = initial_setup._validate_password_strength(strong_password)
        logger.info(f"   Password '{strong_password}': {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        # Check if expert password is already set
        logger.info("Checking current expert password status...")
        current_state = initial_setup.connection_manager.detect_state()
        
        if current_state.value == "fresh":
            logger.info("System is in fresh state - expert password can be set")
            
            # Ask user if they want to proceed with setting expert password
            response = input("\n🤔 Do you want to set the expert password? (y/N): ").strip().lower()
            if response == 'y':
                try:
                    logger.info(f"Setting expert password to: {strong_password}")
                    success = initial_setup.set_expert_password(strong_password)
                    if success:
                        logger.info("✅ Expert password set successfully!")
                        return strong_password
                    else:
                        logger.error("❌ Expert password setting failed")
                        return None
                except Exception as e:
                    logger.error(f"❌ Expert password setting failed: {e}")
                    return None
            else:
                logger.info("⏭️  Skipping expert password setting")
                return None
        else:
            logger.info(f"System state is '{current_state.value}' - expert password may already be set")
            return "TestExpertPass123!"  # Assume this is the password if already set
            
    except Exception as e:
        logger.error(f"❌ Expert password test failed: {e}")
        return None


def test_admin_password_functionality(initial_setup, logger):
    """Test admin password update functionality."""
    logger.info("=" * 60)
    logger.info("TESTING: Admin Password Update Functionality")
    logger.info("=" * 60)
    
    try:
        # Test admin password update
        new_admin_password = "NewAdminPass123!"
        
        logger.info("Testing admin password validation...")
        is_valid = initial_setup._validate_password_strength(new_admin_password)
        logger.info(f"✅ Admin password validation: {'Valid' if is_valid else 'Invalid'}")
        
        # Ask user if they want to proceed with updating admin password
        response = input(f"\n🤔 Do you want to update the admin password to '{new_admin_password}'? (y/N): ").strip().lower()
        if response == 'y':
            try:
                logger.info("Updating admin password...")
                success = initial_setup.update_admin_password(new_admin_password)
                if success:
                    logger.info("✅ Admin password updated successfully!")
                    logger.info(f"   New admin password: {new_admin_password}")
                    return new_admin_password
                else:
                    logger.error("❌ Admin password update failed")
                    return None
            except Exception as e:
                logger.error(f"❌ Admin password update failed: {e}")
                return None
        else:
            logger.info("⏭️  Skipping admin password update")
            return None
            
    except Exception as e:
        logger.error(f"❌ Admin password test failed: {e}")
        return None


def test_wizard_functionality(initial_setup, expert_password, logger):
    """Test first-time wizard functionality."""
    logger.info("=" * 60)
    logger.info("TESTING: First-Time Wizard Functionality")
    logger.info("=" * 60)
    
    try:
        # Check if wizard needs to be run
        current_state = initial_setup.connection_manager.detect_state()
        
        if current_state.value in ["fresh", "expert_set"]:
            logger.info("System needs wizard configuration")
            
            # Create wizard config
            wizard_config = WizardConfig(
                hostname="checkpoint-test",
                timezone="UTC",
                ntp_servers=["pool.ntp.org", "time.nist.gov"],
                dns_servers=["8.8.8.8", "8.8.4.4"],
                domain_name="test.local"
            )
            
            logger.info(f"Wizard configuration:")
            logger.info(f"   - Hostname: {wizard_config.hostname}")
            logger.info(f"   - Timezone: {wizard_config.timezone}")
            logger.info(f"   - NTP Servers: {wizard_config.ntp_servers}")
            logger.info(f"   - DNS Servers: {wizard_config.dns_servers}")
            logger.info(f"   - Domain: {wizard_config.domain_name}")
            
            # Ask user if they want to proceed with wizard
            response = input("\n🤔 Do you want to run the first-time wizard? (y/N): ").strip().lower()
            if response == 'y':
                try:
                    logger.info("Running first-time wizard...")
                    success = initial_setup.run_first_time_wizard(wizard_config)
                    if success:
                        logger.info("✅ First-time wizard completed successfully!")
                        return True
                    else:
                        logger.error("❌ First-time wizard failed")
                        return False
                except Exception as e:
                    logger.error(f"❌ First-time wizard failed: {e}")
                    return False
            else:
                logger.info("⏭️  Skipping first-time wizard")
                return None
        else:
            logger.info(f"System state is '{current_state.value}' - wizard may already be completed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Wizard test failed: {e}")
        return False


def test_cli_mode_switching(connection_manager, expert_password, logger):
    """Test CLI mode switching functionality."""
    logger.info("=" * 60)
    logger.info("TESTING: CLI Mode Switching")
    logger.info("=" * 60)
    
    try:
        # Get current mode
        current_mode = connection_manager.get_cli_mode()
        logger.info(f"Current CLI mode: {current_mode.value}")
        
        if expert_password:
            # Test switching to expert mode
            logger.info("Testing switch to expert mode...")
            success = connection_manager.switch_to_expert(expert_password)
            if success:
                logger.info("✅ Successfully switched to expert mode")
                
                # Verify we're in expert mode
                mode = connection_manager.get_cli_mode()
                logger.info(f"   Current mode: {mode.value}")
                
                # Test switching back to clish
                logger.info("Testing switch back to clish mode...")
                success = connection_manager.switch_to_clish()
                if success:
                    logger.info("✅ Successfully switched back to clish mode")
                    
                    # Verify we're in clish mode
                    mode = connection_manager.get_cli_mode()
                    logger.info(f"   Current mode: {mode.value}")
                    return True
                else:
                    logger.error("❌ Failed to switch back to clish mode")
                    return False
            else:
                logger.error("❌ Failed to switch to expert mode")
                return False
        else:
            logger.info("⏭️  No expert password available - skipping mode switching test")
            return None
            
    except Exception as e:
        logger.error(f"❌ CLI mode switching test failed: {e}")
        return False


def main():
    """Main test function."""
    logger = setup_logging()
    logger.info("🚀 Starting Check Point Real Device Test")
    logger.info(f"Target device: 10.194.58.200")
    
    # Connection details
    connection_info = ConnectionInfo(
        host="10.194.58.200",
        port=22,
        username="admin",
        password="admin",
        timeout=30
    )
    
    connection_manager = None
    expert_password = None
    
    try:
        # Create connection manager
        logger.info("Creating connection manager...")
        connection_manager = CheckPointConnectionManager()
        
        # Connect to device
        logger.info("Connecting to Check Point device...")
        if not connection_manager.connect(connection_info):
            logger.error("❌ Failed to connect to device")
            return 1
        
        logger.info("✅ Connected successfully!")
        
        # Run tests
        test_results = {}
        
        # Test 1: Connection and State Detection
        test_results['connection'] = test_connection_and_state_detection(connection_manager, logger)
        
        # Test 2: Initial Setup Module
        initial_setup = test_initial_setup_module(connection_manager, logger)
        test_results['initial_setup_module'] = initial_setup is not None
        
        if initial_setup:
            # Test 3: Expert Password Functionality
            expert_password = test_expert_password_functionality(initial_setup, logger)
            test_results['expert_password'] = expert_password is not None
            
            # Test 4: Admin Password Functionality
            new_admin_password = test_admin_password_functionality(initial_setup, logger)
            test_results['admin_password'] = new_admin_password is not None
            
            # Test 5: Wizard Functionality
            wizard_result = test_wizard_functionality(initial_setup, expert_password, logger)
            test_results['wizard'] = wizard_result is True
            
            # Test 6: CLI Mode Switching
            cli_switching_result = test_cli_mode_switching(connection_manager, expert_password, logger)
            test_results['cli_switching'] = cli_switching_result is True
        
        # Print summary
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed!")
            return 0
        else:
            logger.warning("⚠️  Some tests failed or were skipped")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return 1
        
    finally:
        # Clean up
        if connection_manager:
            logger.info("Disconnecting from device...")
            connection_manager.disconnect()
            logger.info("✅ Disconnected")


if __name__ == "__main__":
    sys.exit(main())