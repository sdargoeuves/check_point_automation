#!/usr/bin/env python3
"""
Main CheckPoint Automation Script
Programmatic interface for CheckPoint firewall management tasks.
"""

import argparse
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from checkpoint_utils.config import FirewallConfig
from checkpoint_utils.tasks import (
    task_copy_binary,
    task_create_vagrant_user,
    task_set_expert_password,
)


def create_argument_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="CheckPoint Firewall Management Tool - Automate common firewall tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Tasks:
  1 - Set Expert Password
  2 - Configure Vagrant User (Coming Soon) 
  3 - Copy Binary Files (Coming Soon)

Examples:
  # Run default task (expert password setup)
  python checkpoint_main.py 10.194.59.200
  
  # Run specific tasks
  python checkpoint_main.py 10.194.59.200 --task 1
  python checkpoint_main.py 10.194.59.200 -t 2,3
  
  # Custom credentials and timeouts
  python checkpoint_main.py 10.194.59.200 -u admin -p mypass -e myexpert --task 1,2
  python checkpoint_main.py 10.194.59.200 --timeout 60 --read-timeout 10 --task 2
  
  # Debug with extended timeouts
  python checkpoint_main.py 10.194.59.200 --log-level debug --timeout 120 --task 1
        """,
    )

    # Required argument
    parser.add_argument("firewall_ip", help="IP address of the CheckPoint firewall")

    # Optional authentication arguments
    parser.add_argument("-u", "--username", default="admin", help="Admin username (default: admin)")

    parser.add_argument("-p", "--password", default="admin", help="Admin password (default: admin)")

    parser.add_argument(
        "-e",
        "--expert-password",
        default="admin15",
        help="Expert password (default: admin15)",
    )

    # Task selection
    parser.add_argument(
        "-t",
        "--task",
        "--tasks",
        default="1",
        help="Comma-separated list of tasks to run (default: 1)",
    )

    # Logging level
    parser.add_argument(
        "-l",
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        type=str.upper,
        help="Set logging level (default: INFO)",
    )

    # Timeout configuration
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Connection and command timeout in seconds (default: 30)",
    )

    parser.add_argument(
        "--read-timeout",
        type=int,
        default=5,
        help="Quick read timeout for connection checks in seconds (default: 5)",
    )

    return parser


def run_tasks(config: FirewallConfig, task_list: list) -> bool:
    """
    Run the specified tasks in sequence.

    Args:
        config: Firewall configuration
        task_list: List of task numbers to run

    Returns:
        True if all tasks succeeded, False otherwise
    """
    print("\n" + "=" * 70)
    print("🚀 CheckPoint Firewall Management Tool")
    print("=" * 70)
    print(f"Target: {config.ip_address}")
    print(f"Tasks to run: {', '.join(map(str, task_list))}")
    print("=" * 70)

    task_functions = {
        1: ("Set Expert Password", task_set_expert_password),
        2: ("Configure Vagrant User", task_create_vagrant_user),
        3: ("Copy Binary Files", task_copy_binary),
    }

    results = []

    for task_num in task_list:
        if task_num not in task_functions:
            print(f"\n❌ Unknown task number: {task_num}")
            results.append(False)
            continue

        task_name, task_func = task_functions[task_num]

        print(f"\n🎯 Starting Task {task_num}: {task_name}")
        print("-" * 50)

        try:
            success = task_func(config)
            results.append(success)

            if success:
                print(f"✅ Task {task_num} completed successfully!")
            else:
                print(f"❌ Task {task_num} failed!")

        except Exception as e:
            print(f"❌ Task {task_num} failed with exception: {e}")
            logging.exception(f"Task {task_num} execution failed")
            results.append(False)

    # Print summary
    print("\n" + "=" * 70)
    print("� EXECUTION SUMMARY")
    print("=" * 70)

    for i, task_num in enumerate(task_list):
        task_name = task_functions[task_num][0] if task_num in task_functions else f"Unknown Task {task_num}"
        status = "✅ SUCCESS" if results[i] else "❌ FAILED"
        print(f"Task {task_num}: {task_name} - {status}")

    total_success = sum(results)
    total_tasks = len(task_list)
    print(f"\nOverall: {total_success}/{total_tasks} tasks completed successfully")

    if all(results):
        print("🎉 All tasks completed successfully!")
        return True
    else:
        print("⚠️  Some tasks failed - check the output above for details.")
        return False


def main():
    """Main script entry point."""
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Set up logging with specified level
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Parse task list
    try:
        task_list = [int(x.strip()) for x in args.task.split(",")]
    except ValueError:
        print("❌ Invalid task list format. Use comma-separated numbers, no spaces (e.g., '1,2,3')")
        parser.print_help()
        sys.exit(1)

    # Validate task numbers
    valid_tasks = {1, 2, 3}
    invalid_tasks = set(task_list) - valid_tasks
    if invalid_tasks:
        print(f"❌ Invalid task numbers: {', '.join(map(str, invalid_tasks))}")
        print(f"Valid tasks are: {', '.join(map(str, sorted(valid_tasks)))}")
        sys.exit(1)

    # Create configuration
    config = FirewallConfig(
        ip_address=args.firewall_ip,
        username=args.username,
        password=args.password,
        expert_password=args.expert_password,
        logging_level=args.log_level,
        timeout=args.timeout,
        read_timeout=args.read_timeout,
    )

    # Run tasks
    try:
        success = run_tasks(config, task_list)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n👋 Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.exception("Unexpected error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()
