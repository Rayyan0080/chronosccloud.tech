#!/usr/bin/env python3
"""Check airspace events in MongoDB."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from agents.shared.config import get_mongodb_config
from datetime import datetime, timedelta

config = get_mongodb_config()
client = MongoClient(
    config['host'],
    config['port'],
    username=config.get('username'),
    password=config.get('password'),
    authSource='admin' if config.get('username') else None
)
db = client[config['database']]

# Count airspace events
airspace_total = db.events.count_documents({'topic': {'$regex': '^airspace\\.'}})
flight_parsed = db.events.count_documents({'topic': 'airspace.flight.parsed'})
conflicts = db.events.count_documents({'topic': 'airspace.conflict.detected'})
hotspots = db.events.count_documents({'topic': 'airspace.hotspot.detected'})
geo_incidents = db.events.count_documents({'topic': 'geo.incident'})
geo_risk = db.events.count_documents({'topic': 'geo.risk_area'})

print(f"\nAirspace Events Summary:")
print(f"  Total airspace events: {airspace_total}")
print(f"  Flight parsed events: {flight_parsed}")
print(f"  Conflict events: {conflicts}")
print(f"  Hotspot events: {hotspots}")
print(f"  Geo incidents: {geo_incidents}")
print(f"  Geo risk areas: {geo_risk}")

# Recent events
print(f"\nRecent airspace events (last 10):")
recent = list(db.events.find({'topic': {'$regex': '^airspace\\.'}})
              .sort('timestamp', -1)
              .limit(10))

if recent:
    for e in recent:
        ts = e.get('timestamp', 'N/A')
        topic = e.get('topic', 'N/A')
        summary = e.get('summary', 'N/A')[:60]
        print(f"  [{ts}] {topic}: {summary}")
else:
    print("  No airspace events found")

# Check for events with geometry
print(f"\nEvents with geometry (for map display):")
geo_events = list(db.events.find({
    '$or': [
        {'topic': 'geo.incident'},
        {'topic': 'geo.risk_area'},
        {'geometry': {'$exists': True}}
    ]
}).sort('timestamp', -1).limit(10))

if geo_events:
    for e in geo_events:
        topic = e.get('topic', 'N/A')
        has_geo = 'geometry' in e
        print(f"  {topic}: has_geometry={has_geo}")
else:
    print("  No geo events found")

client.close()
