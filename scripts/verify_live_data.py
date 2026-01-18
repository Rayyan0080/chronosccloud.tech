"""
Verification script to check live data adapter status and event flow.

This script helps verify:
1. Which adapters are enabled
2. What mode they're in (live vs mock)
3. If events are being published
4. What's in MongoDB
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from agents.shared.messaging import get_broker
from agents.shared.config import get_mongodb_config
from live_data.base import is_live_mode_enabled

def check_environment():
    """Check environment variables."""
    print("=" * 80)
    print("ENVIRONMENT CHECK")
    print("=" * 80)
    
    live_mode = os.getenv("LIVE_MODE", "off")
    live_adapters = os.getenv("LIVE_ADAPTERS", "")
    
    print(f"LIVE_MODE: {live_mode}")
    print(f"LIVE_ADAPTERS: {live_adapters}")
    print(f"is_live_mode_enabled(): {is_live_mode_enabled()}")
    print()
    
    # Check adapter-specific env vars
    print("Adapter Configuration:")
    print(f"  OCTRANSPO_API_KEY: {'SET' if os.getenv('OCTRANSPO_API_KEY') or os.getenv('OCTRANSPO_SUBSCRIPTION_KEY') else 'NOT SET'}")
    print(f"  OPENSKY_USER: {'SET' if os.getenv('OPENSKY_USER') else 'NOT SET'}")
    print(f"  OPENSKY_PASS: {'SET' if os.getenv('OPENSKY_PASS') else 'NOT SET'}")
    print(f"  OTTAWA_TRAFFIC_INCIDENTS_URL: {os.getenv('OTTAWA_TRAFFIC_INCIDENTS_URL', 'using default')}")
    print()
    
    return live_mode, live_adapters

async def check_broker():
    """Check message broker connection."""
    print("=" * 80)
    print("MESSAGE BROKER CHECK")
    print("=" * 80)
    
    try:
        broker = await get_broker()
        connected = await broker.is_connected()
        broker_type = type(broker).__name__
        
        print(f"Broker Type: {broker_type}")
        print(f"Connected: {connected}")
        print()
        
        await broker.disconnect()
        return connected
    except Exception as e:
        print(f"ERROR: Failed to connect to broker: {e}")
        print()
        return False

def check_mongodb():
    """Check MongoDB connection and recent events."""
    print("=" * 80)
    print("MONGODB CHECK")
    print("=" * 80)
    
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure
        
        config = get_mongodb_config()
        
        if config["username"] and config["password"]:
            connection_string = (
                f"mongodb://{config['username']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['database']}"
                f"?authSource=admin"
            )
        else:
            connection_string = (
                f"mongodb://{config['host']}:{config['port']}/{config['database']}"
            )
        
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[config["database"]]
        collection = db["events"]
        
        print(f"Connected to MongoDB: {config['host']}:{config['port']}")
        print(f"Database: {config['database']}")
        print()
        
        # Count events by topic in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        print("Events in last hour (by topic):")
        pipeline = [
            {"$match": {"timestamp": {"$gte": one_hour_ago}}},
            {"$group": {"_id": "$topic", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        results = list(collection.aggregate(pipeline))
        if results:
            for result in results:
                topic = result["_id"]
                count = result["count"]
                print(f"  {topic}: {count}")
        else:
            print("  No events found in last hour")
        print()
        
        # Check for specific adapter events
        print("Adapter Event Check:")
        adapter_topics = {
            "transit": ["chronos.events.transit.vehicle.position", "chronos.events.transit.trip.update"],
            "traffic": ["chronos.events.geo.incident", "chronos.events.geo.risk_area"],
            "airspace": ["chronos.events.airspace.aircraft.position"],
            "ontario511": ["chronos.events.geo.incident", "chronos.events.geo.risk_area"],
        }
        
        for adapter_name, topics in adapter_topics.items():
            count = collection.count_documents({
                "topic": {"$in": topics},
                "timestamp": {"$gte": one_hour_ago},
                "payload.source": {"$regex": adapter_name, "$options": "i"}
            })
            print(f"  {adapter_name}: {count} events")
        print()
        
        # Check most recent events
        print("Most recent 10 events:")
        recent = collection.find().sort("timestamp", -1).limit(10)
        for event in recent:
            timestamp = event.get("timestamp", "unknown")
            topic = event.get("topic", "unknown")
            source = event.get("payload", {}).get("source", "unknown")
            summary = event.get("payload", {}).get("summary", "no summary")
            print(f"  [{timestamp}] {topic} | source: {source}")
            print(f"    {summary[:80]}...")
        print()
        
        client.close()
        return True
        
    except ConnectionFailure as e:
        print(f"ERROR: Failed to connect to MongoDB: {e}")
        print()
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        print()
        return False

async def check_adapter_status():
    """Check adapter status from the runner (if running)."""
    print("=" * 80)
    print("ADAPTER STATUS CHECK")
    print("=" * 80)
    
    # Try to import and check adapter status
    try:
        from live_data.runner import get_adapter_status_summary
        
        status = get_adapter_status_summary()
        
        print(f"Live Mode: {status['live_mode'].upper()}")
        print(f"Total Adapters: {len(status['adapters'])}")
        print(f"Degraded Adapters: {len(status['degraded_adapters'])}")
        print()
        
        if status['degraded_adapters']:
            print("[WARNING] DEGRADED ADAPTERS:")
            for name in status['degraded_adapters']:
                print(f"  - {name}")
            print()
        
        print("Adapter Details:")
        for adapter in status['adapters']:
            mode_icon = "[LIVE]" if adapter['mode'] == 'live' else "[MOCK]"
            degraded_icon = "[DEGRADED]" if adapter['degraded'] else "[OK]"
            print(f"  {mode_icon} {degraded_icon} {adapter['name']}: {adapter['mode']} (enabled: {adapter['enabled']})")
            if adapter.get('last_fetch'):
                print(f"      Last fetch: {adapter['last_fetch']}")
            if adapter.get('last_error'):
                print(f"      Last error: {adapter['last_error'][:100]}")
        print()
        
    except Exception as e:
        print(f"Could not get adapter status (runner may not be running): {e}")
        print("  This is normal if the live data runner is not currently running.")
        print()

def main():
    """Run all verification checks."""
    print("\n" + "=" * 80)
    print("CHRONOS LIVE DATA VERIFICATION")
    print("=" * 80)
    print()
    
    # 1. Check environment
    live_mode, live_adapters = check_environment()
    
    # 2. Check broker
    broker_ok = asyncio.run(check_broker())
    
    # 3. Check MongoDB
    mongo_ok = check_mongodb()
    
    # 4. Check adapter status
    asyncio.run(check_adapter_status())
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"LIVE_MODE: {live_mode.upper()}")
    print(f"Enabled Adapters: {live_adapters}")
    print(f"Broker: {'[OK] Connected' if broker_ok else '[FAIL] Not Connected'}")
    print(f"MongoDB: {'[OK] Connected' if mongo_ok else '[FAIL] Not Connected'}")
    print()
    
    if live_mode.lower() == "off":
        print("[WARNING] LIVE_MODE is OFF - all adapters will use mock data")
    elif not live_adapters:
        print("[WARNING] No adapters enabled in LIVE_ADAPTERS")
    else:
        print("[OK] Configuration looks good!")
        print()
        print("To see live data:")
        print("  1. Make sure 'python live_data/runner.py' is running")
        print("  2. Make sure 'python agents/state_logger.py' is running")
        print("  3. Check the dashboard at http://localhost:3000")
    print()

if __name__ == "__main__":
    main()

