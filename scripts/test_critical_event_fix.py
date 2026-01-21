#!/usr/bin/env python3
"""
Test script to generate a Critical event and verify it triggers a fix proposal.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.constants import POWER_FAILURE_TOPIC
from agents.shared.schema import Severity


async def create_critical_event():
    """Create a Critical power failure event to test fix proposal generation."""
    # Connect to broker
    broker = await get_broker()
    await broker.connect()
    print("[OK] Connected to message broker")

    # Create Critical power failure event
    event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "test-script",
        "severity": Severity.CRITICAL.value,  # CRITICAL severity
        "sector_id": "building-a-main",
        "summary": "CRITICAL: Complete power failure in Building A",
        "correlation_id": f"TEST-{str(uuid4())[:8].upper()}",
        "details": {
            "voltage": 0.0,
            "load": 0.0,
            "current": 0.0,
            "phase": "all",
            "backup_status": "failed",
            "estimated_restore_time": "2-4 hours",
            "affected_facilities": ["hospital", "data-center"],
        }
    }

    print(f"\nPublishing CRITICAL power failure event:")
    print(f"  Event ID: {event['event_id']}")
    print(f"  Severity: {event['severity']}")
    print(f"  Sector: {event['sector_id']}")
    print(f"  Summary: {event['summary']}")
    
    await publish(POWER_FAILURE_TOPIC, event)
    print(f"\n[OK] Published CRITICAL event to {POWER_FAILURE_TOPIC}")
    print(f"\nThe fix_proposal_agent should automatically generate a fix proposal.")
    print(f"Check the Audit tab in ~5-10 seconds to see the fix.")
    
    await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(create_critical_event())

