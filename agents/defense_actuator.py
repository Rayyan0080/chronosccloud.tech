"""
Defense Actuator Agent

Subscribes to defense.action.approved events and executes defense actions in a safe sandbox.
Publishes defense.action.deployed events.

IMPORTANT: All actions are simulated only. Never interfaces with real weapons or enforcement systems.
"""

import asyncio
import logging
import os
import sys
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.config import get_mongodb_config
from agents.shared.constants import (
    DEFENSE_ACTION_APPROVED_TOPIC,
    DEFENSE_ACTION_DEPLOYED_TOPIC,
    SYSTEM_ACTION_TOPIC,
)
from agents.shared.schema import Severity
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_published_event,
    capture_exception,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB configuration
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "events")
DEPLOYMENT_STATUS_COLLECTION = os.getenv("DEFENSE_DEPLOYMENT_STATUS_COLLECTION", "defense_deployments")

# Supported action types (parsed from AI assessment strings)
ACTION_INCREASE_ALERT_LEVEL = "increase_alert_level"
ACTION_RESTRICT_MAP_VISIBILITY = "restrict_map_visibility"
ACTION_TRIGGER_PUBLIC_ADVISORY = "trigger_public_advisory"
ACTION_INCREASE_MONITORING = "increase_monitoring"
ACTION_LOCK_AUTONOMY = "lock_autonomy"


class DefenseActuatorAgent:
    """Executes defense actions in a safe sandbox."""

    def __init__(self):
        """Initialize the defense actuator agent."""
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_collection = None
        self.deployment_collection = None
        self.connected = False

    async def _connect_mongodb(self) -> None:
        """Connect to MongoDB and create indexes."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure

            config = get_mongodb_config()

            # Build connection string
            if config["username"] and config["password"]:
                connection_string = (
                    f"mongodb://{config['username']}:{config['password']}"
                    f"@{config['host']}:{config['port']}/{config['database']}"
                    f"?authSource=admin"
                )
            else:
                connection_string = (
                    f"mongodb://{config['host']}:{config['port']}/{config['database']}"
                )

            logger.info(f"Connecting to MongoDB at {config['host']}:{config['port']}...")

            # Connect to MongoDB
            self.mongo_client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )

            # Test connection
            self.mongo_client.admin.command("ping")
            self.mongo_db = self.mongo_client[config["database"]]
            self.mongo_collection = self.mongo_db[MONGO_COLLECTION]
            self.deployment_collection = self.mongo_db[DEPLOYMENT_STATUS_COLLECTION]

            # Create indexes for deployment status
            self.deployment_collection.create_index("action_id", unique=True)
            self.deployment_collection.create_index("status")
            self.deployment_collection.create_index("deployed_at")

            self.connected = True
            logger.info("✓ Connected to MongoDB")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.connected = False
            raise
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.connected = False
            raise

    async def _check_deployment_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if an action has already been deployed (idempotency check).
        
        Returns:
            Deployment status document if exists, None otherwise
        """
        if not self.connected:
            return None

        try:
            deployment = self.deployment_collection.find_one({"action_id": action_id})
            return deployment
        except Exception as e:
            logger.error(f"Error checking deployment status: {e}")
            return None

    async def _record_deployment_start(self, action_id: str, action_details: Dict[str, Any]) -> None:
        """Record that deployment has started."""
        if not self.connected:
            return

        try:
            self.deployment_collection.update_one(
                {"action_id": action_id},
                {
                    "$set": {
                        "action_id": action_id,
                        "status": "started",
                        "action_details": action_details,
                        "deployed_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Error recording deployment start: {e}")
            capture_exception(e, {"action_id": action_id, "operation": "record_deployment_start"})

    async def _record_deployment_success(
        self, action_id: str, actions_executed: List[Dict[str, Any]]
    ) -> None:
        """Record successful deployment."""
        if not self.connected:
            return

        try:
            self.deployment_collection.update_one(
                {"action_id": action_id},
                {
                    "$set": {
                        "status": "succeeded",
                        "actions_executed": actions_executed,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception as e:
            logger.error(f"Error recording deployment success: {e}")
            capture_exception(e, {"action_id": action_id, "operation": "record_deployment_success"})

    async def _record_deployment_failure(self, action_id: str, error: str) -> None:
        """Record failed deployment."""
        if not self.connected:
            return

        try:
            self.deployment_collection.update_one(
                {"action_id": action_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": error,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception as e:
            logger.error(f"Error recording deployment failure: {e}")
            capture_exception(e, {"action_id": action_id, "operation": "record_deployment_failure"})

    def _parse_action_string(self, action_string: str) -> Optional[str]:
        """
        Parse an action string from AI assessment and map it to an action type.
        
        Args:
            action_string: Action description string from AI assessment
            
        Returns:
            Action type constant or None if unrecognized
        """
        action_lower = action_string.lower()
        
        # Map common phrases to action types
        if any(phrase in action_lower for phrase in ["increase alert", "raise alert", "elevate alert", "alert level"]):
            return ACTION_INCREASE_ALERT_LEVEL
        elif any(phrase in action_lower for phrase in ["restrict map", "limit map", "map visibility", "restrict visibility"]):
            return ACTION_RESTRICT_MAP_VISIBILITY
        elif any(phrase in action_lower for phrase in ["public advisory", "public alert", "advisory", "notify public"]):
            return ACTION_TRIGGER_PUBLIC_ADVISORY
        elif any(phrase in action_lower for phrase in ["increase monitoring", "enhance monitoring", "more monitoring", "monitoring frequency"]):
            return ACTION_INCREASE_MONITORING
        elif any(phrase in action_lower for phrase in ["lock autonomy", "human only", "disable autonomy", "require human"]):
            return ACTION_LOCK_AUTONOMY
        else:
            logger.warning(f"Unrecognized action string: {action_string}")
            return None

    async def _execute_increase_alert_level(
        self, action_string: str, threat_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute increase alert level action (SANDBOX ONLY)."""
        try:
            # Extract area from action string if mentioned
            area_match = re.search(r"(?:for|in|area|region|sector)\s+([A-Za-z0-9\s-]+)", action_string, re.IGNORECASE)
            area = area_match.group(1).strip() if area_match else sector_id

            # Create system action event (SANDBOX - simulated only)
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": "defense-actuator-agent",
                "severity": Severity.WARNING.value,
                "sector_id": sector_id,
                "summary": f"Alert level increased for {area} (SANDBOX - simulated only)",
                "correlation_id": threat_id,
                "details": {
                    "action_type": ACTION_INCREASE_ALERT_LEVEL,
                    "action_description": action_string,
                    "area": area,
                    "threat_id": threat_id,
                    "simulation_mode": True,  # SAFE SANDBOX
                    "sandbox_only": True,
                    "disclaimer": "This is a simulated action. No real systems were modified.",
                },
            }

            # Publish event
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"action_type": ACTION_INCREASE_ALERT_LEVEL, "threat_id": threat_id},
            )

            # Store in MongoDB
            if self.connected:
                try:
                    self.mongo_collection.insert_one({
                        "topic": SYSTEM_ACTION_TOPIC,
                        "payload": system_action_event,
                        "timestamp": datetime.now(timezone.utc),
                        "logged_at": datetime.now(timezone.utc),
                        "simulation_mode": True,
                        "action_id": threat_id,
                    })
                except Exception as e:
                    logger.warning(f"Failed to store alert level action in MongoDB: {e}")

            logger.info(f"✓ Alert level increased for {area} (SANDBOX - {threat_id})")
            return {"success": True, "action": ACTION_INCREASE_ALERT_LEVEL, "area": area}

        except Exception as e:
            logger.error(f"Error executing increase alert level: {e}")
            capture_exception(e, {"threat_id": threat_id, "action_type": ACTION_INCREASE_ALERT_LEVEL})
            return {"success": False, "error": str(e)}

    async def _execute_restrict_map_visibility(
        self, action_string: str, threat_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute restrict map visibility action (SANDBOX ONLY)."""
        try:
            # Create system action event (SANDBOX - simulated only)
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": "defense-actuator-agent",
                "severity": Severity.WARNING.value,
                "sector_id": sector_id,
                "summary": "Map visibility restricted to high-priority operators (SANDBOX - simulated only)",
                "correlation_id": threat_id,
                "details": {
                    "action_type": ACTION_RESTRICT_MAP_VISIBILITY,
                    "action_description": action_string,
                    "threat_id": threat_id,
                    "simulation_mode": True,  # SAFE SANDBOX
                    "sandbox_only": True,
                    "disclaimer": "This is a simulated action. No real systems were modified.",
                },
            }

            # Publish event
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"action_type": ACTION_RESTRICT_MAP_VISIBILITY, "threat_id": threat_id},
            )

            logger.info(f"✓ Map visibility restricted (SANDBOX - {threat_id})")
            return {"success": True, "action": ACTION_RESTRICT_MAP_VISIBILITY}

        except Exception as e:
            logger.error(f"Error executing restrict map visibility: {e}")
            capture_exception(e, {"threat_id": threat_id, "action_type": ACTION_RESTRICT_MAP_VISIBILITY})
            return {"success": False, "error": str(e)}

    async def _execute_trigger_public_advisory(
        self, action_string: str, threat_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute trigger public advisory action (SANDBOX ONLY)."""
        try:
            # Extract advisory message from action string if mentioned
            message_match = re.search(r"(?:advisory|alert|message|notify):\s*(.+)", action_string, re.IGNORECASE)
            advisory_message = message_match.group(1).strip() if message_match else "Public safety advisory issued (simulated)"

            # Create system action event (SANDBOX - simulated only)
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": "defense-actuator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Public advisory triggered (SANDBOX - simulated only): {advisory_message}",
                "correlation_id": threat_id,
                "details": {
                    "action_type": ACTION_TRIGGER_PUBLIC_ADVISORY,
                    "action_description": action_string,
                    "advisory_message": advisory_message,
                    "threat_id": threat_id,
                    "simulation_mode": True,  # SAFE SANDBOX
                    "sandbox_only": True,
                    "disclaimer": "This is a simulated action. No real public advisories were issued.",
                },
            }

            # Publish event
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"action_type": ACTION_TRIGGER_PUBLIC_ADVISORY, "threat_id": threat_id},
            )

            logger.info(f"✓ Public advisory triggered (SANDBOX - {threat_id}): {advisory_message}")
            return {"success": True, "action": ACTION_TRIGGER_PUBLIC_ADVISORY, "message": advisory_message}

        except Exception as e:
            logger.error(f"Error executing trigger public advisory: {e}")
            capture_exception(e, {"threat_id": threat_id, "action_type": ACTION_TRIGGER_PUBLIC_ADVISORY})
            return {"success": False, "error": str(e)}

    async def _execute_increase_monitoring(
        self, action_string: str, threat_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute increase monitoring frequency action (SANDBOX ONLY)."""
        try:
            # Extract monitoring frequency from action string if mentioned
            freq_match = re.search(r"(?:frequency|rate|interval|every)\s+(\d+)\s*(\w+)", action_string, re.IGNORECASE)
            frequency = freq_match.group(1) + " " + freq_match.group(2) if freq_match else "2x normal"

            # Create system action event (SANDBOX - simulated only)
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": "defense-actuator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Monitoring frequency increased to {frequency} (SANDBOX - simulated only)",
                "correlation_id": threat_id,
                "details": {
                    "action_type": ACTION_INCREASE_MONITORING,
                    "action_description": action_string,
                    "monitoring_frequency": frequency,
                    "threat_id": threat_id,
                    "simulation_mode": True,  # SAFE SANDBOX
                    "sandbox_only": True,
                    "disclaimer": "This is a simulated action. No real monitoring systems were modified.",
                },
            }

            # Publish event
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"action_type": ACTION_INCREASE_MONITORING, "threat_id": threat_id},
            )

            logger.info(f"✓ Monitoring frequency increased to {frequency} (SANDBOX - {threat_id})")
            return {"success": True, "action": ACTION_INCREASE_MONITORING, "frequency": frequency}

        except Exception as e:
            logger.error(f"Error executing increase monitoring: {e}")
            capture_exception(e, {"threat_id": threat_id, "action_type": ACTION_INCREASE_MONITORING})
            return {"success": False, "error": str(e)}

    async def _execute_lock_autonomy(
        self, action_string: str, threat_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute lock autonomy to human-only action (SANDBOX ONLY)."""
        try:
            # Create system action event (SANDBOX - simulated only)
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": "defense-actuator-agent",
                "severity": Severity.WARNING.value,
                "sector_id": sector_id,
                "summary": "Autonomy locked to human-only mode (SANDBOX - simulated only)",
                "correlation_id": threat_id,
                "details": {
                    "action_type": ACTION_LOCK_AUTONOMY,
                    "action_description": action_string,
                    "autonomy_level": "human_only",
                    "threat_id": threat_id,
                    "simulation_mode": True,  # SAFE SANDBOX
                    "sandbox_only": True,
                    "disclaimer": "This is a simulated action. No real autonomy systems were modified.",
                },
            }

            # Publish event
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"action_type": ACTION_LOCK_AUTONOMY, "threat_id": threat_id},
            )

            logger.info(f"✓ Autonomy locked to human-only (SANDBOX - {threat_id})")
            return {"success": True, "action": ACTION_LOCK_AUTONOMY}

        except Exception as e:
            logger.error(f"Error executing lock autonomy: {e}")
            capture_exception(e, {"threat_id": threat_id, "action_type": ACTION_LOCK_AUTONOMY})
            return {"success": False, "error": str(e)}

    async def _execute_action(
        self, action_string: str, threat_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute a single defense action based on its type."""
        action_type = self._parse_action_string(action_string)

        if action_type == ACTION_INCREASE_ALERT_LEVEL:
            return await self._execute_increase_alert_level(action_string, threat_id, sector_id)
        elif action_type == ACTION_RESTRICT_MAP_VISIBILITY:
            return await self._execute_restrict_map_visibility(action_string, threat_id, sector_id)
        elif action_type == ACTION_TRIGGER_PUBLIC_ADVISORY:
            return await self._execute_trigger_public_advisory(action_string, threat_id, sector_id)
        elif action_type == ACTION_INCREASE_MONITORING:
            return await self._execute_increase_monitoring(action_string, threat_id, sector_id)
        elif action_type == ACTION_LOCK_AUTONOMY:
            return await self._execute_lock_autonomy(action_string, threat_id, sector_id)
        else:
            logger.warning(f"Unknown or unrecognized action: {action_string}")
            return {"success": False, "error": f"Unknown action: {action_string}"}

    async def _publish_deploy_succeeded(
        self,
        action_id: str,
        threat_id: str,
        sector_id: str,
        actions_executed: List[Dict[str, Any]],
    ) -> None:
        """Publish defense.action.deployed event."""
        deploy_succeeded_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "defense-actuator-agent",
            "severity": Severity.INFO.value,
            "sector_id": sector_id,
            "summary": f"Defense action {action_id} deployed successfully (SANDBOX)",
            "correlation_id": threat_id,
            "details": {
                "action_id": action_id,
                "threat_id": threat_id,
                "deployment_status": "success",
                "deployed_by": "defense-actuator-agent",
                "deployed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "deployment_notes": f"Deployed {len(actions_executed)} protective actions in sandbox",
                "actions_executed": actions_executed,
                "simulation_mode": True,  # SAFE SANDBOX
                "sandbox_only": True,
            },
        }

        await publish(DEFENSE_ACTION_DEPLOYED_TOPIC, deploy_succeeded_event)
        capture_published_event(
            DEFENSE_ACTION_DEPLOYED_TOPIC,
            deploy_succeeded_event["event_id"],
            {"action_id": action_id, "threat_id": threat_id},
        )
        logger.info(f"Published defense.action.deployed for {action_id}")

    async def _publish_deploy_failed(
        self, action_id: str, threat_id: str, sector_id: str, error: str
    ) -> None:
        """Publish defense.action.deployed event with failed status."""
        deploy_failed_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "defense-actuator-agent",
            "severity": Severity.CRITICAL.value,
            "sector_id": sector_id,
            "summary": f"Defense action {action_id} deployment failed: {error}",
            "correlation_id": threat_id,
            "details": {
                "action_id": action_id,
                "threat_id": threat_id,
                "deployment_status": "failed",
                "deployed_by": "defense-actuator-agent",
                "deployed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "deployment_notes": f"Deployment failed: {error}",
            },
        }

        await publish(DEFENSE_ACTION_DEPLOYED_TOPIC, deploy_failed_event)
        capture_published_event(
            DEFENSE_ACTION_DEPLOYED_TOPIC,
            deploy_failed_event["event_id"],
            {"action_id": action_id, "threat_id": threat_id},
        )
        logger.error(f"Published defense.action.deployed (failed) for {action_id}: {error}")

    async def _handle_action_approved(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle defense.action.approved event."""
        try:
            capture_received_event(topic, payload.get("event_id", "unknown"))

            action_details = payload.get("details", {})
            action_id = action_details.get("action_id")
            threat_id = action_details.get("threat_id")
            protective_actions = action_details.get("protective_actions", [])
            sector_id = payload.get("sector_id", "unknown")

            if not action_id:
                logger.error("Missing action_id in defense.action.approved event")
                return

            if not threat_id:
                logger.error("Missing threat_id in defense.action.approved event")
                return

            if not protective_actions or len(protective_actions) == 0:
                logger.warning(f"No protective actions in approved event for action {action_id}")
                # Still publish deployed event with empty actions
                await self._publish_deploy_succeeded(action_id, threat_id, sector_id, [])
                return

            logger.info("=" * 80)
            logger.info(f"DEFENSE ACTION APPROVED: Action {action_id} for Threat {threat_id}")
            logger.info(f"Protective Actions: {len(protective_actions)}")
            logger.info("=" * 80)

            # IDEMPOTENCY CHECK: Check if already deployed
            existing_deployment = await self._check_deployment_status(action_id)
            if existing_deployment:
                status = existing_deployment.get("status")
                if status in ["started", "succeeded"]:
                    logger.warning(
                        f"Action {action_id} already deployed (status: {status}). Skipping deployment (idempotent)."
                    )
                    return
                elif status == "failed":
                    logger.info(f"Action {action_id} previously failed. Retrying deployment...")

            # Record deployment start
            await self._record_deployment_start(action_id, action_details)

            # Execute all protective actions
            actions_executed = []
            errors = []

            for i, action_string in enumerate(protective_actions):
                logger.info(f"Executing protective action {i+1}/{len(protective_actions)}: {action_string}")
                result = await self._execute_action(action_string, threat_id, sector_id)
                
                if result.get("success"):
                    actions_executed.append({
                        "action_index": i,
                        "action_string": action_string,
                        "result": result,
                    })
                    logger.info(f"✓ Action {i+1} executed successfully")
                else:
                    error_msg = result.get("error", "Unknown error")
                    errors.append(f"Action {i+1}: {error_msg}")
                    logger.error(f"✗ Action {i+1} failed: {error_msg}")

            # Determine overall deployment status
            if len(errors) == 0:
                # All actions succeeded
                await self._record_deployment_success(action_id, actions_executed)
                await self._publish_deploy_succeeded(action_id, threat_id, sector_id, actions_executed)
                logger.info(f"✓ All {len(actions_executed)} defense actions deployed successfully (SANDBOX)")
            elif len(actions_executed) > 0:
                # Partial success
                error_summary = "; ".join(errors)
                await self._record_deployment_failure(action_id, f"Partial failure: {error_summary}")
                await self._publish_deploy_failed(action_id, threat_id, sector_id, f"Partial failure: {error_summary}")
                logger.warning(f"⚠ Partial deployment: {len(actions_executed)}/{len(protective_actions)} actions succeeded")
            else:
                # All actions failed
                error_summary = "; ".join(errors)
                await self._record_deployment_failure(action_id, error_summary)
                await self._publish_deploy_failed(action_id, threat_id, sector_id, error_summary)
                logger.error(f"✗ All defense actions failed: {error_summary}")

        except Exception as e:
            logger.error(f"Error handling defense.action.approved: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "payload": payload})
            
            # Try to publish failure event
            try:
                action_id = payload.get("details", {}).get("action_id", "unknown")
                threat_id = payload.get("details", {}).get("threat_id", "unknown")
                sector_id = payload.get("sector_id", "unknown")
                await self._publish_deploy_failed(action_id, threat_id, sector_id, str(e))
            except:
                pass

    async def run(self) -> None:
        """Run the defense actuator agent."""
        logger.info("=" * 80)
        logger.info("DEFENSE ACTUATOR AGENT STARTING")
        logger.info("=" * 80)
        logger.info("⚠️  SANDBOX MODE: All actions are simulated only")
        logger.info("⚠️  Never interfaces with real weapons or enforcement systems")
        logger.info("=" * 80)

        init_sentry("defense_actuator")
        capture_startup("defense_actuator")

        try:
            # Connect to MongoDB
            await self._connect_mongodb()
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.warning("Continuing without MongoDB (deployment status tracking disabled)")

        # Connect to message broker
        broker = await get_broker()
        await broker.connect()
        logger.info("✓ Connected to message broker")

        # Subscribe to defense.action.approved
        await subscribe(
            DEFENSE_ACTION_APPROVED_TOPIC,
            self._handle_action_approved,
        )
        logger.info(f"✓ Subscribed to {DEFENSE_ACTION_APPROVED_TOPIC}")

        logger.info("=" * 80)
        logger.info("DEFENSE ACTUATOR AGENT READY")
        logger.info("=" * 80)

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down defense actuator agent...")
        finally:
            await broker.disconnect()
            if self.mongo_client:
                self.mongo_client.close()


async def main():
    """Main entry point."""
    agent = DefenseActuatorAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

