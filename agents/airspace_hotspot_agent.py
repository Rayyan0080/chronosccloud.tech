"""
Airspace Hotspot Mitigation Agent

Subscribes to task.airspace.hotspot_mitigation tasks and proposes partial solutions for hotspots.
Part of AGENTIC mode solution generation.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.constants import (
    TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC,
    TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC,
)
from agents.shared.sentry import init_sentry, capture_startup, capture_received_event, capture_published_event, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AirspaceHotspotAgent:
    """Agent that handles hotspot mitigation tasks and proposes partial solutions."""

    async def _handle_hotspot_task(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle hotspot mitigation task and propose partial solution."""
        try:
            task_id = payload.get("details", {}).get("task_id")
            hotspot = payload.get("details", {}).get("hotspot", {})
            correlation_id = payload.get("correlation_id")

            capture_received_event(topic, payload.get("event_id", "unknown"), {"task_id": task_id})

            logger.info("=" * 80)
            logger.info("HOTSPOT MITIGATION TASK RECEIVED")
            logger.info("=" * 80)
            logger.info(f"Task ID: {task_id}")
            logger.info(f"Hotspot ID: {hotspot.get('hotspot_id')}")
            logger.info(f"Affected Flights: {len(hotspot.get('affected_flights', []))}")
            logger.info("=" * 80)

            # Generate partial solution for hotspot
            affected_flights = hotspot.get("affected_flights", [])
            if len(affected_flights) == 0:
                logger.warning("Hotspot has no affected flights, skipping")
                return

            # Partial solution: Speed reduction for first 2 flights
            partial_solution = {
                "task_id": task_id,
                "solution_type": "speed_adjustment",
                "problem_id": hotspot.get("hotspot_id"),
                "affected_flights": affected_flights[:2],
                "proposed_actions": [
                    {
                        "flight_id": flight_id,
                        "action": "speed_reduction",
                        "speed_change_knots": -20,
                        "delay_minutes": 2,
                        "reasoning": "Reduce speed to decrease hotspot density",
                    }
                    for flight_id in affected_flights[:2]
                ],
                "estimated_impact": {
                    "total_delay_minutes": 2,
                    "fuel_impact_percent": 0.8,
                    "affected_passengers": len(affected_flights[:2]) * 150,
                },
                "confidence_score": 0.85,
                "agent_name": "airspace-hotspot-agent",
            }

            # Publish partial solution
            partial_solution_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "airspace-hotspot-agent",
                "severity": "info",
                "sector_id": payload.get("sector_id", "airspace-sector-1"),
                "summary": f"Partial solution for hotspot mitigation task {task_id}",
                "correlation_id": correlation_id,
                "details": partial_solution,
            }

            await publish(TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC, partial_solution_event)
            logger.info(f"Published partial solution for task {task_id}")
            capture_published_event(
                TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC,
                partial_solution_event["event_id"],
                {"task_id": task_id, "solution_type": "speed_adjustment"},
            )

        except Exception as e:
            logger.error(f"Error handling hotspot task: {e}", exc_info=True)
            capture_exception(e, {"service": "airspace_hotspot_agent", "task_id": task_id})

    async def run(self) -> None:
        """Run the hotspot agent."""
        init_sentry("airspace_hotspot_agent")
        capture_startup("airspace_hotspot_agent", {"service_type": "task_agent"})

        logger.info("=" * 80)
        logger.info("AIRSPACE HOTSPOT AGENT")
        logger.info("=" * 80)
        logger.info(f"Subscribed to: {TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC}")
        logger.info("=" * 80)

        try:
            broker = await get_broker()
            logger.info("Connected to message broker")

            await subscribe(TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC, self._handle_hotspot_task)
            logger.info(f"Subscribed to: {TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC}")

            logger.info("=" * 80)
            logger.info("Airspace Hotspot Agent running...")
            logger.info("=" * 80)

            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("Service cancelled")

            await broker.disconnect()
            logger.info("Disconnected from message broker")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            capture_exception(e, {"service": "airspace_hotspot_agent", "error_type": "fatal"})
            raise

        logger.info("Airspace Hotspot Agent stopped")


async def main() -> None:
    """Main entry point."""
    agent = AirspaceHotspotAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

