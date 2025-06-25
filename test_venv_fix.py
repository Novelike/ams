#!/usr/bin/env python3
"""
Test script to verify the virtual environment fix
Simulates the deployment process to ensure venv creation works correctly
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path

def log_info(message):
    print(f"🔍 [INFO] {message}")

def log_success(message):
    print(f"✅ [SUCCESS] {message}")

def log_error(message):
    print(f"❌ [ERROR] {message}")

def test_venv_creation_logic():
    """Test the virtual environment creation logic"""
    log_info("Testing virtual environment creation logic...")
    
    # Create a temporary directory to simulate the deployment environment
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        log_info(f"Working in temporary directory: {temp_dir}")
        
        # Create a simple requirements.txt for testing
        with open("requirements.txt", "w") as f:
            f.write("requests==2.31.0\n")
        
        # Test the venv creation logic (similar to what's in the workflow)
        test_script = """
#!/bin/bash
set -e

echo "🚀 Testing venv creation logic..."

# 1. Check and create venv if it doesn't exist
if [ ! -d "venv" ]; then
  echo "📦 가상환경 생성 중..."
  python3 -m venv venv
fi

# 2. Activate venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify installation
python -c "import requests; print('✅ Dependencies installed successfully')"

echo "🎉 Test completed successfully!"
"""
        
        # Write the test script
        with open("test_venv.sh", "w") as f:
            f.write(test_script)
        
        # Make it executable
        os.chmod("test_venv.sh", 0o755)
        
        # Run the test script
        try:
            result = subprocess.run(["bash", "test_venv.sh"], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                log_success("Virtual environment creation test passed")
                log_info("Script output:")
                print(result.stdout)
                return True
            else:
                log_error("Virtual environment creation test failed")
                log_error("Error output:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            log_error("Test timed out")
            return False
        except Exception as e:
            log_error(f"Test failed with exception: {e}")
            return False

def test_workflow_syntax():
    """Test if the GitHub Actions workflow has valid syntax"""
    log_info("Testing GitHub Actions workflow syntax...")
    
    workflow_path = ".github/workflows/backend-optimized-deploy.yml"
    if not os.path.exists(workflow_path):
        log_error(f"Workflow file not found: {workflow_path}")
        return False
    
    try:
        import yaml
        with open(workflow_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        log_success("Workflow YAML syntax is valid")
        return True
    except ImportError:
        log_info("PyYAML not available, skipping YAML syntax check")
        return True
    except yaml.YAMLError as e:
        log_error(f"YAML syntax error: {e}")
        return False

def test_deployment_script_syntax():
    """Test if the deployment script has valid bash syntax"""
    log_info("Testing deployment script syntax...")
    
    script_path = "deployment/backend_deploy.sh"
    if not os.path.exists(script_path):
        log_error(f"Deployment script not found: {script_path}")
        return False
    
    try:
        # Use bash -n to check syntax without executing
        result = subprocess.run(["bash", "-n", script_path], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            log_success("Deployment script syntax is valid")
            return True
        else:
            log_error("Deployment script syntax error:")
            print(result.stderr)
            return False
            
    except Exception as e:
        log_error(f"Failed to check script syntax: {e}")
        return False

def check_venv_logic_in_files():
    """Check if the venv creation logic is present in both files"""
    log_info("Checking virtual environment logic in files...")
    
    files_to_check = [
        (".github/workflows/backend-optimized-deploy.yml", [
            "if [ ! -d \"venv\" ]; then",
            "python3 -m venv venv"
        ]),
        ("deployment/backend_deploy.sh", [
            "if [ ! -d \"venv\" ]; then",
            "python3 -m venv venv"
        ])
    ]
    
    all_checks_passed = True
    
    for file_path, required_patterns in files_to_check:
        if not os.path.exists(file_path):
            log_error(f"File not found: {file_path}")
            all_checks_passed = False
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in required_patterns:
            if pattern in content:
                log_success(f"Found required pattern in {file_path}: {pattern}")
            else:
                log_error(f"Missing required pattern in {file_path}: {pattern}")
                all_checks_passed = False
    
    return all_checks_passed

def main():
    """Main test function"""
    print("🚀 Testing Virtual Environment Fix")
    print("=" * 60)
    
    tests = [
        ("File Logic Check", check_venv_logic_in_files),
        ("Workflow Syntax", test_workflow_syntax),
        ("Script Syntax", test_deployment_script_syntax),
        ("Venv Creation Logic", test_venv_creation_logic)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running test: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed_tests += 1
                log_success(f"Test passed: {test_name}")
            else:
                log_error(f"Test failed: {test_name}")
        except Exception as e:
            log_error(f"Test error in {test_name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        log_success("All tests passed! Virtual environment fix is working correctly.")
    else:
        log_error(f"{total_tests - passed_tests} tests failed. Please review the issues.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)