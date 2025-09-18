#!/usr/bin/env python3
"""
Debug the exact output when exiting expert mode.
"""

import sys
import logging
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo


def main():
    """Debug exit output."""
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
        logger.info("Connecting...")
        if not connection_manager.connect(connection_info):
            return 1
        
        # Switch to expert mode
        logger.info("Switching to expert mode...")
        connection_manager.switch_to_expert("admin15")
        
        # First check what shell we're in
        logger.info("Checking current shell...")
        shell = connection_manager._shell
        
        shell.send("echo $0\n")
        time.sleep(1)
        if shell.recv_ready():
            shell_output = shell.recv(1024).decode('utf-8', errors='ignore')
            logger.info(f"Shell check output: {repr(shell_output)}")
        
        # Try 'clish' command to switch back
        logger.info("Trying 'clish' command...")
        shell.send("clish\n")
        
        # Wait and read output in stages
        output = ""
        for i in range(10):  # Wait up to 10 seconds
            time.sleep(1)
            if shell.recv_ready():
                chunk = shell.recv(1024).decode('utf-8', errors='ignore')
                output += chunk
                logger.info(f"After {i+1}s: {repr(chunk)}")
                
                # Check if we got the clish prompt
                if ">" in chunk and "[Expert@" not in chunk:
                    logger.info("Found clish prompt!")
                    break
            else:
                logger.info(f"No output after {i+1}s")
        
        logger.info(f"Complete exit output: {repr(output)}")
        
        # Test what happens if we send 'expert' command now
        logger.info("Testing 'expert' command to see current mode...")
        shell.send("expert\n")
        time.sleep(2)
        
        if shell.recv_ready():
            expert_output = shell.recv(1024).decode('utf-8', errors='ignore')
            logger.info(f"Expert command output: {repr(expert_output)}")
            
            if "Enter expert password:" in expert_output:
                logger.info("✅ We're in CLISH mode! (expert asks for password)")
            elif "[Expert@" in expert_output:
                logger.info("❌ We're still in EXPERT mode")
            else:
                logger.info(f"🤔 Unclear mode, output: {expert_output}")
        
        # Check what we're looking for
        has_gt = ">" in output
        no_expert = "[Expert@" not in output
        
        logger.info(f"Contains '>': {has_gt}")
        logger.info(f"No '[Expert@': {no_expert}")
        logger.info(f"Should succeed: {has_gt and no_expert}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        connection_manager.disconnect()


if __name__ == "__main__":
    sys.exit(main())