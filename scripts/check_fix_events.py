#!/usr/bin/env python3
"""
Check if fix events are in MongoDB.
"""

import os
import sys
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.config import get_mongodb_config

def check_fix_events():
    """Check for fix events in MongoDB."""
    config = get_mongodb_config()
    
    # Build connection string
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
    
    try:
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        db = client[config["database"]]
        collection = db["events"]
        
        # Check for fix.review_required events
        review_required = list(collection.find({
            "topic": "chronos.events.fix.review_required"
        }).sort("timestamp", -1).limit(10))
        
        print(f"\nFound {len(review_required)} fix.review_required events:")
        for event in review_required:
            fix_id = event.get("payload", {}).get("details", {}).get("fix_id", "UNKNOWN")
            timestamp = event.get("timestamp", "UNKNOWN")
            print(f"  - Fix ID: {fix_id}, Timestamp: {timestamp}")
        
        # Check for fix.proposed events
        proposed = list(collection.find({
            "topic": "chronos.events.fix.proposed"
        }).sort("timestamp", -1).limit(10))
        
        print(f"\nFound {len(proposed)} fix.proposed events:")
        for event in proposed:
            fix_id = event.get("payload", {}).get("details", {}).get("fix_id", "UNKNOWN")
            timestamp = event.get("timestamp", "UNKNOWN")
            print(f"  - Fix ID: {fix_id}, Timestamp: {timestamp}")
        
        # Check for approved/rejected events
        processed = list(collection.find({
            "topic": {"$in": ["chronos.events.fix.approved", "chronos.events.fix.rejected"]}
        }).sort("timestamp", -1).limit(10))
        
        print(f"\nFound {len(processed)} processed fixes (approved/rejected):")
        for event in processed:
            fix_id = event.get("payload", {}).get("details", {}).get("fix_id", "UNKNOWN")
            topic = event.get("topic", "UNKNOWN")
            print(f"  - Fix ID: {fix_id}, Status: {topic.split('.')[-1]}")
        
        # Check what the API would return
        processed_fix_ids = set()
        for event in processed:
            fix_id = event.get("payload", {}).get("details", {}).get("fix_id")
            if fix_id:
                processed_fix_ids.add(fix_id)
        
        pending = [e for e in review_required 
                  if e.get("payload", {}).get("details", {}).get("fix_id") not in processed_fix_ids]
        
        print(f"\nPending fixes (not approved/rejected): {len(pending)}")
        for event in pending:
            fix_id = event.get("payload", {}).get("details", {}).get("fix_id", "UNKNOWN")
            print(f"  - Fix ID: {fix_id}")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fix_events()

