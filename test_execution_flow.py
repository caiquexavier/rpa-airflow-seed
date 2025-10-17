#!/usr/bin/env python3
"""Test script to verify the execution correlation flow."""
import requests
import json
import time

# Test configuration
API_BASE_URL = "http://localhost:3000"

def test_request_execution():
    """Test requesting an RPA execution."""
    print("Testing RPA execution request...")
    
    payload = {
        "rpa_key_id": "job-001",
        "callback_url": f"{API_BASE_URL}/updateRpaExecution",
        "rpa_request": {"nota_fiscal": "12345"}
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/request_rpa_exec",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 202:
            data = response.json()
            return data.get("exec_id")
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error making request: {e}")
        return None

def test_update_execution(exec_id):
    """Test updating execution status."""
    print(f"\nTesting execution update for exec_id={exec_id}...")
    
    payload = {
        "exec_id": exec_id,
        "rpa_key_id": "job-001",
        "rpa_response": {"files": ["pod.pdf"], "meta": {"elapsed_ms": 5000}},
        "status": "SUCCESS",
        "error_message": None
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/updateRpaExecution",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error making request: {e}")
        return False

def test_validation_errors():
    """Test validation error handling."""
    print("\nTesting validation errors...")
    
    # Test missing rpa_key_id
    payload = {"rpa_request": {"k": "v"}}
    response = requests.post(f"{API_BASE_URL}/request_rpa_exec", json=payload)
    print(f"Missing rpa_key_id - Status: {response.status_code}")
    
    # Test invalid callback URL
    payload = {"rpa_key_id": "job-001", "callback_url": "not-a-url"}
    response = requests.post(f"{API_BASE_URL}/request_rpa_exec", json=payload)
    print(f"Invalid callback URL - Status: {response.status_code}")
    
    # Test FAIL without error_message
    payload = {
        "exec_id": 999,
        "rpa_key_id": "job-001",
        "rpa_response": {},
        "status": "FAIL"
    }
    response = requests.post(f"{API_BASE_URL}/updateRpaExecution", json=payload)
    print(f"FAIL without error_message - Status: {response.status_code}")

def main():
    """Run all tests."""
    print("=== RPA Execution Correlation Test ===\n")
    
    # Test 1: Request execution
    exec_id = test_request_execution()
    if not exec_id:
        print("Failed to create execution. Make sure the API is running.")
        return
    
    # Test 2: Update execution
    if test_update_execution(exec_id):
        print("✅ Execution update successful!")
    else:
        print("❌ Execution update failed!")
    
    # Test 3: Validation errors
    test_validation_errors()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
