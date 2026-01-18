#!/usr/bin/env python3
"""
System Verification Script - Tests actual running system components.
"""

import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from agents.shared.config import get_mongodb_config, get_broker_backend
from agents.shared.messaging import get_broker, publish
from agents.shared.constants import POWER_FAILURE_TOPIC

def test_docker():
    """Test Docker services are running."""
    print("\n[1] Testing Docker Services...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("  [FAIL] Docker not accessible")
            return False
        
        containers = result.stdout.strip().split("\n")
        required = ["chronos-mongodb", "chronos-nats"]
        found = [c for c in required if any(c in line for line in containers)]
        
        if len(found) == len(required):
            print(f"  [OK] Docker services running: {', '.join(found)}")
            return True
        else:
            missing = [c for c in required if c not in found]
            print(f"  [FAIL] Missing containers: {', '.join(missing)}")
            return False
    except Exception as e:
        print(f"  [FAIL] Docker error: {e}")
        return False

def test_mongodb():
    """Test MongoDB connection."""
    print("\n[2] Testing MongoDB Connection...")
    try:
        config = get_mongodb_config()
        if config["username"] and config["password"]:
            client = MongoClient(
                config["host"],
                config["port"],
                username=config["username"],
                password=config["password"],
                authSource="admin",
                serverSelectionTimeoutMS=5000,
            )
        else:
            client = MongoClient(
                config["host"],
                config["port"],
                serverSelectionTimeoutMS=5000,
            )
        
        client.server_info()
        db = client[config["database"]]
        count = db.events.count_documents({})
        client.close()
        print(f"  [OK] MongoDB connected ({count:,} events in database)")
        return True
    except Exception as e:
        print(f"  [FAIL] MongoDB error: {e}")
        return False

async def test_nats_connection():
    """Test NATS connection with retry."""
    print("\n[3] Testing NATS Connection...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            broker = await get_broker()
            # Wait a bit for connection to establish
            await asyncio.sleep(1)
            if await broker.is_connected():
                backend = get_broker_backend()
                print(f"  [OK] Connected to {backend.upper()}")
                return True
            else:
                if attempt < max_retries - 1:
                    print(f"  [RETRY] Attempt {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(2)
                    continue
                print("  [FAIL] Not connected after retries")
                return False
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [RETRY] Attempt {attempt + 1}/{max_retries}... Error: {str(e)[:50]}")
                await asyncio.sleep(2)
                continue
            print(f"  [FAIL] NATS connection error: {e}")
            return False
    return False

async def test_nats_publish():
    """Test publishing to NATS."""
    print("\n[4] Testing NATS Publish...")
    try:
        broker = await get_broker()
        if not await broker.is_connected():
            print("  [SKIP] Skipping (not connected)")
            return False
        
        test_event = {
            "event_id": f"verify-{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "severity": "info",
            "summary": "System verification test event",
        }
        
        await publish(POWER_FAILURE_TOPIC, test_event)
        print("  [OK] Event published successfully")
        return True
    except Exception as e:
        print(f"  [FAIL] Publish error: {e}")
        return False

def test_dashboard_api():
    """Test Dashboard API."""
    print("\n[5] Testing Dashboard API...")
    try:
        import urllib.request
        import json
        
        url = "http://localhost:3000/api/events?limit=10"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            count = len(data.get("events", []))
            print(f"  [OK] Dashboard API accessible ({count} events returned)")
            return True
    except urllib.error.URLError:
        print("  [WARN] Dashboard API not accessible (may not be running)")
        return False
    except Exception as e:
        print(f"  [WARN] Dashboard API error: {e}")
        return False

async def main():
    print("=" * 70)
    print("SYSTEM VERIFICATION")
    print("=" * 70)
    
    results = {}
    
    # Test Docker
    results["docker"] = test_docker()
    
    # Test MongoDB
    results["mongodb"] = test_mongodb()
    
    # Test NATS
    results["nats"] = await test_nats_connection()
    
    # Test NATS Publish
    if results["nats"]:
        results["nats_publish"] = await test_nats_publish()
    else:
        results["nats_publish"] = False
        print("\n[4] Testing NATS Publish...")
        print("  [SKIP] Skipped (NATS not connected)")
    
    # Test Dashboard
    results["dashboard"] = test_dashboard_api()
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All system components verified!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        if not results.get("nats"):
            print("\nNOTE: If NATS test failed, check:")
            print("  1. Docker container is running: docker ps | grep chronos-nats")
            print("  2. Port 4222 is accessible: netstat -an | findstr 4222")
            print("  3. Try restarting NATS: docker restart chronos-nats")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nVerification interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

