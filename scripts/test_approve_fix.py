#!/usr/bin/env python3
"""
Test the approve endpoint directly.
"""

import requests
import json
import sys

if len(sys.argv) < 2:
    print("Usage: test_approve_fix.py <fix_id>")
    sys.exit(1)

fix_id = sys.argv[1]
url = f"http://localhost:3000/api/fix/{fix_id}/approve"

print(f"Testing approve endpoint for fix: {fix_id}")
print(f"URL: {url}")

try:
    response = requests.post(url, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    try:
        data = response.json()
        print(f"Response Body: {json.dumps(data, indent=2)}")
    except:
        print(f"Response Body (text): {response.text}")
        
    if response.status_code == 200 and data.get('success'):
        print("\n[OK] Fix approved successfully!")
    else:
        print(f"\n[FAIL] Approval failed: {data.get('error', 'Unknown error')}")
        
except requests.exceptions.ConnectionError:
    print("\n[ERROR] Could not connect to dashboard. Is it running on localhost:3000?")
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

