"""Command execution and response handling for Check Point firewalls."""

import logging

# import re
# import socket
# import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import paramiko


class FirewallMode(Enum):
    """Enumeration of firewall modes."""

    CLISH = "clish"
    EXPERT = "expert"
    UNKNOWN = "unknown"


@dataclass
class CommandResponse:
    """Response structure for command execution."""

    command: str
    output: str
    success: bool
    error_message: Optional[str] = None
    mode: FirewallMode = FirewallMode.UNKNOWN


class CommandExecutor:
    """Executes commands and handles responses for Check Point firewalls."""

    def __init__(self, shell: paramiko.Channel, logger: logging.Logger):
        """Initialize command executor.

        Args:
            shell: Active SSH shell channel
            logger: Logger instance for debugging
        """
        self.shell = shell
        self.logger = logger
        self.current_mode = FirewallMode.UNKNOWN

        # Common prompt patterns for Check Point firewalls
        self.clish_prompt_patterns = [
            r"[\w\-]+>\s*$",  # Standard clish prompt: gw-123456>
            r"[\w\-]+>\s*\r?\n?$",  # With potential newlines
        ]

        self.expert_prompt_patterns = [
            r"\[Expert@[\w\-]+:\d+\]#\s*$",  # Expert mode: [Expert@gw-123456:0]#
            r"\[Expert@[\w\-]+:\d+\]#\s*\r?\n?$",  # With potential newlines
        ]

        # Timeout for command execution
        self.default_timeout = 10

    # def send_command(self, command: str, timeout: Optional[int] = None,
    #                 expected_prompts: Optional[List[str]] = None) -> CommandResponse:
    #     """Send command and capture response.

    #     Args:
    #         command: Command to execute
    #         timeout: Command timeout in seconds (uses default if None)
    #         expected_prompts: List of expected prompt patterns to wait for

    #     Returns:
    #         CommandResponse object with command results
    #     """
    #     if timeout is None:
    #         timeout = self.default_timeout

    #     self.logger.debug(f"Executing command: {command}")

    #     try:
    #         # Send command
    #         self.shell.send(command + '\n')

    #         # Wait for response
    #         output = self._read_until_prompt(timeout, expected_prompts)

    #         # Detect current mode from the output
    #         detected_mode = self.detect_mode(output)
    #         if detected_mode != FirewallMode.UNKNOWN:
    #             self.current_mode = detected_mode

    #         # Check for common error indicators
    #         success, error_message = self._analyze_response(output)

    #         response = CommandResponse(
    #             command=command,
    #             output=output,
    #             success=success,
    #             error_message=error_message,
    #             mode=self.current_mode
    #         )

    #         self.logger.debug(f"Command response - Success: {success}, Mode: {self.current_mode.value}")
    #         if not success and error_message:
    #             self.logger.warning(f"Command failed: {error_message}")

    #         return response

    #     except socket.timeout:
    #         error_msg = f"Command '{command}' timed out after {timeout} seconds"
    #         self.logger.error(error_msg)
    #         return CommandResponse(
    #             command=command,
    #             output="",
    #             success=False,
    #             error_message=error_msg,
    #             mode=self.current_mode
    #         )
    #     except Exception as e:
    #         error_msg = f"Error executing command '{command}': {str(e)}"
    #         self.logger.error(error_msg)
    #         return CommandResponse(
    #             command=command,
    #             output="",
    #             success=False,
    #             error_message=error_msg,
    #             mode=self.current_mode
    #         )

    # def send_input(self, input_text: str, timeout: Optional[int] = None) -> str:
    #     """Send input to an interactive prompt (like password entry).

    #     Args:
    #         input_text: Text to send as input
    #         timeout: Timeout for reading response

    #     Returns:
    #         Response output as string
    #     """
    #     if timeout is None:
    #         timeout = self.default_timeout

    #     self.logger.debug(f"Sending input (length: {len(input_text)})")

    #     try:
    #         # Send input without logging the actual content (could be password)
    #         self.shell.send(input_text + '\n')

    #         # Wait for response
    #         output = self._read_until_prompt(timeout)

    #         # Update mode detection after input
    #         detected_mode = self.detect_mode(output)
    #         if detected_mode != FirewallMode.UNKNOWN:
    #             self.current_mode = detected_mode
    #             self.logger.debug(f"Mode updated to: {self.current_mode.value}")

    #         return output

    #     except Exception as e:
    #         self.logger.error(f"Error sending input: {e}")
    #         return ""

    # def _read_until_prompt(self, timeout: int,
    #                       expected_prompts: Optional[List[str]] = None) -> str:
    #     """Read output until a prompt is detected.

    #     Args:
    #         timeout: Maximum time to wait for prompt
    #         expected_prompts: Additional prompt patterns to look for

    #     Returns:
    #         Complete command output as string
    #     """
    #     output = ""
    #     start_time = time.time()

    #     # Combine default prompts with any expected prompts
    #     all_patterns = (self.clish_prompt_patterns + self.expert_prompt_patterns +
    #                    (expected_prompts or []))

    #     while time.time() - start_time < timeout:
    #         if self.shell.recv_ready():
    #             try:
    #                 chunk = self.shell.recv(1024).decode('utf-8', errors='ignore')
    #                 output += chunk

    #                 # Check if we've received a complete prompt
    #                 if self._has_prompt(output, all_patterns):
    #                     break

    #             except socket.timeout:
    #                 break
    #             except Exception as e:
    #                 self.logger.debug(f"Error reading from shell: {e}")
    #                 break
    #         else:
    #             time.sleep(0.1)

    #     return output.strip()

    # def _has_prompt(self, text: str, patterns: List[str]) -> bool:
    #     """Check if text contains any of the prompt patterns.

    #     Args:
    #         text: Text to check for prompts
    #         patterns: List of regex patterns to match

    #     Returns:
    #         True if any prompt pattern is found
    #     """
    #     # Split text into lines and check the last few lines for prompts
    #     lines = text.split('\n')

    #     # Check last 3 lines for prompt patterns (to handle multi-line responses)
    #     for line in lines[-3:]:
    #         line = line.strip()
    #         if line:  # Skip empty lines
    #             for pattern in patterns:
    #                 if re.search(pattern, line):
    #                     return True

    #     return False

    # def detect_mode(self, output: str = None) -> FirewallMode:
    #     """Detect current firewall mode from output or by sending a test command.

    #     Args:
    #         output: Optional output text to analyze for mode detection

    #     Returns:
    #         Detected firewall mode
    #     """
    #     if output:
    #         # Analyze provided output for mode indicators
    #         if self._has_prompt(output, self.expert_prompt_patterns):
    #             return FirewallMode.EXPERT
    #         elif self._has_prompt(output, self.clish_prompt_patterns):
    #             return FirewallMode.CLISH

    #     # If no output provided or mode not detected, send a test command
    #     try:
    #         # Send a simple command that works in both modes
    #         self.shell.send('\n')
    #         time.sleep(0.5)

    #         if self.shell.recv_ready():
    #             response = self.shell.recv(1024).decode('utf-8', errors='ignore')

    #             if self._has_prompt(response, self.expert_prompt_patterns):
    #                 return FirewallMode.EXPERT
    #             elif self._has_prompt(response, self.clish_prompt_patterns):
    #                 return FirewallMode.CLISH

    #     except Exception as e:
    #         self.logger.debug(f"Error detecting mode: {e}")

    #     return FirewallMode.UNKNOWN

    # def _analyze_response(self, output: str) -> Tuple[bool, Optional[str]]:
    #     """Analyze command response for success/failure indicators.

    #     Args:
    #         output: Command output to analyze

    #     Returns:
    #         Tuple of (success, error_message)
    #     """
    #     # Common Check Point error patterns
    #     error_patterns = [
    #         r'CLINFR\d+\s+(.+)',  # Check Point CLI error codes
    #         r'Error:\s*(.+)',
    #         r'Failed:\s*(.+)',
    #         r'Invalid\s+(.+)',
    #         r'command not found',
    #         r'Permission denied',
    #         r'Access denied',
    #     ]

    #     # Check for error patterns
    #     for pattern in error_patterns:
    #         match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
    #         if match:
    #             error_message = match.group(1) if match.groups() else match.group(0)
    #             return False, error_message.strip()

    #     # If no errors found, consider it successful
    #     return True, None

    # def wait_for_prompt(self, expected_prompt: str, timeout: int = 30) -> bool:
    #     """Wait for a specific prompt pattern.

    #     Args:
    #         expected_prompt: Regex pattern for expected prompt
    #         timeout: Maximum time to wait

    #     Returns:
    #         True if prompt detected within timeout
    #     """
    #     start_time = time.time()

    #     while time.time() - start_time < timeout:
    #         if self.shell.recv_ready():
    #             try:
    #                 output = self.shell.recv(1024).decode('utf-8', errors='ignore')
    #                 if re.search(expected_prompt, output):
    #                     return True
    #             except Exception as e:
    #                 self.logger.debug(f"Error waiting for prompt: {e}")
    #                 break
    #         time.sleep(0.1)

    #     return False

    # def get_current_mode(self) -> FirewallMode:
    #     """Get the currently detected firewall mode.

    #     Returns:
    #         Current firewall mode
    #     """
    #     return self.current_mode

    # def set_timeout(self, timeout: int) -> None:
    #     """Set default timeout for command execution.

    #     Args:
    #         timeout: New default timeout in seconds
    #     """
    #     self.default_timeout = timeout
    #     self.logger.debug(f"Default command timeout set to {timeout} seconds")
