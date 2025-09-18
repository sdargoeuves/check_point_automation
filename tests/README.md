# Tests for Check Point Automation

This directory contains test files for the Check Point automation framework.

## Test Files

### `test_command_execution.py`
Unit tests for the command execution functionality:
- Tests CommandResponse object creation
- Tests FirewallMode enumeration
- Tests prompt detection patterns (regex validation)
- Tests error analysis patterns

### `test_integration.py`
Integration tests that verify components work together:
- Tests SSH manager integration with command executor
- Tests configuration validation
- Tests firewall mode detection logic
- Demonstrates usage patterns

## Running Tests

To run the tests, execute them from the project root directory:

```bash
# Run command execution tests
python tests/test_command_execution.py

# Run integration tests
python tests/test_integration.py

# Run all tests
python tests/test_command_execution.py && python tests/test_integration.py
```

## Test Coverage

These tests cover:
- ✅ Command execution and response handling
- ✅ Prompt detection using regex patterns
- ✅ Firewall mode detection (clish vs expert)
- ✅ Error analysis and response parsing
- ✅ Configuration validation
- ✅ SSH manager integration

## Notes

- These tests do not require an actual firewall connection
- They test the logic and patterns used by the command executor
- Integration tests verify that components are properly wired together
- All tests should pass before deploying the automation framework