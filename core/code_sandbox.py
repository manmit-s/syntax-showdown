import traceback
from typing import List, Dict, Tuple, Any

def run_test_cases(user_code: str, test_cases: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Execute user code against test cases in a sandboxed environment.
    
    Args:
        user_code: Python code submitted by user
        test_cases: List of test case dictionaries with 'input' and 'expected_output'
    
    Returns:
        Tuple of (results_list, passed_count)
        results_list: List of dictionaries with test results
        passed_count: Number of test cases that passed
    
    WARNING: Using exec() on untrusted code is unsafe for production.
    For production, use Docker containers or isolated environments.
    """
    results = []
    passed_count = 0
    
    exec_globals = {}
    
    try:
        # Execute the user's code
        exec(user_code, exec_globals)
        
        # Find the first callable function in the executed code
        function_candidates = [
            value
            for name, value in exec_globals.items()
            if callable(value) and not name.startswith("__")
        ]
        
        if not function_candidates:
            raise ValueError("No callable function was found in the submitted code.")
        
        # Use the first found function (assume it's the solve function)
        func = function_candidates[0]
        function_name = [
            name 
            for name, value in exec_globals.items() 
            if value is func and not name.startswith("__")
        ][0] if len(function_candidates) > 0 else "solve"
        
        # Run each test case
        for index, test_case in enumerate(test_cases):
            input_args = test_case.get("input", [])
            expected = test_case.get("expected_output")
            
            try:
                # Handle the input based on its type
                if isinstance(input_args, list):
                    # Unpack list arguments
                    actual = func(*input_args)
                elif isinstance(input_args, dict):
                    # Unpack dictionary arguments
                    actual = func(**input_args)
                else:
                    # Single argument
                    actual = func(input_args)
                
                # Compare actual and expected outputs
                # Note: We convert to string for comparison to handle different types
                is_pass = str(actual) == str(expected)
                
                if is_pass:
                    passed_count += 1
                
                results.append({
                    "Test Case": f"#{index + 1}",
                    "Input": str(input_args),
                    "Expected": str(expected),
                    "Output": str(actual),
                    "Status": "✅ Pass" if is_pass else "❌ Fail",
                })
                
            except Exception as test_error:
                # Test case execution failed
                results.append({
                    "Test Case": f"#{index + 1}",
                    "Input": str(input_args),
                    "Expected": str(expected),
                    "Output": f"Error: {str(test_error)}",
                    "Status": "❌ Runtime Error",
                })
        
    except SyntaxError as e:
        # Syntax error in user code
        results.append({
            "Test Case": "Syntax",
            "Input": "",
            "Expected": "",
            "Output": f"Syntax Error: {str(e)}",
            "Status": "❌ Syntax Error",
        })
        
    except ValueError as e:
        # No function found or other value error
        results.append({
            "Test Case": "Function",
            "Input": "",
            "Expected": "",
            "Output": f"Function Error: {str(e)}",
            "Status": "❌ Function Error",
        })
        
    except Exception as error:
        # General execution error
        error_details = traceback.format_exc()
        results.append({
            "Test Case": "Execution",
            "Input": "",
            "Expected": "",
            "Output": f"Execution Error: {str(error)}\n{error_details[:500]}",
            "Status": "❌ Execution Error",
        })
    
    return results, passed_count

def calculate_score(passed_count: int, total_test_cases: int, ai_bonus_score: int) -> int:
    """
    Calculate final score based on passed tests and AI bonus.
    
    Args:
        passed_count: Number of test cases passed
        total_test_cases: Total number of test cases
        ai_bonus_score: AI bonus score (0-10)
    
    Returns:
        Total score
    """
    if total_test_cases == 0:
        return 0
    
    test_score = int((passed_count / total_test_cases) * 100)
    return test_score + ai_bonus_score

def sanitize_code(user_code: str) -> str:
    """
    Basic code sanitization for safety.
    
    WARNING: This is minimal protection. In production, use proper sandboxing.
    """
    # Basic safety checks
    dangerous_imports = [
        "import os", "from os import", 
        "import sys", "from sys import",
        "import subprocess", "from subprocess import",
        "import socket", "from socket import",
        "eval(", "exec(",
        "__import__(", "compile(",
        "open(", "file(",
        "input(", "raw_input("
    ]
    
    user_code_lower = user_code.lower()
    
    for dangerous in dangerous_imports:
        if dangerous.lower() in user_code_lower:
            raise ValueError(f"Code contains potentially dangerous operation: {dangerous}")
    
    # Limit code length (basic protection)
    if len(user_code) > 10000:
        raise ValueError("Code exceeds maximum length (10,000 characters)")
    
    return user_code

def execute_solution(user_code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Full solution execution pipeline.
    
    Args:
        user_code: User's Python code
        test_cases: List of test cases
    
    Returns:
        Dictionary with execution results
    """
    try:
        # Sanitize code first
        sanitized_code = sanitize_code(user_code)
        
        # Run test cases
        results, passed_count = run_test_cases(sanitized_code, test_cases)
        
        return {
            "results": results,
            "passed_count": passed_count,
            "total_tests": len(test_cases),
            "success": True
        }
        
    except ValueError as e:
        return {
            "results": [{
                "Test Case": "Security",
                "Input": "",
                "Expected": "",
                "Output": str(e),
                "Status": "❌ Security Block"
            }],
            "passed_count": 0,
            "total_tests": len(test_cases),
            "success": False
        }
    except Exception as e:
        return {
            "results": [{
                "Test Case": "Error",
                "Input": "",
                "Expected": "",
                "Output": str(e),
                "Status": "❌ General Error"
            }],
            "passed_count": 0,
            "total_tests": len(test_cases),
            "success": False
        }

if __name__ == "__main__":
    # Test the module with a simple example
    test_code = """
def solve(numbers):
    return sum(numbers)
"""
    
    test_cases = [
        {"input": [[1, 2, 3]], "expected_output": 6},
        {"input": [[10, 20, 30]], "expected_output": 60},
        {"input": [[0, 0, 0]], "expected_output": 0}
    ]
    
    print("Code Sandbox Module - Testing interface")
    results, passed = run_test_cases(test_code, test_cases)
    
    print(f"Passed: {passed}/{len(test_cases)}")
    for result in results:
        print(result)
    
    score = calculate_score(passed, len(test_cases), 8)
    print(f"Score: {score}")
