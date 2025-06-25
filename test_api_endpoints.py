import requests
import json

def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=10)
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
            return True
        else:
            print(f"Health endpoint failed: {response.text}")
            return False
    except Exception as e:
        print(f"Health endpoint error: {str(e)}")
        return False

def test_verification_stats_endpoint():
    """Test the verification stats endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/registration/verification/stats", timeout=10)
        print(f"Verification stats endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Verification stats response: {response.json()}")
            return True
        else:
            print(f"Verification stats endpoint failed: {response.text}")
            return False
    except Exception as e:
        print(f"Verification stats endpoint error: {str(e)}")
        return False

def test_workflow_endpoint():
    """Test the workflow endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/registration/workflow", timeout=10)
        print(f"Workflow endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Workflow response: {response.json()}")
            return True
        else:
            print(f"Workflow endpoint failed: {response.text}")
            return False
    except Exception as e:
        print(f"Workflow endpoint error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing API endpoints...")
    print("=" * 50)
    
    # Test endpoints
    health_ok = test_health_endpoint()
    print("-" * 30)
    
    verification_ok = test_verification_stats_endpoint()
    print("-" * 30)
    
    workflow_ok = test_workflow_endpoint()
    print("-" * 30)
    
    # Summary
    print("\nTest Summary:")
    print(f"Health endpoint: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Verification stats: {'✓ PASS' if verification_ok else '✗ FAIL'}")
    print(f"Workflow endpoint: {'✓ PASS' if workflow_ok else '✗ FAIL'}")
    
    if all([health_ok, verification_ok, workflow_ok]):
        print("\n🎉 All API endpoints are working correctly!")
    else:
        print("\n⚠️ Some API endpoints have issues that need to be addressed.")