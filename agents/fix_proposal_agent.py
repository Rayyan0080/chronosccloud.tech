"""
Fix Proposal Agent

Automatically generates fix proposals for all Critical severity events.
Subscribes to all event topics and triggers fix proposal generation when Critical events are detected.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, subscribe
from agents.shared.constants import (
    ALL_TOPICS,
    FIX_PROPOSED_TOPIC,
    FIX_REVIEW_REQUIRED_TOPIC,
    FIX_APPROVED_TOPIC,
    FIX_REJECTED_TOPIC,
    FIX_DEPLOY_REQUESTED_TOPIC,
    FIX_DEPLOY_STARTED_TOPIC,
    FIX_DEPLOY_SUCCEEDED_TOPIC,
    FIX_DEPLOY_FAILED_TOPIC,
    FIX_VERIFIED_TOPIC,
    FIX_ROLLBACK_REQUESTED_TOPIC,
    FIX_ROLLBACK_SUCCEEDED_TOPIC,
)
from agents.shared.schema import Severity
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_exception,
)
from ai.llm_client import get_fix_proposal_with_fallback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Track processed events to avoid duplicate fix proposals
processed_events = set()


class FixProposalAgent:
    """Automatically generates fix proposals for Critical events."""

    def __init__(self):
        """Initialize the fix proposal agent."""
        self.processed_event_ids = set()

    def _is_critical_event(self, payload: Dict[str, Any]) -> bool:
        """Check if an event has Critical severity."""
        severity = payload.get("severity", "").lower()
        return severity == "critical" or severity == Severity.CRITICAL.value

    async def _handle_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle incoming event and generate fix proposal if Critical."""
        try:
            event_id = payload.get("event_id")
            if not event_id:
                return

            # Skip fix-related events (to avoid infinite loops)
            fix_topics = [
                FIX_PROPOSED_TOPIC,
                FIX_REVIEW_REQUIRED_TOPIC,
                FIX_APPROVED_TOPIC,
                FIX_REJECTED_TOPIC,
                FIX_DEPLOY_REQUESTED_TOPIC,
                FIX_DEPLOY_STARTED_TOPIC,
                FIX_DEPLOY_SUCCEEDED_TOPIC,
                FIX_DEPLOY_FAILED_TOPIC,
                FIX_VERIFIED_TOPIC,
                FIX_ROLLBACK_REQUESTED_TOPIC,
                FIX_ROLLBACK_SUCCEEDED_TOPIC,
            ]
            if topic in fix_topics:
                return

            # Skip if already processed
            if event_id in self.processed_event_ids:
                return

            # Check if event is Critical
            if not self._is_critical_event(payload):
                return

            capture_received_event(topic, event_id, {"severity": payload.get("severity")})

            logger.info("=" * 80)
            logger.info(f"CRITICAL EVENT DETECTED: {topic}")
            logger.info("=" * 80)
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Severity: {payload.get('severity')}")
            logger.info(f"Sector: {payload.get('sector_id', 'unknown')}")
            logger.info(f"Summary: {payload.get('summary', 'N/A')}")
            logger.info("=" * 80)

            # Get correlation ID (use event_id if not provided)
            correlation_id = payload.get("correlation_id") or event_id

            # Generate fix proposal (with automatic fallback)
            logger.info("Generating fix proposal for Critical event...")
            fix_data = await get_fix_proposal_with_fallback(payload, correlation_id)

            if fix_data:
                fix_id = fix_data.get("fix_id", "UNKNOWN")
                logger.info(f"✓ Fix proposal generated: {fix_id}")
                logger.info(f"  Title: {fix_data.get('title', 'N/A')}")
                logger.info(f"  Actions: {len(fix_data.get('actions', []))}")
                logger.info(f"  Risk Level: {fix_data.get('risk_level', 'N/A')}")
            else:
                logger.warning("Failed to generate fix proposal (fallback also failed)")

            # Mark event as processed
            self.processed_event_ids.add(event_id)

            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "event_id": payload.get("event_id")})

    async def run(self) -> None:
        """Main run loop for the fix proposal agent."""
        # Initialize Sentry
        init_sentry()
        capture_startup("fix-proposal-agent")

        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        await broker.connect()
        logger.info("✓ Connected to message broker")

        # Subscribe to all event topics (except fix-related to avoid loops)
        fix_topics = [
            FIX_PROPOSED_TOPIC,
            FIX_REVIEW_REQUIRED_TOPIC,
            FIX_APPROVED_TOPIC,
            FIX_REJECTED_TOPIC,
            FIX_DEPLOY_REQUESTED_TOPIC,
            FIX_DEPLOY_STARTED_TOPIC,
            FIX_DEPLOY_SUCCEEDED_TOPIC,
            FIX_DEPLOY_FAILED_TOPIC,
            FIX_VERIFIED_TOPIC,
            FIX_ROLLBACK_REQUESTED_TOPIC,
            FIX_ROLLBACK_SUCCEEDED_TOPIC,
        ]
        topics_to_subscribe = [t for t in ALL_TOPICS if t not in fix_topics]
        
        logger.info(f"Subscribing to {len(topics_to_subscribe)} event topics (excluding fix events)...")
        for topic in topics_to_subscribe:
            try:
                await subscribe(topic, self._handle_event)
                logger.debug(f"✓ Subscribed to {topic}")
            except Exception as e:
                logger.warning(f"Failed to subscribe to {topic}: {e}")

        logger.info("=" * 80)
        logger.info("FIX PROPOSAL AGENT RUNNING")
        logger.info("=" * 80)
        logger.info("Monitoring all events for Critical severity...")
        logger.info("Automatically generating fix proposals for Critical events")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal. Shutting down...")
        finally:
            await broker.disconnect()
            logger.info("Fix proposal agent stopped")


async def main():
    """Main entry point."""
    agent = FixProposalAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

