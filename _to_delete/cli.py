"""
Command-line interface for Check Point automation.
"""

import argparse
import logging
import sys
from typing import Optional

from .config import FirewallConfig
from .ssh_connection import SSHConnectionManager


def setup_logging(level: str = "INFO") -> None:
    """Set up global logging configuration."""
    # Only configure root logger for paramiko and other third-party libraries
    # Our custom loggers handle their own configuration
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings/errors from third-party libs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set paramiko to WARNING to reduce noise
    logging.getLogger("paramiko").setLevel(logging.WARNING)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check Point VM Automation Tool"
    )
    parser.add_argument(
        "--ip", 
        required=True, 
        help="Firewall IP address"
    )
    parser.add_argument(
        "--username", 
        default="admin", 
        help="SSH username (default: admin)"
    )
    parser.add_argument(
        "--password", 
        default="admin", 
        help="SSH password (default: admin)"
    )
    parser.add_argument(
        "--expert-password", 
        help="Expert mode password"
    )
    parser.add_argument(
        "--log-level", 
        default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--test-connection", 
        action="store_true",
        help="Test SSH connection only"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    try:
        # Create configuration
        config = FirewallConfig(
            ip_address=args.ip,
            username=args.username,
            password=args.password,
            expert_password=args.expert_password
        )
        
        # Test connection if requested
        if args.test_connection:
            with SSHConnectionManager(config, console_log_level=args.log_level) as ssh:
                print(f"Successfully connected to {config.ip_address}")
                return
        
        print("Use --test-connection to test SSH connectivity")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()