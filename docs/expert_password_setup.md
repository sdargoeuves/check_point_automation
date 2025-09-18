# Expert Password Setup

This document describes the expert password setup functionality implemented in the Check Point VM automation framework.

## Overview

The expert password setup functionality allows automated configuration of the expert password on fresh Check Point VM installations. This is a critical first step in the Check Point VM initialization process, as the expert password is required for advanced configuration operations.

## Features

- **Password Strength Validation**: Enforces Check Point password policy requirements
- **Interactive Prompt Handling**: Automatically handles CLI password prompts
- **Verification**: Confirms password was set correctly by testing expert mode access
- **Error Handling**: Comprehensive error handling with detailed error messages
- **Idempotency**: Safe to run multiple times without side effects

## Password Requirements

The expert password must meet the following criteria:

- Minimum 8 characters in length
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one digit (0-9)
- At least one special character (!@#$%^&*()_+-=[]{}|;':"\\,.<>?)

## Usage

### Basic Usage

```python
from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.connection import CheckPointConnectionManager
from checkpoint_automation.core.models import ConnectionInfo

# Create connection manager
connection_info = ConnectionInfo(
    host="192.168.1.100",
    username="admin",
    password="admin"  # Default password for fresh installation
)

connection_manager = CheckPointConnectionManager()
connection_manager.connect(connection_info)

# Create initial setup module
initial_setup = InitialSetupModule(connection_manager)

# Set expert password
expert_password = "SecureExpert123!"
success = initial_setup.set_expert_password(expert_password)

if success:
    print("Expert password set successfully!")
else:
    print("Failed to set expert password")
```

### With Error Handling

```python
from checkpoint_automation.modules.initial_setup import InitialSetupModule
from checkpoint_automation.core.exceptions import ConfigurationError, ValidationError

try:
    # Validate configuration first
    config = {"expert_password": "SecureExpert123!"}
    if not initial_setup.validate_config(config):
        print("Password validation failed")
        return
    
    # Set expert password
    success = initial_setup.set_expert_password("SecureExpert123!")
    print("Expert password set successfully!")
    
except ValidationError as e:
    print(f"Password validation error: {e}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Prerequisites

Before setting the expert password, ensure:

1. **Connection Established**: SSH connection to the Check Point VM is active
2. **Fresh Installation**: VM is in fresh installation state (not already configured)
3. **CLI Access**: Able to access the Check Point CLI (clish mode)

## Implementation Details

### Password Validation

The `_validate_password_strength()` method uses regular expressions to validate password requirements:

```python
def _validate_password_strength(self, password: str) -> bool:
    """Validate password meets Check Point requirements."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
        return False
    return True
```

### Command Execution

The expert password setup process involves:

1. **Mode Verification**: Ensure CLI is in clish mode
2. **Command Execution**: Execute `set expert-password` command
3. **Interactive Handling**: Handle password and confirmation prompts
4. **Verification**: Test expert mode access with new password

### Error Handling

The implementation handles various error scenarios:

- **Connection Errors**: SSH connection issues
- **Authentication Errors**: Invalid credentials or password policy violations
- **Configuration Errors**: Command execution failures
- **Validation Errors**: Password strength or prerequisite validation failures

## Testing

### Unit Tests

Comprehensive unit tests cover:

- Password strength validation
- Command execution scenarios
- Error handling paths
- Interactive prompt handling

Run unit tests:

```bash
python -m pytest tests/unit/test_initial_setup.py -v
```

### Integration Tests

Integration tests demonstrate end-to-end functionality:

- Complete password setup workflow
- Error scenarios
- Configuration validation

Run integration tests:

```bash
python -m pytest tests/integration/test_initial_setup_integration.py -v
```

## Example Script

A complete example script is available at `examples/expert_password_setup.py`:

```bash
python examples/expert_password_setup.py
```

## API Reference

### InitialSetupModule.set_expert_password()

```python
def set_expert_password(self, password: str) -> bool:
    """
    Set expert password on fresh Check Point VM.
    
    Args:
        password: The expert password to set
        
    Returns:
        True if password was set successfully, False otherwise
        
    Raises:
        ConfigurationError: If password setting fails
        ValidationError: If password validation fails
        AuthenticationError: If authentication issues occur
    """
```

### InitialSetupModule.validate_config()

```python
def validate_config(self, config: Dict[str, Any]) -> bool:
    """
    Validate configuration before applying.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
```

### InitialSetupModule.validate_prerequisites()

```python
def validate_prerequisites(self) -> bool:
    """
    Validate that prerequisites for initial setup are met.
    
    Returns:
        True if prerequisites are met, False otherwise
    """
```

## Troubleshooting

### Common Issues

1. **Password Too Weak**: Ensure password meets all strength requirements
2. **Wrong VM State**: Only works on fresh installations, not configured systems
3. **Connection Issues**: Verify SSH connectivity and credentials
4. **CLI Mode Issues**: Ensure proper CLI mode switching

### Debug Logging

Enable debug logging for detailed troubleshooting:

```python
from checkpoint_automation.core.logging_config import setup_logging

setup_logging(log_level="DEBUG")
```

## Future Enhancements

The current implementation focuses on expert password setup. Future enhancements will include:

- First-time wizard automation (`run_first_time_wizard()`)
- Admin password updates (`update_admin_password()`)
- Setup verification (`verify_initial_setup()`)

These methods are currently marked as `NotImplementedError` and will be implemented in subsequent tasks.