#!/usr/bin/env python3
"""
Quick verification script to test all critical components.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from agents.shared.config import get_mongodb_config
from agents.shared.messaging import get_broker, publish
from agents.shared.constants import POWER_FAILURE_TOPIC

async def test_nats():
    """Test NATS connection."""
    print("\n[TEST] NATS Connection...")
    try:
        broker = await get_broker()
        if await broker.is_connected():
            print("  [OK] NATS connected")
            return True
        else:
            print("  [FAIL] NATS not connected")
            return False
    except Exception as e:
        print(f"  [FAIL] NATS error: {e}")
        return False

async def test_nats_publish():
    """Test publishing to NATS."""
    print("\n[TEST] NATS Publish...")
    try:
        broker = await get_broker()
        if not await broker.is_connected():
            print("  [SKIP] Skipping (not connected)")
            return False
        
        test_event = {
            "event_id": "test-verify-001",
            "timestamp": "2026-01-18T00:00:00Z",
            "severity": "info",
            "summary": "Test verification event",
        }
        
        await publish(POWER_FAILURE_TOPIC, test_event)
        print("  [OK] Event published successfully")
        return True
    except Exception as e:
        print(f"  [FAIL] Publish error: {e}")
        return False

def test_mongodb():
    """Test MongoDB connection."""
    print("\n[TEST] MongoDB Connection...")
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
        print(f"  [OK] MongoDB connected ({count} events in database)")
        return True
    except Exception as e:
        print(f"  [FAIL] MongoDB error: {e}")
        return False

def test_docker():
    """Test Docker services."""
    print("\n[TEST] Docker Services...")
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

async def main():
    print("=" * 70)
    print("QUICK VERIFICATION")
    print("=" * 70)
    
    results = {}
    
    # Test Docker
    results["docker"] = test_docker()
    
    # Test MongoDB
    results["mongodb"] = test_mongodb()
    
    # Test NATS
    results["nats"] = await test_nats()
    
    # Test NATS Publish
    if results["nats"]:
        results["nats_publish"] = await test_nats_publish()
    else:
        results["nats_publish"] = False
        print("\n[TEST] NATS Publish...")
        print("  ⚠️  Skipped (NATS not connected)")
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All critical components verified!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

