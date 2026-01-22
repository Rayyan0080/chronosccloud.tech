"""
Create a test defense threat for testing the Audit tab.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.constants import DEFENSE_THREAT_DETECTED_TOPIC, DISCLAIMER_DEFENSE
from agents.shared.schema import Severity, ThreatType

async def main():
    """Create a test defense threat."""
    threat_id = f"THREAT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    threat_event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "defense-detector-test",
        "severity": Severity.MODERATE.value,
        "sector_id": "ottawa-airspace",
        "summary": f"Test threat detected: Multiple airspace conflicts in downtown area",
        "correlation_id": threat_id,
        "details": {
            "threat_id": threat_id,
            "threat_type": ThreatType.AIRSPACE.value,
            "confidence_score": 0.75,
            "severity": "high",
            "affected_area": {
                "type": "Polygon",
                "coordinates": [[
                    [-75.7, 45.4],
                    [-75.6, 45.4],
                    [-75.6, 45.5],
                    [-75.7, 45.5],
                    [-75.7, 45.4]
                ]]
            },
            "sources": ["airspace", "transit"],
            "summary": "Multiple airspace conflicts detected in downtown Ottawa area. Elevated risk of collision.",
            "detected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "disclaimer": DISCLAIMER_DEFENSE,
        },
    }
    
    # Connect and publish
    broker = await get_broker()
    await broker.connect()
    
    print(f"Publishing test threat: {threat_id}")
    await publish(DEFENSE_THREAT_DETECTED_TOPIC, threat_event)
    print(f"[OK] Published defense.threat.detected event")
    print(f"  Threat ID: {threat_id}")
    print(f"  Type: {threat_event['details']['threat_type']}")
    print(f"  Confidence: {threat_event['details']['confidence_score']*100}%")
    print(f"  Severity: {threat_event['details']['severity']}")
    print(f"\nNow:")
    print("1. Go to the Audit tab in the dashboard")
    print("2. Click on the 'Defense Threats' tab")
    print("3. You should see this threat in the list")
    
    await broker.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

