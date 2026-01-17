"""
Airspace Deconflict Agent

Subscribes to task.airspace.deconflict tasks and proposes partial solutions for conflicts.
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
    TASK_AIRSPACE_DECONFLICT_TOPIC,
    TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC,
)
from agents.shared.sentry import init_sentry, capture_startup, capture_received_event, capture_published_event, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AirspaceDeconflictAgent:
    """Agent that handles deconflict tasks and proposes partial solutions."""

    async def _handle_deconflict_task(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle deconflict task and propose partial solution."""
        try:
            task_id = payload.get("details", {}).get("task_id")
            conflict = payload.get("details", {}).get("conflict", {})
            correlation_id = payload.get("correlation_id")

            capture_received_event(topic, payload.get("event_id", "unknown"), {"task_id": task_id})

            logger.info("=" * 80)
            logger.info("DECONFLICT TASK RECEIVED")
            logger.info("=" * 80)
            logger.info(f"Task ID: {task_id}")
            logger.info(f"Conflict ID: {conflict.get('conflict_id')}")
            logger.info(f"Flight IDs: {conflict.get('flight_ids', [])}")
            logger.info("=" * 80)

            # Generate partial solution for conflict
            flight_ids = conflict.get("flight_ids", [])
            if len(flight_ids) < 2:
                logger.warning("Conflict has less than 2 flights, skipping")
                return

            # Partial solution: Altitude change for first flight
            partial_solution = {
                "task_id": task_id,
                "solution_type": "altitude_change",
                "problem_id": conflict.get("conflict_id"),
                "affected_flights": [flight_ids[0]],
                "proposed_actions": [
                    {
                        "flight_id": flight_ids[0],
                        "action": "altitude_change",
                        "new_altitude": 37000,  # Increase by 2000 feet
                        "delay_minutes": 0,
                        "reasoning": "Increase altitude to create vertical separation",
                    }
                ],
                "estimated_impact": {
                    "total_delay_minutes": 0,
                    "fuel_impact_percent": 0.5,
                    "affected_passengers": 150,
                },
                "confidence_score": 0.90,
                "agent_name": "airspace-deconflict-agent",
            }

            # Publish partial solution
            partial_solution_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "airspace-deconflict-agent",
                "severity": "info",
                "sector_id": payload.get("sector_id", "airspace-sector-1"),
                "summary": f"Partial solution for deconflict task {task_id}",
                "correlation_id": correlation_id,
                "details": partial_solution,
            }

            await publish(TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC, partial_solution_event)
            logger.info(f"Published partial solution for task {task_id}")
            capture_published_event(
                TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC,
                partial_solution_event["event_id"],
                {"task_id": task_id, "solution_type": "altitude_change"},
            )

        except Exception as e:
            logger.error(f"Error handling deconflict task: {e}", exc_info=True)
            capture_exception(e, {"service": "airspace_deconflict_agent", "task_id": task_id})

    async def run(self) -> None:
        """Run the deconflict agent."""
        init_sentry("airspace_deconflict_agent")
        capture_startup("airspace_deconflict_agent", {"service_type": "task_agent"})

        logger.info("=" * 80)
        logger.info("AIRSPACE DECONFLICT AGENT")
        logger.info("=" * 80)
        logger.info(f"Subscribed to: {TASK_AIRSPACE_DECONFLICT_TOPIC}")
        logger.info("=" * 80)

        try:
            broker = await get_broker()
            logger.info("Connected to message broker")

            await subscribe(TASK_AIRSPACE_DECONFLICT_TOPIC, self._handle_deconflict_task)
            logger.info(f"Subscribed to: {TASK_AIRSPACE_DECONFLICT_TOPIC}")

            logger.info("=" * 80)
            logger.info("Airspace Deconflict Agent running...")
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
            capture_exception(e, {"service": "airspace_deconflict_agent", "error_type": "fatal"})
            raise

        logger.info("Airspace Deconflict Agent stopped")


async def main() -> None:
    """Main entry point."""
    agent = AirspaceDeconflictAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

