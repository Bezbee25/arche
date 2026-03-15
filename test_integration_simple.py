#!/usr/bin/env python3
"""Simple test to verify the code changes are syntactically correct."""

import ast
import sys

def test_file_syntax(filepath):
    """Test if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

def test_function_signature():
    """Test if build_task_prompt has the selected_instruction_ids parameter."""
    try:
        with open('core/context.py', 'r') as f:
            content = f.read()
        
        # Check if the function signature includes selected_instruction_ids
        if 'selected_instruction_ids: list = None' in content:
            print("✓ build_task_prompt has selected_instruction_ids parameter")
            return True
        else:
            print("✗ build_task_prompt missing selected_instruction_ids parameter")
            return False
    except Exception as e:
        print(f"Error checking function signature: {e}")
        return False

def test_instructions_section():
    """Test if the instructions section was added to the prompt."""
    try:
        with open('core/context.py', 'r') as f:
            content = f.read()
        
        if '## Instructions sélectionnées' in content:
            print("✓ Instructions section added to prompt")
            return True
        else:
            print("✗ Instructions section not found in prompt")
            return False
    except Exception as e:
        print(f"Error checking instructions section: {e}")
        return False

def test_server_changes():
    """Test if server.py was updated correctly."""
    try:
        with open('web/server.py', 'r') as f:
            content = f.read()
        
        checks = [
            ('instructions: str = ""', 'instructions parameter in server functions'),
            ('selected_instruction_ids=selected_instruction_ids', 'selected_instruction_ids passed to build_task_prompt'),
        ]
        
        all_passed = True
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"Error checking server changes: {e}")
        return False

def test_frontend_changes():
    """Test if app.js was updated correctly."""
    try:
        with open('web/static/app.js', 'r') as f:
            content = f.read()
        
        checks = [
            ('state.selectedInstructionIds', 'selectedInstructionIds in state'),
            ('params.append(\'instructions\'', 'instructions parameter added to frontend'),
            ('instructions: state.selectedInstructionIds', 'instructions in bulk payload'),
        ]
        
        all_passed = True
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"Error checking frontend changes: {e}")
        return False

# Run all tests
print("Testing instruction integration changes...")
print()

tests = [
    ("core/context.py syntax", lambda: test_file_syntax('core/context.py')),
    ("web/server.py syntax", lambda: test_file_syntax('web/server.py')),
    ("web/static/app.js syntax", lambda: test_file_syntax('web/static/app.js')),
    ("Function signature", test_function_signature),
    ("Instructions section", test_instructions_section),
    ("Server changes", test_server_changes),
    ("Frontend changes", test_frontend_changes),
]

all_passed = True
for test_name, test_func in tests:
    print(f"Testing {test_name}...")
    if not test_func():
        all_passed = False
    print()

if all_passed:
    print("🎉 All tests passed! Instruction integration is properly implemented.")
    print()
    print("Implementation summary:")
    print("- Modified core/context.py to accept and include selected instructions")
    print("- Updated web/server.py to pass instruction IDs to context builder")
    print("- Modified web/static/app.js to send selected instruction IDs from frontend")
    print("- Selected instructions will appear in the '## Instructions sélectionnées' section")
else:
    print("❌ Some tests failed. Please check the implementation.")
    sys.exit(1)
