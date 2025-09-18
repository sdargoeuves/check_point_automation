#!/usr/bin/env python3
"""
Test script for command execution functionality.
This script tests the command executor without requiring an actual firewall connection.
"""

import sys
import os

# Add the checkpoint_automation module to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checkpoint_automation import FirewallConfig, CommandExecutor, CommandResponse, FirewallMode
import logging

def test_command_response_creation():
    """Test CommandResponse object creation."""
    print("Testing CommandResponse creation...")
    
    response = CommandResponse(
        command="show version all",
        output="Check Point Gaia R81.20",
        success=True,
        mode=FirewallMode.CLISH
    )
    
    assert response.command == "show version all"
    assert response.success == True
    assert response.mode == FirewallMode.CLISH
    print("✓ CommandResponse creation test passed")

def test_firewall_mode_enum():
    """Test FirewallMode enumeration."""
    print("Testing FirewallMode enum...")
    
    assert FirewallMode.CLISH.value == "clish"
    assert FirewallMode.EXPERT.value == "expert"
    assert FirewallMode.UNKNOWN.value == "unknown"
    print("✓ FirewallMode enum test passed")

def test_prompt_detection():
    """Test prompt detection patterns."""
    print("Testing prompt detection patterns...")
    
    # Create a mock logger
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    
    # We can't test the full CommandExecutor without a shell,
    # but we can test the pattern matching logic
    
    # Test clish prompt patterns
    clish_prompts = [
        "gw-123456>",
        "gw-test> ",
        "firewall-01>\n",
    ]
    
    expert_prompts = [
        "[Expert@gw-123456:0]#",
        "[Expert@firewall-01:0]# ",
        "[Expert@test:0]#\n",
    ]
    
    # These would be tested in the actual CommandExecutor
    # For now, just verify the patterns compile
    import re
    
    clish_pattern = r'[\w\-]+>\s*$'
    expert_pattern = r'\[Expert@[\w\-]+:\d+\]#\s*$'
    
    for prompt in clish_prompts:
        assert re.search(clish_pattern, prompt.strip()), f"Clish pattern failed for: {prompt}"
    
    for prompt in expert_prompts:
        assert re.search(expert_pattern, prompt.strip()), f"Expert pattern failed for: {prompt}"
    
    print("✓ Prompt detection pattern test passed")

def test_error_analysis():
    """Test error analysis patterns."""
    print("Testing error analysis patterns...")
    
    error_outputs = [
        "CLINFR0519  Configuration lock present. Can not execute this command.",
        "Error: Invalid command",
        "command not found",
        "Permission denied",
    ]
    
    success_outputs = [
        "gw-123456>",
        "Configuration saved successfully",
        "[Expert@gw-123456:0]#",
    ]
    
    # Test error pattern matching
    import re
    
    error_patterns = [
        r'CLINFR\d+\s+(.+)',
        r'Error:\s*(.+)',
        r'command not found',
        r'Permission denied',
    ]
    
    # Check that error outputs match error patterns
    for output in error_outputs:
        found_error = False
        for pattern in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                found_error = True
                break
        assert found_error, f"Error pattern not found in: {output}"
    
    # Check that success outputs don't match error patterns
    for output in success_outputs:
        found_error = False
        for pattern in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                found_error = True
                break
        assert not found_error, f"False positive error detected in: {output}"
    
    print("✓ Error analysis pattern test passed")

def main():
    """Run all tests."""
    print("Running command execution tests...\n")
    
    try:
        test_command_response_creation()
        test_firewall_mode_enum()
        test_prompt_detection()
        test_error_analysis()
        
        print("\n✅ All command execution tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())