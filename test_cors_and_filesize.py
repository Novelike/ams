import requests
import json
import os
from io import BytesIO

def test_cors_configuration():
    """Test CORS configuration by checking allowed origins"""
    print("🔍 Testing CORS Configuration...")
    
    # Test health endpoint with different origins
    test_origins = [
        "https://ams.novelike.dev",
        "http://ams.novelike.dev", 
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    
    base_url = "http://localhost:8000"
    
    for origin in test_origins:
        try:
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
            
            # Test preflight request
            response = requests.options(f"{base_url}/api/health", headers=headers)
            
            if response.status_code == 200:
                cors_headers = response.headers
                allowed_origins = cors_headers.get("Access-Control-Allow-Origin", "")
                
                if allowed_origins == origin or allowed_origins == "*":
                    print(f"✅ CORS OK for origin: {origin}")
                else:
                    print(f"❌ CORS FAILED for origin: {origin}")
            else:
                print(f"❌ Preflight failed for origin: {origin} - Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing origin {origin}: {str(e)}")

def test_file_size_limit():
    """Test file size limit middleware"""
    print("\n📁 Testing File Size Limit...")
    
    base_url = "http://localhost:8000"
    
    # Create test files of different sizes
    test_cases = [
        {"size_mb": 1, "should_pass": True, "description": "1MB file (should pass)"},
        {"size_mb": 10, "should_pass": True, "description": "10MB file (should pass)"},
        {"size_mb": 60, "should_pass": False, "description": "60MB file (should fail)"}
    ]
    
    for test_case in test_cases:
        try:
            # Create a test file in memory
            file_size = test_case["size_mb"] * 1024 * 1024
            test_data = b"0" * file_size
            
            files = {"file": ("test_file.txt", BytesIO(test_data), "text/plain")}
            
            # Try to upload to a test upload endpoint
            # Note: This assumes there's an upload endpoint - adjust URL as needed
            response = requests.post(f"{base_url}/upload", files=files)
            
            if test_case["should_pass"]:
                if response.status_code != 413:
                    print(f"✅ {test_case['description']} - Status: {response.status_code}")
                else:
                    print(f"❌ {test_case['description']} - Unexpected 413 error")
            else:
                if response.status_code == 413:
                    print(f"✅ {test_case['description']} - Correctly rejected with 413")
                else:
                    print(f"❌ {test_case['description']} - Should have been rejected but got: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Error testing {test_case['description']}: {str(e)}")

def test_health_endpoint():
    """Test basic health endpoint functionality"""
    print("\n🏥 Testing Health Endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/api/health")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ Health endpoint working correctly")
                print(f"   Service: {data.get('service')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Timestamp: {data.get('timestamp')}")
            else:
                print("❌ Health endpoint returned unexpected data")
        else:
            print(f"❌ Health endpoint failed - Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {str(e)}")

def check_environment_config():
    """Check if environment variables are properly configured"""
    print("\n⚙️ Checking Environment Configuration...")
    
    # Check if .env file exists and has correct values
    env_file = "ams-back/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
            
        required_configs = [
            "ENVIRONMENT=production",
            "https://ams.novelike.dev",
            "http://ams.novelike.dev",
            "PROD_SERVER_IP=10.0.3.203"
        ]
        
        for config in required_configs:
            if config in content:
                print(f"✅ Found: {config}")
            else:
                print(f"❌ Missing: {config}")
    else:
        print("❌ .env file not found")

if __name__ == "__main__":
    print("🚀 Starting CORS and File Size Limit Tests")
    print("=" * 50)
    
    # Check environment configuration first
    check_environment_config()
    
    # Test health endpoint
    test_health_endpoint()
    
    # Test CORS configuration
    test_cors_configuration()
    
    # Test file size limits
    test_file_size_limit()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\nNote: Make sure the backend server is running on localhost:8000")
    print("Run: cd ams-back && python main.py")