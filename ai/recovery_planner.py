"""
Recovery Planner Service

Subscribes to power.failure events and automatically generates recovery plans
using Gemini AI (or fallback if API key not set).
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.schema import Severity
from ai.llm_client import get_recovery_plan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Event topics
POWER_FAILURE_TOPIC = "chronos.events.power.failure"
RECOVERY_PLAN_TOPIC = "chronos.events.recovery.plan"


async def _handle_power_failure(topic: str, payload: dict) -> None:
    """
    Handle power.failure events and generate recovery plans.

    Args:
        topic: Event topic
        payload: Event payload
    """
    try:
        event_id = payload.get("event_id")
        sector_id = payload.get("sector_id")
        severity = payload.get("severity")

        logger.info("=" * 60)
        logger.info("POWER FAILURE DETECTED - GENERATING RECOVERY PLAN")
        logger.info("=" * 60)
        logger.info(f"Event ID: {event_id}")
        logger.info(f"Sector: {sector_id}")
        logger.info(f"Severity: {severity}")
        logger.info("=" * 60)

        # Generate recovery plan using Gemini (or fallback)
        logger.info("Generating recovery plan...")
        plan_details = get_recovery_plan(payload)

        logger.info(f"Recovery plan generated: {plan_details.get('plan_id')}")
        logger.info(f"Plan Name: {plan_details.get('plan_name')}")
        logger.info(f"Steps: {len(plan_details.get('steps', []))} steps")
        logger.info(f"Assigned Agents: {', '.join(plan_details.get('assigned_agents', []))}")

        # Create recovery plan event
        recovery_plan_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": Severity.CRITICAL.value if severity == "critical" else Severity.INFO.value,
            "sector_id": sector_id,
            "summary": f"Recovery plan {plan_details.get('plan_id')} generated for {sector_id}",
            "details": plan_details,
        }

        # Log the full plan
        logger.info("=" * 60)
        logger.info("RECOVERY PLAN EVENT")
        logger.info("=" * 60)
        logger.info(f"Plan ID: {plan_details.get('plan_id')}")
        logger.info(f"Plan Name: {plan_details.get('plan_name')}")
        logger.info(f"Status: {plan_details.get('status')}")
        logger.info("Steps:")
        for i, step in enumerate(plan_details.get("steps", []), 1):
            logger.info(f"  {i}. {step}")
        logger.info(f"Estimated Completion: {plan_details.get('estimated_completion')}")
        logger.info(f"Assigned Agents: {', '.join(plan_details.get('assigned_agents', []))}")
        logger.info("=" * 60)
        logger.info(f"Event JSON:\n{json.dumps(recovery_plan_event, indent=2)}")
        logger.info("=" * 60)

        # Publish recovery plan event
        await publish(RECOVERY_PLAN_TOPIC, recovery_plan_event)
        logger.info(f"Published recovery plan to topic: {RECOVERY_PLAN_TOPIC}")

    except Exception as e:
        logger.error(f"Error handling power failure: {e}", exc_info=True)


async def main() -> None:
    """Main entry point for the recovery planner service."""
    logger.info("Starting Recovery Planner Service")
    logger.info("=" * 60)
    logger.info("Configuration:")
    logger.info(f"  Subscribed Topic: {POWER_FAILURE_TOPIC}")
    logger.info(f"  Published Topic: {RECOVERY_PLAN_TOPIC}")
    # Check which LLM provider is configured
    cerebras_key = os.getenv("LLM_SERVICE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if cerebras_key:
        logger.info(f"  Cerebras LLM: Enabled (key: {cerebras_key[:10]}...)")
        logger.info(f"  Model: {os.getenv('LLM_SERVICE_PLANNING_MODEL_NAME', 'openai/zai-glm-4.7')}")
    elif gemini_key:
        logger.info(f"  Gemini API: Enabled (key: {gemini_key[:10]}...)")
    else:
        logger.info("  LLM API: Disabled (using fallback plans)")
    logger.info("=" * 60)

    try:
        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        logger.info("Connected to message broker")

        # Subscribe to power.failure events
        await subscribe(POWER_FAILURE_TOPIC, _handle_power_failure)
        logger.info(f"Subscribed to: {POWER_FAILURE_TOPIC}")

        logger.info("=" * 60)
        logger.info("Recovery Planner is running. Waiting for power failures...")
        logger.info("=" * 60)

        # Keep running
        try:
            await asyncio.Event().wait()  # Wait indefinitely
        except asyncio.CancelledError:
            logger.info("Service cancelled")

        # Disconnect from broker
        await broker.disconnect()
        logger.info("Disconnected from message broker")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

    logger.info("Recovery Planner Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

