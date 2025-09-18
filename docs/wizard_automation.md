# Check Point First-Time Wizard Automation

This document describes the first-time wizard automation functionality implemented in the Check Point VM automation system.

## Overview

The wizard automation feature automates the initial configuration of fresh Check Point VM appliances through the first-time wizard process. This eliminates the need for manual configuration through the web interface and enables consistent, repeatable deployments.

## Features

### Core Functionality

- **Automated Configuration Generation**: Creates Check Point configuration files based on provided parameters
- **Validation**: Validates configuration before application using dry-run mode
- **Error Handling**: Comprehensive error handling with detailed logging
- **Idempotency**: Safe to run multiple times without causing issues
- **Password Management**: Handles admin and maintenance password hashing automatically

### Supported Configuration Options

- **System Identity**: Hostname, domain name, timezone
- **Network Settings**: DNS servers, NTP servers
- **Security**: Admin password management, maintenance password
- **Installation Type**: Security Gateway with Management (standalone)
- **User Center**: Data sharing preferences

## Usage

### Basic Example

```python
from checkpoint_automation.core.models import WizardConfig
from checkpoint_automation.modules.initial_setup import InitialSetupModule

# Create wizard configuration
wizard_config = WizardConfig(
    hostname="cp-gateway-01",
    timezone="America/New_York",
    ntp_servers=["pool.ntp.org", "time.nist.gov"],
    dns_servers=["8.8.8.8", "8.8.4.4"],
    domain_name="example.com"
)

# Initialize setup module (assumes connection manager is configured)
initial_setup = InitialSetupModule(connection_manager)

# Run wizard automation
success = initial_setup.run_first_time_wizard(wizard_config)
```

### Configuration Parameters

#### WizardConfig Class

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hostname` | str | Yes | System hostname |
| `timezone` | str | No | System timezone (default: UTC) |
| `ntp_servers` | List[str] | No | NTP server addresses |
| `dns_servers` | List[str] | No | DNS server IP addresses |
| `domain_name` | str | No | Domain name |

#### Example Configurations

**Minimal Configuration:**
```python
wizard_config = WizardConfig(hostname="checkpoint-gw")
```

**Full Configuration:**
```python
wizard_config = WizardConfig(
    hostname="cp-gateway-prod",
    timezone="Europe/London",
    ntp_servers=["ntp1.company.com", "ntp2.company.com"],
    dns_servers=["10.0.0.10", "10.0.0.11", "8.8.8.8"],
    domain_name="company.com"
)
```

## Implementation Details

### Configuration File Generation

The wizard automation generates a Check Point configuration file with the following structure:

```ini
# Install Security Gateway and Management
install_security_gw=true
install_security_managment=true
install_mgmt_primary=true

# System identification
hostname=cp-gateway-01
domainname=example.com
timezone='America/New_York'

# Network services
ntp_primary=pool.ntp.org
ntp_secondary=time.nist.gov
primary=8.8.8.8
secondary=8.8.4.4

# Security settings
admin_hash='$6$salt$hashedpassword'
maintenance_hash='grub.pbkdf2.sha512.10000.hash'

# Additional settings...
```

### Process Flow

1. **Validation**: Validate input parameters and system prerequisites
2. **Configuration Generation**: Create configuration file content
3. **File Creation**: Write configuration to temporary file in expert mode
4. **Dry-Run Validation**: Validate configuration using `config_system --dry-run`
5. **Application**: Apply configuration using `config_system`
6. **Verification**: Verify wizard completion and system state
7. **Cleanup**: Remove temporary configuration file

### Error Handling

The system provides comprehensive error handling for common scenarios:

- **Connection Errors**: SSH connection failures, authentication issues
- **Validation Errors**: Invalid configuration parameters
- **Configuration Errors**: Failed configuration application
- **State Errors**: Unexpected system states

### Password Management

The system automatically handles password hashing:

- **Admin Password**: Retrieved from current system using `dbget passwd:admin:passwd`
- **Maintenance Password**: Generated using `grub2-mkpasswd-pbkdf2`

## Prerequisites

### System Requirements

- Fresh Check Point VM installation
- SSH access with default credentials (admin/admin)
- Expert password must be set before running wizard

### Network Requirements

- Management interface connectivity
- DNS resolution (if using hostnames for NTP/DNS servers)

## Validation

### Input Validation

- **Hostname**: RFC-compliant hostname format
- **IP Addresses**: Valid IPv4 format for DNS servers
- **Hostnames**: Valid hostname or FQDN format for NTP servers
- **Timezone**: Valid timezone identifier

### Configuration Validation

- Dry-run validation before application
- System state verification after completion
- Configuration file syntax validation

## Error Scenarios and Troubleshooting

### Common Issues

1. **Expert Mode Access Failure**
   - Ensure expert password is set
   - Verify SSH connectivity

2. **Configuration Validation Failure**
   - Check parameter formats
   - Verify DNS/NTP server accessibility

3. **Wizard Completion Verification Failure**
   - Allow additional time for system processing
   - Check system logs for errors

### Logging

The system provides detailed logging at multiple levels:

- **INFO**: General progress information
- **DEBUG**: Detailed operation information
- **WARNING**: Non-fatal issues
- **ERROR**: Fatal errors requiring attention

### Recovery

If wizard automation fails:

1. Check system state using `get_current_config()`
2. Review error logs for specific failure points
3. Manually complete configuration if needed
4. Reset system to fresh state if necessary

## Integration

### With Existing Workflows

The wizard automation integrates with the broader Check Point automation system:

- **Connection Manager**: Uses existing SSH connection management
- **State Detection**: Integrates with system state detection
- **Configuration Management**: Part of the overall configuration workflow

### Testing

Comprehensive test coverage includes:

- Unit tests for all validation functions
- Integration tests with mock Check Point systems
- Error scenario testing
- Configuration generation testing

## Security Considerations

- **Credential Management**: Secure handling of passwords and hashes
- **Temporary Files**: Secure creation and cleanup of configuration files
- **Logging**: Sensitive information is not logged
- **Access Control**: Requires appropriate system privileges

## Performance

- **Execution Time**: Typically 2-5 minutes depending on system performance
- **Resource Usage**: Minimal CPU and memory impact
- **Network Usage**: Limited to SSH communication and configuration transfer

## Future Enhancements

Potential improvements for future versions:

- Support for additional installation types (MDS, VSX)
- Advanced network configuration options
- Integration with external configuration management systems
- Enhanced validation and error recovery