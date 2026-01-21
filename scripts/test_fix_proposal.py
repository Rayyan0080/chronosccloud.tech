#!/usr/bin/env python3
"""
Test script to generate a fix proposal for testing the Audit tab.

This creates a test fix that will appear in the Audit tab for review.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.constants import FIX_PROPOSED_TOPIC, FIX_REVIEW_REQUIRED_TOPIC
from agents.shared.schema import Severity, ActionType, FixSource, RiskLevel


async def create_test_fix():
    """Create a test fix proposal."""
    # Connect to broker
    broker = await get_broker()
    await broker.connect()
    print("[OK] Connected to message broker")

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

    # Create fix.proposed event
    fix_proposed_event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "test-script",
        "severity": Severity.WARNING.value,
        "sector_id": "ottawa-transit",
        "summary": f"Fix {fix_id} proposed: {fix_details['title']}",
        "correlation_id": correlation_id,
        "details": fix_details
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

    # Publish events
    print(f"\nPublishing test fix: {fix_id}")
    await publish(FIX_PROPOSED_TOPIC, fix_proposed_event)
    print(f"[OK] Published fix.proposed event")
    
    await publish(FIX_REVIEW_REQUIRED_TOPIC, fix_review_event)
    print(f"[OK] Published fix.review_required event")
    
    print(f"\n[OK] Test fix created successfully!")
    print(f"  Fix ID: {fix_id}")
    print(f"  Title: {fix_details['title']}")
    print(f"\nRefresh the Audit tab to see the fix.")
    
    await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(create_test_fix())

