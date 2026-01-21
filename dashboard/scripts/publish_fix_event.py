#!/usr/bin/env python3
"""
Helper script to publish fix events to NATS from the dashboard API.
This is called by Next.js API routes via subprocess.
"""
import sys
import json
import asyncio
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.shared.messaging import get_broker, publish
from agents.shared.constants import (
    FIX_APPROVED_TOPIC,
    FIX_REJECTED_TOPIC,
    FIX_DEPLOY_REQUESTED_TOPIC,
)


async def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: publish_fix_event.py <topic> <event_json_base64>"}))
        sys.exit(1)

    topic = sys.argv[1]
    event_json_base64 = sys.argv[2]

    try:
        # Decode from base64
        import base64
        event_json = base64.b64decode(event_json_base64).decode('utf-8')
        event = json.loads(event_json)
        
        # Connect to broker
        broker = await get_broker()
        await broker.connect()

        # Publish event
        await publish(topic, event)
        
        print(json.dumps({"success": True, "topic": topic}))
        
        # Disconnect
        await broker.disconnect()
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

