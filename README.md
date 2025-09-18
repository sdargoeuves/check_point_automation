# Check Point VM Automation

A comprehensive automation framework for Check Point VM appliances, providing automated initial setup, network configuration, and security policy management. Starting from a fresh install, all the way to a fully ready and functional FW.

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

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install it first:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

Then set up the project:

```bash
# Clone the repository
git clone <repository-url>
cd checkpoint-vm-automation

# Create virtual environment and install dependencies
uv sync

# Install with optional dependencies (choose what you need)
uv sync --extra nornir      # For Nornir backend
uv sync --extra ansible     # For Ansible backend  
uv sync --extra dev         # For development tools
uv sync --extra all         # Install everything

# Activate the virtual environment
source .venv/bin/activate   # On macOS/Linux
# or
.venv\Scripts\activate      # On Windows
```

### Using pip (Alternative)

```bash
# Clone the repository
git clone <repository-url>
cd checkpoint-vm-automation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # On macOS/Linux
# or
.venv\Scripts\activate      # On Windows

# Install the package with dependencies
pip install -e .

# Install optional dependencies as needed
pip install -e ".[nornir]"    # For Nornir backend
pip install -e ".[ansible]"   # For Ansible backend
pip install -e ".[dev]"       # For development tools
pip install -e ".[all]"       # Install everything
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

### Setup Development Environment

```bash
# Install with development dependencies
uv sync --extra dev

# Or if using pip
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run unit tests
uv run pytest tests/unit/

# Run integration tests (requires Check Point VM)
uv run pytest tests/integration/

# Run all tests with coverage
uv run pytest --cov=checkpoint_automation

# Or if using activated venv
pytest tests/unit/
pytest --cov=checkpoint_automation
```

### Code Quality

```bash
# Format code (ruff replaces black)
uv run ruff format checkpoint_automation/ tests/

# Lint code  
uv run ruff check checkpoint_automation/ tests/

# Fix linting issues automatically
uv run ruff check --fix checkpoint_automation/ tests/

# Type checking
uv run mypy checkpoint_automation/

# Run all code quality checks
uv run ruff format checkpoint_automation/ tests/
uv run ruff check --fix checkpoint_automation/ tests/
uv run mypy checkpoint_automation/

# Or if using activated venv
ruff format checkpoint_automation/ tests/
ruff check checkpoint_automation/ tests/
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