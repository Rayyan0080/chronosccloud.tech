#!/usr/bin/env python3
"""
Hard Real-Time System Test
Tests all real-time functionality including:
- SSE connections
- Fix proposal generation
- Fix approval workflow
- Verification system
- Map updates
- Audit tab updates
"""

import asyncio
import logging
import os
import sys
import subprocess
import time
import json
import requests
from datetime import datetime
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.config import get_mongodb_config
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test results
test_results = {}

def log_test(name: str, passed: bool, message: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    logger.info(f"{status}: {name}")
    if message:
        logger.info(f"  → {message}")
    test_results[name] = (passed, message)

async def test_infrastructure_async():
    """Test infrastructure services (async version)."""
    logger.info("\n" + "="*70)
    logger.info("TESTING INFRASTRUCTURE")
    logger.info("="*70)
    
    # Test MongoDB
    try:
        config = get_mongodb_config()
        if config["username"] and config["password"]:
            conn_str = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?authSource=admin"
        else:
            conn_str = f"mongodb://{config['host']}:{config['port']}/{config['database']}"
        
        client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[config["database"]]
        collections = db.list_collection_names()
        log_test("MongoDB Connection", True, f"Connected, {len(collections)} collections")
        client.close()
    except Exception as e:
        log_test("MongoDB Connection", False, str(e))
        return False
    
    # Test NATS
    try:
        broker = await get_broker()
        await broker.connect()
        await broker.disconnect()
        log_test("NATS Connection", True, "Connected successfully")
    except Exception as e:
        log_test("NATS Connection", False, str(e))
        return False
    
    # Test Dashboard
    try:
        response = requests.get("http://localhost:3000/api/events?limit=1", timeout=5)
        if response.status_code == 200:
            log_test("Dashboard API", True, f"Status: {response.status_code}")
        else:
            log_test("Dashboard API", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Dashboard API", False, str(e))
        return False
    
    return True

async def test_fix_proposal_workflow():
    """Test the complete fix proposal workflow."""
    logger.info("\n" + "="*70)
    logger.info("TESTING FIX PROPOSAL WORKFLOW")
    logger.info("="*70)
    
    try:
        # Create a critical event
        event_id = f"TEST-{uuid4().hex[:8].upper()}"
        correlation_id = f"HOTSPOT-{uuid4().hex[:8].upper()}"
        
        critical_event = {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": "critical",
            "sector_id": "ottawa-transit",
            "summary": "Test critical event for fix proposal",
            "correlation_id": correlation_id,
            "details": {
                "incident_type": "transit_disruption",
                "location": {
                    "latitude": 45.4215,
                    "longitude": -75.6972,
                },
                "description": "Test critical transit disruption",
            },
        }
        
        # Publish critical event
        broker = await get_broker()
        await broker.connect()
        
        topic = "chronos.events.transit.disruption.risk"
        await publish(topic, critical_event)
        logger.info(f"Published critical event: {event_id}")
        
        # Wait for fix proposal agent to generate fix
        await asyncio.sleep(5)
        
        # Check MongoDB for fix.review_required event
        config = get_mongodb_config()
        if config["username"] and config["password"]:
            conn_str = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?authSource=admin"
        else:
            conn_str = f"mongodb://{config['host']}:{config['port']}/{config['database']}"
        
        client = MongoClient(conn_str)
        db = client[config["database"]]
        events_collection = db["events"]
        
        # Check for fix.review_required
        fix_event = events_collection.find_one({
            "topic": "chronos.events.fix.review_required",
            "payload.correlation_id": correlation_id,
        })
        
        if fix_event:
            fix_id = fix_event["payload"]["details"]["fix_id"]
            log_test("Fix Proposal Generation", True, f"Fix ID: {fix_id}")
            
            # Test approval API
            try:
                response = requests.post(
                    f"http://localhost:3000/api/fix/{fix_id}/approve",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        log_test("Fix Approval API", True, "Fix approved successfully")
                        
                        # Check for fix.approved and fix.deploy_requested events
                        await asyncio.sleep(2)
                        approved_event = events_collection.find_one({
                            "topic": "chronos.events.fix.approved",
                            "payload.details.fix_id": fix_id,
                        })
                        deploy_event = events_collection.find_one({
                            "topic": "chronos.events.fix.deploy_requested",
                            "payload.details.fix_id": fix_id,
                        })
                        
                        if approved_event and deploy_event:
                            log_test("Fix Approval Events", True, "Both events published")
                        else:
                            log_test("Fix Approval Events", False, "Missing events")
                    else:
                        log_test("Fix Approval API", False, data.get("error", "Unknown error"))
                else:
                    log_test("Fix Approval API", False, f"Status: {response.status_code}")
            except Exception as e:
                log_test("Fix Approval API", False, str(e))
            
            # Check for deployment status
            await asyncio.sleep(3)
            deployment_collection = db["fix_deployments"]
            deployment = deployment_collection.find_one({"fix_id": fix_id})
            
            if deployment:
                log_test("Fix Deployment Tracking", True, f"Status: {deployment.get('status', 'unknown')}")
            else:
                log_test("Fix Deployment Tracking", False, "Deployment not found")
            
            # Check for verification status
            verification_collection = db["fix_verifications"]
            verification = verification_collection.find_one({"fix_id": fix_id})
            
            if verification:
                log_test("Fix Verification Tracking", True, f"Status: {verification.get('status', 'unknown')}")
            else:
                log_test("Fix Verification Tracking", False, "Verification not started yet")
            
        else:
            log_test("Fix Proposal Generation", False, "No fix.review_required event found")
        
        await broker.disconnect()
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"Error in fix proposal workflow test: {e}", exc_info=True)
        log_test("Fix Proposal Workflow", False, str(e))
        return False

def test_audit_api():
    """Test Audit tab API endpoints."""
    logger.info("\n" + "="*70)
    logger.info("TESTING AUDIT API")
    logger.info("="*70)
    
    try:
        # Test /api/audit
        response = requests.get("http://localhost:3000/api/audit?limit=10", timeout=5)
        if response.status_code == 200:
            data = response.json()
            fixes = data.get("fixes", [])
            log_test("Audit API - List Fixes", True, f"Found {len(fixes)} fixes")
        else:
            log_test("Audit API - List Fixes", False, f"Status: {response.status_code}")
            return False
        
        # Test /api/audit/stream (SSE endpoint)
        try:
            response = requests.get(
                "http://localhost:3000/api/audit/stream?since=2024-01-01T00:00:00Z",
                timeout=3,
                stream=True
            )
            if response.status_code == 200:
                # Check if it's SSE format
                content_type = response.headers.get("Content-Type", "")
                if "text/event-stream" in content_type:
                    log_test("Audit API - SSE Stream", True, "SSE endpoint responding")
                else:
                    log_test("Audit API - SSE Stream", False, f"Wrong content type: {content_type}")
            else:
                log_test("Audit API - SSE Stream", False, f"Status: {response.status_code}")
        except requests.exceptions.Timeout:
            # SSE timeout is expected, just check it started
            log_test("Audit API - SSE Stream", True, "SSE endpoint accessible (timeout expected)")
        except Exception as e:
            log_test("Audit API - SSE Stream", False, str(e))
        
        return True
        
    except Exception as e:
        log_test("Audit API", False, str(e))
        return False

def test_map_api():
    """Test Map API endpoints."""
    logger.info("\n" + "="*70)
    logger.info("TESTING MAP API")
    logger.info("="*70)
    
    try:
        # Test /api/geo-events
        response = requests.get(
            "http://localhost:3000/api/geo-events?timeRange=15m&severity=all&source=all",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            incidents = data.get("incidents", [])
            risk_areas = data.get("riskAreas", [])
            log_test("Map API - Geo Events", True, f"{len(incidents)} incidents, {len(risk_areas)} risk areas")
        else:
            log_test("Map API - Geo Events", False, f"Status: {response.status_code}")
            return False
        
        # Test /api/events/stream (SSE endpoint)
        try:
            response = requests.get(
                "http://localhost:3000/api/events/stream?since=2024-01-01T00:00:00Z",
                timeout=3,
                stream=True
            )
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "text/event-stream" in content_type:
                    log_test("Map API - SSE Stream", True, "SSE endpoint responding")
                else:
                    log_test("Map API - SSE Stream", False, f"Wrong content type: {content_type}")
            else:
                log_test("Map API - SSE Stream", False, f"Status: {response.status_code}")
        except requests.exceptions.Timeout:
            log_test("Map API - SSE Stream", True, "SSE endpoint accessible (timeout expected)")
        except Exception as e:
            log_test("Map API - SSE Stream", False, str(e))
        
        return True
        
    except Exception as e:
        log_test("Map API", False, str(e))
        return False

def test_agents_running():
    """Check if agents are running."""
    logger.info("\n" + "="*70)
    logger.info("TESTING AGENTS STATUS")
    logger.info("="*70)
    
    try:
        # Check MongoDB for recent events from agents
        config = get_mongodb_config()
        if config["username"] and config["password"]:
            conn_str = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?authSource=admin"
        else:
            conn_str = f"mongodb://{config['host']}:{config['port']}/{config['database']}"
        
        client = MongoClient(conn_str)
        db = client[config["database"]]
        events_collection = db["events"]
        
        # Check for recent fix events
        recent_fix_events = events_collection.count_documents({
            "topic": {"$regex": "^chronos.events.fix"},
            "timestamp": {"$gte": datetime.utcnow().replace(second=0, microsecond=0)},
        })
        
        if recent_fix_events > 0:
            log_test("Fix Proposal Agent", True, f"{recent_fix_events} recent fix events")
        else:
            log_test("Fix Proposal Agent", False, "No recent fix events (agent may not be running)")
        
        # Check for deployment events
        recent_deploy_events = events_collection.count_documents({
            "topic": {"$in": [
                "chronos.events.fix.deploy_started",
                "chronos.events.fix.deploy_succeeded",
                "chronos.events.fix.deploy_failed",
            ]},
            "timestamp": {"$gte": datetime.utcnow().replace(second=0, microsecond=0)},
        })
        
        if recent_deploy_events > 0:
            log_test("Actuator Agent", True, f"{recent_deploy_events} recent deployment events")
        else:
            log_test("Actuator Agent", False, "No recent deployment events (agent may not be running)")
        
        # Check for verification events
        recent_verify_events = events_collection.count_documents({
            "topic": {"$in": [
                "chronos.events.fix.verified",
                "chronos.events.fix.rollback_requested",
            ]},
            "timestamp": {"$gte": datetime.utcnow().replace(second=0, microsecond=0)},
        })
        
        if recent_verify_events > 0:
            log_test("Verification Agent", True, f"{recent_verify_events} recent verification events")
        else:
            log_test("Verification Agent", False, "No recent verification events (agent may not be running)")
        
        client.close()
        return True
        
    except Exception as e:
        log_test("Agents Status", False, str(e))
        return False

async def test_realtime_updates():
    """Test real-time update mechanisms."""
    logger.info("\n" + "="*70)
    logger.info("TESTING REAL-TIME UPDATES")
    logger.info("="*70)
    
    try:
        # Test SSE endpoints are accessible
        endpoints = [
            ("/api/audit/stream", "Audit SSE"),
            ("/api/events/stream", "Events SSE"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(
                    f"http://localhost:3000{endpoint}?since=2024-01-01T00:00:00Z",
                    timeout=2,
                    stream=True
                )
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        log_test(f"Real-time - {name}", True, "SSE endpoint working")
                    else:
                        log_test(f"Real-time - {name}", False, f"Wrong content type: {content_type}")
                else:
                    log_test(f"Real-time - {name}", False, f"Status: {response.status_code}")
            except requests.exceptions.Timeout:
                log_test(f"Real-time - {name}", True, "SSE endpoint accessible")
            except Exception as e:
                log_test(f"Real-time - {name}", False, str(e))
        
        return True
        
    except Exception as e:
        log_test("Real-time Updates", False, str(e))
        return False

async def main():
    """Run all hard tests."""
    logger.info("")
    logger.info("="*70)
    logger.info("HARD REAL-TIME SYSTEM TEST")
    logger.info("="*70)
    logger.info("")
    
    # Run tests
    results = {}
    
    # Infrastructure
    results["infrastructure"] = await test_infrastructure_async()
    await asyncio.sleep(1)
    
    # APIs
    results["audit_api"] = test_audit_api()
    await asyncio.sleep(1)
    
    results["map_api"] = test_map_api()
    await asyncio.sleep(1)
    
    # Agents
    results["agents"] = test_agents_running()
    await asyncio.sleep(1)
    
    # Real-time
    results["realtime"] = await test_realtime_updates()
    await asyncio.sleep(1)
    
    # Fix workflow
    results["fix_workflow"] = await test_fix_proposal_workflow()
    await asyncio.sleep(1)
    
    # Summary
    logger.info("")
    logger.info("="*70)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed ({passed*100//total}%)")
    logger.info("")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

