# Check Point VM Automation

A comprehensive automation framework for Check Point VM appliances, providing automated initial setup, network configuration, and security policy management.

## Features

- **Initial Setup Automation**: Automate fresh Check Point VM setup including expert password creation and first-time wizard
- **Network Configuration**: Configure interfaces, OSPF routing, and LLDP
- **Security Policy Management**: Create network objects and firewall rules
- **Multiple Backends**: Support for direct SSH, Nornir, and Ansible automation
- **Idempotency**: Safe to run multiple times without duplicating configurations
- **Comprehensive Validation**: Verify configurations and system state

## Project Structure

```
checkpoint_automation/
├── checkpoint_automation/          # Main package
│   ├── core/                      # Core components
│   │   ├── __init__.py
│   │   ├── exceptions.py          # Exception classes
│   │   ├── interfaces.py          # Abstract interfaces
│   │   ├── logging_config.py      # Logging configuration
│   │   ├── models.py              # Data models
│   │   └── utils.py               # Utility functions
│   ├── modules/                   # Automation modules
│   │   └── __init__.py
│   ├── backends/                  # Automation backends
│   │   └── __init__.py
│   └── __init__.py
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── config/                        # Configuration files
│   └── checkpoint_config.yaml     # Configuration template
├── requirements.txt               # Python dependencies
├── setup.py                      # Package setup
└── README.md                     # This file
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd checkpoint-vm-automation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

Copy the configuration template and customize it for your environment:

```bash
cp config/checkpoint_config.yaml my_config.yaml
```

Edit `my_config.yaml` with your Check Point VM details, network configuration, and security policies.

## Usage

The framework provides both programmatic and CLI interfaces for automation tasks.

### Programmatic Usage

```python
from checkpoint_automation import CheckPointConfig
from checkpoint_automation.core.models import ConnectionInfo

# Load configuration
config = CheckPointConfig.from_yaml("my_config.yaml")

# Initialize automation
# (Implementation will be added in subsequent tasks)
```

### CLI Usage

```bash
# Run initial setup
checkpoint-automation setup --config my_config.yaml

# Configure networking
checkpoint-automation network --config my_config.yaml

# Apply security policy
checkpoint-automation policy --config my_config.yaml
```

## Development

### Running Tests

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires Check Point VM)
pytest tests/integration/

# Run all tests with coverage
pytest --cov=checkpoint_automation
```

### Code Quality

```bash
# Format code
black checkpoint_automation/ tests/

# Lint code
flake8 checkpoint_automation/ tests/

# Type checking
mypy checkpoint_automation/
```

## Requirements

- Python 3.8+
- SSH access to Check Point VM
- Check Point VM in fresh installation state (for initial setup)

## Supported Check Point Versions

- Check Point R81.x
- Check Point R80.x (limited support)

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Support

For issues and questions, please create an issue in the repository or contact the development team.