# CheckPoint Automation

A Python library for automating Check Point firewall configuration and management tasks. This library provides a clean, programmatic interface for common firewall operations using SSH connectivity.

## Features

- 🔐 **Expert Password Management**: Automated setup and validation of expert passwords
- 👤 **User Management**: Create and configure firewall user accounts
- 📁 **File Transfer**: Secure binary file deployment to firewall systems
- 🔌 **SSH Connection Management**: Robust connection handling with automatic mode switching
- 📝 **Comprehensive Logging**: Detailed logging with configurable levels
- 🛡️ **Error Handling**: Graceful error handling and recovery

## Installation

### Prerequisites

- Python 3.10 or higher
- Network connectivity to Check Point firewall(s)
- Valid firewall credentials with appropriate permissions

### Install from PyPI (Coming Soon)

```bash
# Install the package from PyPI
pip install checkpoint-automation
```

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd checkpoint-automation

# Install the package (creates cp_automate command)
pip install -e .
```

### Using uv (Recommended)

```bash
# Install using uv for faster dependency resolution
uv pip install -e .
```

## Quick Start

### 🚀 CLI Tool (Recommended)

After installation, use the `cp_automate` command from anywhere:

> **Note**: The `cp_automate` command is available after running `pip install -e .` or installing from PyPI

```bash
# Set expert password (default task)
cp_automate 10.194.59.200

# Run specific tasks with custom credentials
cp_automate 10.194.59.200 \
    --username admin \
    --password mypass \
    --expert-password myexpert \
    --task 1

# Run multiple tasks with debug logging
cp_automate 10.194.59.200 \
    --log-level DEBUG \
    --task 1,2 \
    --timeout 60

# Show help and available options
cp_automate --help
```

### Alternative Methods

If you haven't installed the package or prefer other methods:

```bash
# Run as Python module
python -m checkpoint_utils.cli 10.194.59.200 --task 1

# Legacy method (still works)
python checkpoint_main.py 10.194.59.200 --task 1
```

### Available Tasks

| Task | Description | Status |
|------|-------------|---------|
| 1 | Set Expert Password | ✅ Available |
| 2 | Configure Vagrant User | 🚧 Coming Soon |
| 3 | Copy Binary Files | 🚧 Coming Soon |

### Python API

```python
from checkpoint_utils import (
    FirewallConfig,
    SSHConnectionManager,
    ExpertPasswordManager
)

# Create firewall configuration
config = FirewallConfig(
    ip_address="10.194.59.200",
    username="admin",
    password="admin",
    expert_password="newexpertpass",
    timeout=30,
    read_timeout=10,
    last_read=1,
    logging_level="INFO"
)

# Connect and manage expert password
with SSHConnectionManager(config) as ssh_manager:
    expert_mgr = ExpertPasswordManager(ssh_manager)
    
    # Check if expert password is already set
    is_set, message = expert_mgr.is_expert_password_set()
    print(f"Expert password status: {message}")
    
    if not is_set:
        # Set the expert password
        success, result = expert_mgr.set_expert_password(config.expert_password)
        if success:
            print("Expert password set successfully!")
        else:
            print(f"Failed to set expert password: {result}")
```

## Configuration

### FirewallConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ip_address` | str | Required | Firewall IP address |
| `username` | str | Required | Admin username |
| `password` | str | Required | Admin password |
| `expert_password` | str | Required | Expert mode password (min 6 chars) |
| `timeout` | int | 15 | Connection timeout in seconds |
| `read_timeout` | int | 5 | Read timeout for connection checks |
| `last_read` | int | 1 | Last read timeout |
| `logging_level` | str | "WARNING" | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Logging

The library automatically creates log files in the `logs/` directory with the naming pattern:

```text
logs/checkpoint_{ip_with_underscores}.log
```

Example: `logs/checkpoint_10_194_59_200.log`

You can control logging verbosity using the `logging_level` parameter or `--log-level` CLI flag.

## API Reference

### Core Classes

#### SSHConnectionManager

Manages SSH connections to Check Point firewalls using netmiko.

```python
class SSHConnectionManager:
    def __init__(self, config: FirewallConfig)
    def connect(self) -> bool
    def disconnect(self) -> None
    def execute_command(self, command: str) -> CommandResponse
    def get_current_mode(self) -> FirewallMode
    def enter_expert_mode(self) -> bool
    def exit_expert_mode(self) -> bool
```

#### ExpertPasswordManager

Manages expert password operations.

```python
class ExpertPasswordManager:
    def __init__(self, ssh_manager: SSHConnectionManager)
    def is_expert_password_set(self) -> Tuple[bool, str]
    def set_expert_password(self, password: str) -> Tuple[bool, str]
    def validate_expert_password(self, password: str) -> Tuple[bool, str]
```

#### CommandExecutor

Low-level command execution with mode awareness.

```python
class CommandExecutor:
    def execute_command(self, command: str) -> CommandResponse
    def execute_clish_command(self, command: str) -> CommandResponse
    def execute_expert_command(self, command: str) -> CommandResponse
```

### Data Types

#### CommandResponse

```python
@dataclass
class CommandResponse:
    command: str
    output: str
    error_message: str
    success: bool
    execution_time: float
```

#### FirewallMode

```python
class FirewallMode(Enum):
    CLISH = "clish"
    EXPERT = "expert" 
    UNKNOWN = "unknown"
```

## Examples

### Example 1: Basic Expert Password Setup

```python
from checkpoint_utils import FirewallConfig, SSHConnectionManager, ExpertPasswordManager

config = FirewallConfig(
    ip_address="192.168.1.100",
    username="admin",
    password="admin",
    expert_password="secure123",
    logging_level="INFO"
)

with SSHConnectionManager(config) as ssh:
    expert_mgr = ExpertPasswordManager(ssh)
    success, message = expert_mgr.set_expert_password(config.expert_password)
    print(f"Result: {message}")
```

### Example 2: Command Line with Custom Settings

```bash
# Connect with extended timeouts for slower networks
cp_automate 10.194.59.200 \
    --timeout 120 \
    --read-timeout 30 \
    --expert-password "MySecurePassword123" \
    --log-level INFO
```

### Example 3: Error Handling

```python
from checkpoint_utils import FirewallConfig, SSHConnectionManager
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException

config = FirewallConfig(
    ip_address="10.194.59.200",
    username="admin", 
    password="admin",
    expert_password="newpass",
    timeout=30,
    logging_level="DEBUG"
)

try:
    with SSHConnectionManager(config) as ssh:
        # Your automation tasks here
        response = ssh.execute_command("show version all")
        print(response.output)
        
except NetMikoTimeoutException:
    print("Connection timed out - check network connectivity")
except NetMikoAuthenticationException:
    print("Authentication failed - check credentials")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Development

### Project Structure

```text
checkpoint-automation/
├── checkpoint_main.py          # Legacy CLI script
├── checkpoint_utils/           # Core library modules
│   ├── __init__.py            # Package exports
│   ├── cli.py                 # Modern CLI entry point (cp_automate)
│   ├── config.py              # Configuration management
│   ├── ssh_connection.py      # SSH connection handling  
│   ├── command_executor.py    # Command execution
│   ├── expert_password.py     # Expert password management
│   ├── user_management.py     # User account management
│   └── tasks.py               # High-level task functions
├── logs/                      # Automatic log file directory
├── pyproject.toml            # Modern Python packaging
├── requirements.txt          # Dependencies
└── uv.lock                   # Dependency lock file
```

### Dependencies

- **netmiko** (≥4.6.0): Network device SSH connectivity
- **Python** (≥3.10): Core runtime

### Code Quality

The project uses several tools for code quality:

- **Ruff**: Fast Python linter and formatter
- **Type hints**: Full type annotation support
- **Docstrings**: Comprehensive API documentation

## Troubleshooting

### Common Issues

#### Connection Timeout

```bash
# Increase timeout values for slow networks
cp_automate 10.194.59.200 --timeout 120 --read-timeout 30
```

#### Authentication Errors

- Verify firewall credentials are correct
- Check if the admin user has appropriate permissions
- Ensure the firewall is accessible on the management interface

#### Expert Password Issues

- Expert passwords must be at least 6 characters
- Check if expert password is already set: use `--log-level DEBUG`
- Verify the current expert password if one exists

#### SSH Connection Problems

- Verify SSH is enabled on the firewall management interface
- Check firewall management access rules
- Test basic SSH connectivity: `ssh admin@<firewall_ip>`

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
cp_automate 10.194.59.200 --log-level DEBUG
```

This will show:

- Detailed SSH connection steps
- All commands sent to the firewall
- Response parsing and mode detection
- Error details and stack traces

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or contributions:

1. Check existing issues in the repository
2. Create a new issue with detailed information
3. Include log output when reporting problems
4. Specify firewall model and software version when relevant

---

**Note**: This library is designed for Check Point Gaia-based firewalls. Always test in a non-production environment first and ensure you have proper backups before making configuration changes.
