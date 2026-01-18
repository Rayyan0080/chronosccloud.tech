#!/usr/bin/env python3
"""
Quick script to populate the airspace map with test data.
Uploads a test flight plan and ensures agents are processing it.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    print("=" * 70)
    print("Populating Airspace Map with Test Data")
    print("=" * 70)
    print()
    
    # Check if test flight plan exists
    test_plan_path = project_root / "dashboard" / "test_flight_plan_simple.json"
    if not test_plan_path.exists():
        print(f"[ERROR] Test flight plan not found: {test_plan_path}")
        print("   Creating a simple Ottawa-area test plan...")
        
        # Create a simple Ottawa-area flight plan
        ottawa_plan = {
            "plan_name": "Ottawa Test Flight Plan",
            "flights": [
                {
                    "ACID": "YOW001",
                    "Plane type": "Boeing 737-800",
                    "route": ["CYOW", "CYYZ"],  # Ottawa to Toronto
                    "altitude": 35000,
                    "departure airport": "CYOW",
                    "arrival airport": "CYYZ",
                    "departure time": "2024-01-20T10:00:00Z",
                    "aircraft speed": 450,
                    "passengers": 180,
                    "is_cargo": False
                },
                {
                    "ACID": "YOW002",
                    "Plane type": "Airbus A320",
                    "route": ["CYOW", "CYUL"],  # Ottawa to Montreal
                    "altitude": 35000,
                    "departure airport": "CYOW",
                    "arrival airport": "CYUL",
                    "departure time": "2024-01-20T10:15:00Z",
                    "aircraft speed": 450,
                    "passengers": 150,
                    "is_cargo": False
                },
                {
                    "ACID": "YOW003",
                    "Plane type": "Boeing 777",
                    "route": ["CYYZ", "CYOW"],  # Toronto to Ottawa
                    "altitude": 38000,
                    "departure airport": "CYYZ",
                    "arrival airport": "CYOW",
                    "departure time": "2024-01-20T11:00:00Z",
                    "aircraft speed": 480,
                    "passengers": 350,
                    "is_cargo": False
                }
            ]
        }
        
        test_plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(test_plan_path, 'w') as f:
            json.dump(ottawa_plan, f, indent=2)
        print(f"[OK] Created test plan: {test_plan_path}")
    
    # Run flight_plan_ingestor
    print()
    print("Step 1: Processing flight plan...")
    ingestor_path = project_root / "agents" / "flight_plan_ingestor.py"
    
    if not ingestor_path.exists():
        print(f"[ERROR] Flight plan ingestor not found: {ingestor_path}")
        return 1
    
    try:
        result = subprocess.run(
            [sys.executable, str(ingestor_path), str(test_plan_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("[OK] Flight plan processed successfully")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()[:200]}")
        else:
            print(f"[WARN] Flight plan ingestor returned code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()[:200]}")
    except subprocess.TimeoutExpired:
        print("⚠️  Flight plan ingestor timed out (this is OK if it's still processing)")
    except Exception as e:
        print(f"[ERROR] Error running ingestor: {e}")
        return 1
    
    print()
    print("Step 2: Checking for airspace events in database...")
    
    try:
        from agents.shared.config import get_mongodb_config
        from pymongo import MongoClient
        
        config = get_mongodb_config()
        uri = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?authSource=admin"
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client[config['database']]
        events = db.events
        
        airspace_count = events.count_documents({'topic': {'$regex': 'airspace'}})
        geo_count = events.count_documents({'topic': {'$regex': 'geo'}})
        
        print(f"   Airspace events: {airspace_count}")
        print(f"   Geo events: {geo_count}")
        
        if airspace_count > 0 or geo_count > 0:
            print("[OK] Events found in database!")
            print()
            print("Next steps:")
            print("1. Make sure trajectory_insight_agent is running:")
            print("   python agents/trajectory_insight_agent.py")
            print("2. Refresh the dashboard map page")
            print("3. The map should now show flights, conflicts, and hotspots")
        else:
            print("⚠️  No airspace events found yet")
            print()
            print("This could mean:")
            print("1. The flight plan ingestor needs more time to process")
            print("2. The trajectory_insight_agent needs to be running to detect conflicts")
            print("3. Try uploading the plan via the dashboard Upload Plan tab")
        
        client.close()
    except Exception as e:
        print(f"[ERROR] Error checking database: {e}")
        return 1
    
    print()
    print("=" * 70)
    print("Done!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())

