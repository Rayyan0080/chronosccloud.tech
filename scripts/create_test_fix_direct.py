#!/usr/bin/env python3
"""
Create a test fix directly in MongoDB (bypasses NATS/state_logger).
Useful for testing when state_logger isn't running.
"""

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.config import get_mongodb_config
from agents.shared.schema import Severity, ActionType, FixSource, RiskLevel


def create_test_fix_direct():
    """Create a test fix directly in MongoDB."""
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
        
        # Generate test fix
        fix_id = f"FIX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        correlation_id = f"TEST-{str(uuid4())[:8].upper()}"
        
        fix_details = {
            "fix_id": fix_id,
            "correlation_id": correlation_id,
            "source": FixSource.RULES.value,
            "title": "Test Transit Reroute Fix",
            "summary": "Test fix proposal: Reroute bus route 95 to bypass downtown congestion area. This is a simulated fix for testing the Audit tab workflow.",
            "actions": [
                {
                    "type": ActionType.TRANSIT_REROUTE_SIM.value,
                    "target": {
                        "route_id": "ROUTE-95",
                        "area_bbox": {
                            "min_lat": 45.4115,
                            "max_lat": 45.4315,
                            "min_lon": -75.7072,
                            "max_lon": -75.6872
                        }
                    },
                    "params": {
                        "alternative_route": ["STOP-12345", "STOP-12350", "STOP-12355"],
                        "expected_delay_reduction": 15.0
                    },
                    "verification": {
                        "metric_name": "delay_reduction",
                        "threshold": 10.0,
                        "window_seconds": 300
                    }
                }
            ],
            "risk_level": RiskLevel.MED.value,
            "expected_impact": {
                "delay_reduction": 15.0,
                "risk_score_delta": -0.2,
                "area_affected": "Downtown core"
            },
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "proposed_by": "test-script",
            "requires_human_approval": True
        }
        
        # Create fix.review_required event
        fix_review_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "test-script",
            "severity": Severity.WARNING.value,
            "sector_id": "ottawa-transit",
            "summary": f"Fix {fix_id} requires human review",
            "correlation_id": correlation_id,
            "details": fix_details
        }
        
        # Insert directly into MongoDB
        now = datetime.now(timezone.utc)
        collection.insert_one({
            "topic": "chronos.events.fix.review_required",
            "payload": fix_review_event,
            "timestamp": now,
            "logged_at": now,
        })
        
        print(f"[OK] Test fix created directly in MongoDB!")
        print(f"  Fix ID: {fix_id}")
        print(f"  Title: {fix_details['title']}")
        print(f"\nRefresh the Audit tab to see the fix.")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_test_fix_direct()

