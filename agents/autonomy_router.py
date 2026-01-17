"""
Autonomy Router Service

Routes recovery plans based on operator autonomy level.
- HIGH autonomy: Automatically executes actions (publishes audit.decision and system.action)
- NORMAL autonomy: Requires approval (publishes approval.required)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.schema import DecisionType, DecisionOutcome, Severity
from agents.shared.sentry import init_sentry, capture_startup, capture_received_event, capture_published_event, capture_exception

# Optional voice output
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from voice.elevenlabs_client import speak_autonomy_takeover
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False
    speak_autonomy_takeover = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Event topics
OPERATOR_STATUS_TOPIC = "chronos.events.operator.status"
RECOVERY_PLAN_TOPIC = "chronos.events.recovery.plan"
AUDIT_DECISION_TOPIC = "chronos.events.audit.decision"
SYSTEM_ACTION_TOPIC = "chronos.events.system.action"
APPROVAL_REQUIRED_TOPIC = "chronos.events.approval.required"

# Autonomy levels
AUTONOMY_NORMAL = "NORMAL"
AUTONOMY_HIGH = "HIGH"

# Agent ID for autonomous decisions
AUTONOMY_AGENT_ID = os.getenv("AUTONOMY_AGENT_ID", "autonomy-router-001")


class AutonomyRouter:
    """Routes actions based on operator autonomy level."""

    def __init__(self):
        """Initialize the autonomy router."""
        self.current_autonomy = AUTONOMY_NORMAL
        self.operator_id = None
        self.operator_name = None
        self.pending_recovery_plans = {}  # Track pending plans for approval

    async def _handle_operator_status(self, topic: str, payload: dict) -> None:
        """
        Handle operator.status events to track autonomy level.

        Args:
            topic: Event topic
            payload: Event payload
        """
        try:
            details = payload.get("details", {})
            autonomy_level = details.get("autonomy_level")

            if autonomy_level:
                old_autonomy = self.current_autonomy
                self.current_autonomy = autonomy_level
                self.operator_id = details.get("operator_id")
                self.operator_name = details.get("operator_name")

                logger.info("=" * 60)
                logger.info("AUTONOMY LEVEL UPDATE")
                logger.info("=" * 60)
                logger.info(f"Operator: {self.operator_name} ({self.operator_id})")
                logger.info(f"Autonomy Level: {old_autonomy} → {self.current_autonomy}")
                logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error handling operator status: {e}", exc_info=True)

    async def _handle_recovery_plan(self, topic: str, payload: dict) -> None:
        """
        Handle recovery.plan events and route based on autonomy level.

        Args:
            topic: Event topic
            payload: Event payload
        """
        try:
            plan_id = payload.get("details", {}).get("plan_id")
            plan_name = payload.get("details", {}).get("plan_name")
            status = payload.get("details", {}).get("status")
            sector_id = payload.get("sector_id")
            event_id = payload.get("event_id")

            logger.info("=" * 60)
            logger.info("RECOVERY PLAN RECEIVED")
            logger.info("=" * 60)
            logger.info(f"Plan ID: {plan_id}")
            logger.info(f"Plan Name: {plan_name}")
            logger.info(f"Status: {status}")
            logger.info(f"Sector: {sector_id}")
            logger.info(f"Current Autonomy: {self.current_autonomy}")
            logger.info("=" * 60)

            # Only process draft or active plans
            if status not in ["draft", "active"]:
                logger.info(f"Skipping plan {plan_id} with status: {status}")
                return

            if self.current_autonomy == AUTONOMY_HIGH:
                # High autonomy: Automatically execute
                await self._execute_autonomous_action(plan_id, plan_name, sector_id, event_id)
            else:
                # Normal autonomy: Require approval
                await self._request_approval(plan_id, plan_name, sector_id, event_id)

        except Exception as e:
            logger.error(f"Error handling recovery plan: {e}", exc_info=True)

    async def _execute_autonomous_action(
        self, plan_id: str, plan_name: str, sector_id: str, related_event_id: str
    ) -> None:
        """
        Execute action autonomously (HIGH autonomy mode).

        Publishes audit.decision and system.action events.

        Args:
            plan_id: Recovery plan ID
            plan_name: Recovery plan name
            sector_id: Sector identifier
            related_event_id: Related event ID
        """
        try:
            decision_id = f"DEC-{datetime.utcnow().year}-{str(uuid4())[:8].upper()}"
            action = f"execute_recovery_plan_{plan_id}"

            # Publish audit.decision event
            audit_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Autonomous decision to execute recovery plan: {plan_name}",
                "details": {
                    "decision_id": decision_id,
                    "decision_type": DecisionType.AUTOMATED.value,
                    "decision_maker": AUTONOMY_AGENT_ID,
                    "action": action,
                    "reasoning": f"High autonomy mode active. Automatically executing recovery plan {plan_id}.",
                    "outcome": DecisionOutcome.PENDING.value,
                    "related_events": [related_event_id],
                },
            }

            logger.info("Publishing audit.decision event (HIGH autonomy)")
            logger.info(f"Decision ID: {decision_id}")
            logger.info(f"Action: {action}")
            await publish(AUDIT_DECISION_TOPIC, audit_event)
            logger.info(f"Published to: {AUDIT_DECISION_TOPIC}")

            # Publish system.action event
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"System executing recovery plan: {plan_name}",
                "details": {
                    "action_type": "execute_recovery_plan",
                    "plan_id": plan_id,
                    "plan_name": plan_name,
                    "executor": AUTONOMY_AGENT_ID,
                    "autonomy_level": AUTONOMY_HIGH,
                    "status": "executing",
                    "decision_id": decision_id,
                    "related_events": [related_event_id, audit_event["event_id"]],
                },
            }

            logger.info("Publishing system.action event")
            logger.info(f"Action: execute_recovery_plan")
            logger.info(f"Plan: {plan_name}")
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            logger.info(f"Published to: {SYSTEM_ACTION_TOPIC}")
            
            # Voice announcement (optional)
            if VOICE_ENABLED and speak_autonomy_takeover:
                try:
                    speak_autonomy_takeover(plan_name, sector_id)
                except Exception as e:
                    logger.warning(f"Voice announcement failed: {e}")
            
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error executing autonomous action: {e}", exc_info=True)

    async def _request_approval(
        self, plan_id: str, plan_name: str, sector_id: str, related_event_id: str
    ) -> None:
        """
        Request approval for action (NORMAL autonomy mode).

        Publishes approval.required event.

        Args:
            plan_id: Recovery plan ID
            plan_name: Recovery plan name
            sector_id: Sector identifier
            related_event_id: Related event ID
        """
        try:
            approval_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": Severity.WARNING.value,
                "sector_id": sector_id,
                "summary": f"Approval required for recovery plan: {plan_name}",
                "details": {
                    "approval_id": f"APP-{datetime.utcnow().year}-{str(uuid4())[:8].upper()}",
                    "plan_id": plan_id,
                    "plan_name": plan_name,
                    "requested_by": AUTONOMY_AGENT_ID,
                    "operator_id": self.operator_id,
                    "operator_name": self.operator_name,
                    "status": "pending",
                    "autonomy_level": AUTONOMY_NORMAL,
                    "action_required": f"execute_recovery_plan_{plan_id}",
                    "related_events": [related_event_id],
                    "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
                },
            }

            # Store pending plan
            self.pending_recovery_plans[plan_id] = approval_event

            logger.info("Publishing approval.required event (NORMAL autonomy)")
            logger.info(f"Approval ID: {approval_event['details']['approval_id']}")
            logger.info(f"Plan: {plan_name}")
            logger.info(f"Operator: {self.operator_name} ({self.operator_id})")
            await publish(APPROVAL_REQUIRED_TOPIC, approval_event)
            logger.info(f"Published to: {APPROVAL_REQUIRED_TOPIC}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error requesting approval: {e}", exc_info=True)

    async def run(self) -> None:
        """Run the autonomy router service."""
        logger.info("Starting Autonomy Router Service")
        logger.info("=" * 60)
        logger.info("Configuration:")
        logger.info(f"  Agent ID: {AUTONOMY_AGENT_ID}")
        logger.info(f"  Initial Autonomy: {self.current_autonomy}")
        logger.info("=" * 60)
        logger.info("Subscribed Topics:")
        logger.info(f"  - {OPERATOR_STATUS_TOPIC}")
        logger.info(f"  - {RECOVERY_PLAN_TOPIC}")
        logger.info("=" * 60)

        try:
            # Connect to message broker
            logger.info("Connecting to message broker...")
            broker = await get_broker()
            logger.info("Connected to message broker")

            # Subscribe to operator.status events
            await subscribe(OPERATOR_STATUS_TOPIC, self._handle_operator_status)
            logger.info(f"Subscribed to: {OPERATOR_STATUS_TOPIC}")

            # Subscribe to recovery.plan events
            await subscribe(RECOVERY_PLAN_TOPIC, self._handle_recovery_plan)
            logger.info(f"Subscribed to: {RECOVERY_PLAN_TOPIC}")

            logger.info("=" * 60)
            logger.info("Autonomy Router is running. Waiting for events...")
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
            capture_exception(e, {"service": "autonomy_router", "error_type": "fatal"})
            raise

        logger.info("Autonomy Router Service stopped")


async def main() -> None:
    """Main entry point for the autonomy router service."""
    router = AutonomyRouter()
    await router.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        import sys

        sys.exit(0)

