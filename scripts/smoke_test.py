#!/usr/bin/env python3
"""
Smoke Test Script for Project Chronos

Tests all API integrations to ensure:
- No uncaught exceptions
- Proper fallbacks work
- Services can start and connect
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.health_report import print_startup_health_report, get_health_summary
from ai.llm_client import get_recovery_plan
from agents.shared.sentry import init_sentry
from agents.shared.secret_masker import mask_dict_secrets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_broker_connection():
    """Test broker connection."""
    logger.info("=" * 60)
    logger.info("TEST: Broker Connection")
    logger.info("=" * 60)
    try:
        broker = await get_broker()
        is_connected = await broker.is_connected()
        if is_connected:
            logger.info("✅ Broker connection: SUCCESS")
            return True
        else:
            logger.error("❌ Broker connection: FAILED (not connected)")
            return False
    except Exception as e:
        logger.error(f"❌ Broker connection: FAILED ({e})")
        return False


async def test_event_publish():
    """Test event publishing."""
    logger.info("=" * 60)
    logger.info("TEST: Event Publishing")
    logger.info("=" * 60)
    try:
        test_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": "info",
            "sector_id": "test-sector",
            "summary": "Smoke test event",
            "details": {"test": True},
        }
        await publish("chronos.events.test.smoke", test_event)
        logger.info("✅ Event publishing: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ Event publishing: FAILED ({e})")
        return False


def test_llm_planner():
    """Test LLM planner (with fallback)."""
    logger.info("=" * 60)
    logger.info("TEST: LLM Planner")
    logger.info("=" * 60)
    try:
        test_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": "critical",
            "sector_id": "test-sector",
            "summary": "Test power failure",
            "details": {"voltage": 0.0, "load": 100.0},
        }
        plan = get_recovery_plan(test_event)
        
        # Validate plan structure
        required_fields = ["plan_id", "plan_name", "status", "steps"]
        missing = [f for f in required_fields if f not in plan]
        
        if missing:
            logger.error(f"❌ LLM Planner: FAILED (missing fields: {missing})")
            return False
        
        logger.info(f"✅ LLM Planner: SUCCESS (plan_id: {plan.get('plan_id')})")
        return True
    except Exception as e:
        logger.error(f"❌ LLM Planner: FAILED ({e})")
        return False


def test_sentry():
    """Test Sentry initialization."""
    logger.info("=" * 60)
    logger.info("TEST: Sentry Initialization")
    logger.info("=" * 60)
    try:
        init_sentry("smoke_test", "NORMAL")
        logger.info("✅ Sentry initialization: SUCCESS (or skipped if DSN not set)")
        return True
    except Exception as e:
        logger.error(f"❌ Sentry initialization: FAILED ({e})")
        return False


async def main():
    """Run all smoke tests."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("SMOKE TEST SUITE - Project Chronos")
    logger.info("=" * 70)
    logger.info("")
    
    # Print health report
    print_startup_health_report("smoke_test")
    
    # Get health summary
    health = get_health_summary()
    logger.info("Configuration Summary:")
    for key, value in health.items():
        logger.info(f"  {key}: {value}")
    logger.info("")
    
    # Run tests
    results = {}
    
    # Test 1: Broker connection
    results["broker"] = await test_broker_connection()
    await asyncio.sleep(1)
    
    # Test 2: Event publishing
    results["publish"] = await test_event_publish()
    await asyncio.sleep(1)
    
    # Test 3: LLM planner
    results["llm"] = test_llm_planner()
    await asyncio.sleep(1)
    
    # Test 4: Sentry
    results["sentry"] = test_sentry()
    await asyncio.sleep(1)
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("SMOKE TEST RESULTS")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ All smoke tests passed!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Smoke test interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in smoke test: {e}", exc_info=True)
        sys.exit(1)

