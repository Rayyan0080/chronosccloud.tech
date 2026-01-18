#!/usr/bin/env python3
"""
Diagnose and fix airspace map issues.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from agents.shared.config import get_mongodb_config
import json

def main():
    config = get_mongodb_config()
    uri = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?authSource=admin"
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[config['database']]
    events = db.events
    
    print("=" * 70)
    print("AIRSPACE MAP DIAGNOSIS")
    print("=" * 70)
    print()
    
    # Check aircraft.position events
    aircraft_events = list(events.find({'topic': 'chronos.events.airspace.aircraft.position'}).limit(5))
    print(f"Aircraft position events: {events.count_documents({'topic': 'chronos.events.airspace.aircraft.position'})}")
    if aircraft_events:
        sample = aircraft_events[0]
        print("\nSample aircraft.position event structure:")
        print(f"  Topic: {sample.get('topic')}")
        print(f"  Payload keys: {list(sample.get('payload', {}).keys())}")
        details = sample.get('payload', {}).get('details', {})
        print(f"  Details keys: {list(details.keys())}")
        print(f"  Has latitude: {'latitude' in details}")
        print(f"  Has longitude: {'longitude' in details}")
        if 'latitude' in details and 'longitude' in details:
            print(f"  Location: ({details.get('latitude')}, {details.get('longitude')})")
        print()
    
    # Check geo.incident events from trajectory_insight_agent
    geo_incidents = list(events.find({
        'topic': 'chronos.events.geo.incident',
        'payload.source': 'trajectory-insight-agent'
    }).limit(5))
    print(f"Geo.incident events from trajectory_insight_agent: {events.count_documents({'topic': 'chronos.events.geo.incident', 'payload.source': 'trajectory-insight-agent'})}")
    if geo_incidents:
        sample = geo_incidents[0]
        print("\nSample geo.incident event structure:")
        print(f"  Topic: {sample.get('topic')}")
        print(f"  Source: {sample.get('payload', {}).get('source')}")
        details = sample.get('payload', {}).get('details', {})
        print(f"  Has geometry in details: {'geometry' in details}")
        if 'geometry' in details:
            geom = details['geometry']
            print(f"  Geometry type: {geom.get('type')}")
            print(f"  Geometry coordinates: {geom.get('coordinates')}")
        print()
    
    # Check conflicts
    conflicts = list(events.find({'topic': 'chronos.events.airspace.conflict.detected'}).limit(3))
    print(f"Conflict events: {events.count_documents({'topic': 'chronos.events.airspace.conflict.detected'})}")
    if conflicts:
        sample = conflicts[0]
        details = sample.get('payload', {}).get('details', {})
        print(f"  Sample conflict has location: {'conflict_location' in details}")
        if 'conflict_location' in details:
            loc = details['conflict_location']
            print(f"    Location: {loc}")
        print()
    
    print("=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print()
    print("1. Make sure trajectory_insight_agent is running:")
    print("   python agents/trajectory_insight_agent.py")
    print()
    print("2. The map should show:")
    print("   - Aircraft positions (from aircraft.position events)")
    print("   - Conflicts (from geo.incident events with source=trajectory-insight-agent)")
    print("   - Hotspots (from geo.risk_area events with source=trajectory-insight-agent)")
    print()
    print("3. Check browser console (F12) for errors")
    print()
    
    client.close()

if __name__ == "__main__":
    main()

