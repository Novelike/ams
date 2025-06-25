import requests
import json

def reset_services():
    """Reset all services"""
    try:
        response = requests.post("http://localhost:8000/api/registration/services/reset", timeout=10)
        print(f"Service reset status: {response.status_code}")
        if response.status_code == 200:
            print(f"Reset response: {response.json()}")
            return True
        else:
            print(f"Service reset failed: {response.text}")
            return False
    except Exception as e:
        print(f"Service reset error: {str(e)}")
        return False

def test_verification_stats_endpoint():
    """Test the verification stats endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/registration/verification/stats", timeout=15)
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

if __name__ == "__main__":
    print("Testing API endpoints with service reset...")
    print("=" * 60)
    
    # First test health to make sure server is running
    health_ok = test_health_endpoint()
    print("-" * 40)
    
    if not health_ok:
        print("❌ Server is not running or health endpoint failed")
        exit(1)
    
    # Reset services
    reset_ok = reset_services()
    print("-" * 40)
    
    if not reset_ok:
        print("⚠️ Service reset failed, but continuing with test...")
    
    # Test verification stats after reset
    verification_ok = test_verification_stats_endpoint()
    print("-" * 40)
    
    # Summary
    print("\nTest Summary:")
    print(f"Health endpoint: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Service reset: {'✓ PASS' if reset_ok else '✗ FAIL'}")
    print(f"Verification stats: {'✓ PASS' if verification_ok else '✗ FAIL'}")
    
    if verification_ok:
        print("\n🎉 Verification stats endpoint is now working correctly!")
    else:
        print("\n⚠️ Verification stats endpoint still has issues.")