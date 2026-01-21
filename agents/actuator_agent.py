"""
Actuator Agent

Subscribes to fix.deploy_requested events and executes actions in a safe sandbox.
Publishes appropriate domain-specific events and tracks deployment status in MongoDB.

IMPORTANT: Deployments are idempotent - same fix_id will not deploy twice.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.config import get_mongodb_config
from agents.shared.constants import (
    FIX_DEPLOY_REQUESTED_TOPIC,
    FIX_DEPLOY_STARTED_TOPIC,
    FIX_DEPLOY_SUCCEEDED_TOPIC,
    FIX_DEPLOY_FAILED_TOPIC,
    TRANSIT_MITIGATION_APPLIED_TOPIC,
    GEO_RISK_AREA_TOPIC,
    AIRSPACE_MITIGATION_APPLIED_TOPIC,
    SYSTEM_ACTION_TOPIC,
)
from agents.shared.schema import (
    Severity,
    ActionType,
    FixDetails,
)
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
DEPLOYMENT_STATUS_COLLECTION = os.getenv("DEPLOYMENT_STATUS_COLLECTION", "fix_deployments")


class ActuatorAgent:
    """Executes fix deployments in a safe sandbox."""

    def __init__(self):
        """Initialize the actuator agent."""
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
            self.deployment_collection.create_index("fix_id", unique=True)
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

    async def _check_deployment_status(self, fix_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if a fix has already been deployed (idempotency check).
        
        Returns:
            Deployment status document if exists, None otherwise
        """
        if not self.connected:
            return None

        try:
            deployment = self.deployment_collection.find_one({"fix_id": fix_id})
            return deployment
        except Exception as e:
            logger.error(f"Error checking deployment status: {e}")
            return None

    async def _record_deployment_start(self, fix_id: str, fix_details: Dict[str, Any]) -> None:
        """Record that deployment has started."""
        if not self.connected:
            return

        try:
            self.deployment_collection.update_one(
                {"fix_id": fix_id},
                {
                    "$set": {
                        "fix_id": fix_id,
                        "status": "started",
                        "fix_details": fix_details,
                        "started_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Error recording deployment start: {e}")
            capture_exception(e, {"fix_id": fix_id, "operation": "record_deployment_start"})

    async def _record_deployment_success(self, fix_id: str, actions_executed: List[Dict[str, Any]]) -> None:
        """Record successful deployment."""
        if not self.connected:
            return

        try:
            self.deployment_collection.update_one(
                {"fix_id": fix_id},
                {
                    "$set": {
                        "status": "succeeded",
                        "actions_executed": actions_executed,
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as e:
            logger.error(f"Error recording deployment success: {e}")
            capture_exception(e, {"fix_id": fix_id, "operation": "record_deployment_success"})

    async def _record_deployment_failure(self, fix_id: str, error: str) -> None:
        """Record failed deployment."""
        if not self.connected:
            return

        try:
            self.deployment_collection.update_one(
                {"fix_id": fix_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": error,
                        "failed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as e:
            logger.error(f"Error recording deployment failure: {e}")
            capture_exception(e, {"fix_id": fix_id, "operation": "record_deployment_failure"})

    async def _execute_transit_action(
        self, action: Dict[str, Any], fix_id: str, correlation_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute a transit reroute action."""
        try:
            target = action.get("target", {})
            params = action.get("params", {})
            route_id = target.get("route_id", "UNKNOWN")

            # Create transit.mitigation.applied event
            mitigation_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "actuator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Transit mitigation applied: Reroute {route_id} (Fix {fix_id})",
                "correlation_id": correlation_id,
                "details": {
                    "fix_id": fix_id,
                    "action_type": ActionType.TRANSIT_REROUTE_SIM.value,
                    "route_id": route_id,
                    "target": target,
                    "params": params,
                    "simulation_mode": True,  # SAFE SANDBOX - marked as simulation
                    "what_if_active": True,  # Store as "what-if active" in Mongo
                },
            }

            # Publish event
            await publish(TRANSIT_MITIGATION_APPLIED_TOPIC, mitigation_event)
            capture_published_event(
                TRANSIT_MITIGATION_APPLIED_TOPIC,
                mitigation_event["event_id"],
                {"fix_id": fix_id, "route_id": route_id},
            )

            # Store in MongoDB as "what-if active"
            if self.connected:
                try:
                    self.mongo_collection.insert_one({
                        "topic": TRANSIT_MITIGATION_APPLIED_TOPIC,
                        "payload": mitigation_event,
                        "timestamp": datetime.utcnow(),
                        "logged_at": datetime.utcnow(),
                        "what_if_active": True,  # Mark as what-if scenario
                        "fix_id": fix_id,
                    })
                except Exception as e:
                    logger.warning(f"Failed to store transit mitigation in MongoDB: {e}")

            logger.info(f"✓ Transit mitigation applied for route {route_id} (Fix {fix_id})")
            return {"success": True, "action": "transit_reroute", "route_id": route_id}

        except Exception as e:
            logger.error(f"Error executing transit action: {e}")
            capture_exception(e, {"fix_id": fix_id, "action_type": "transit"})
            return {"success": False, "error": str(e)}

    async def _execute_traffic_action(
        self, action: Dict[str, Any], fix_id: str, correlation_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute a traffic advisory action."""
        try:
            target = action.get("target", {})
            params = action.get("params", {})
            area_bbox = target.get("area_bbox")

            # Create geo.risk_area reduction advisory event
            risk_area_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "actuator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Traffic advisory: Risk area reduction (Fix {fix_id})",
                "correlation_id": correlation_id,
                "details": {
                    "fix_id": fix_id,
                    "action_type": ActionType.TRAFFIC_ADVISORY_SIM.value,
                    "risk_type": "traffic_advisory",
                    "risk_level": "reduced",
                    "area_bbox": area_bbox,
                    "target": target,
                    "params": params,
                    "simulation_mode": True,  # SAFE SANDBOX
                },
            }

            # Publish geo.risk_area event
            await publish(GEO_RISK_AREA_TOPIC, risk_area_event)
            capture_published_event(
                GEO_RISK_AREA_TOPIC,
                risk_area_event["event_id"],
                {"fix_id": fix_id},
            )

            # Create notification event
            notification_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "actuator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Traffic advisory notification: Risk area reduced (Fix {fix_id})",
                "correlation_id": correlation_id,
                "details": {
                    "fix_id": fix_id,
                    "notification_type": "traffic_advisory",
                    "message": f"Traffic risk area reduced in {sector_id}",
                },
            }

            # Publish notification (using system.action topic)
            await publish(SYSTEM_ACTION_TOPIC, notification_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                notification_event["event_id"],
                {"fix_id": fix_id, "type": "notification"},
            )

            logger.info(f"✓ Traffic advisory applied (Fix {fix_id})")
            return {"success": True, "action": "traffic_advisory"}

        except Exception as e:
            logger.error(f"Error executing traffic action: {e}")
            capture_exception(e, {"fix_id": fix_id, "action_type": "traffic"})
            return {"success": False, "error": str(e)}

    async def _execute_airspace_action(
        self, action: Dict[str, Any], fix_id: str, correlation_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute an airspace mitigation action."""
        try:
            target = action.get("target", {})
            params = action.get("params", {})

            # Create airspace.mitigation.applied event
            mitigation_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "actuator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"Airspace mitigation applied (Fix {fix_id})",
                "correlation_id": correlation_id,
                "details": {
                    "fix_id": fix_id,
                    "action_type": ActionType.AIRSPACE_MITIGATION_SIM.value,
                    "target": target,
                    "params": params,
                    "simulation_mode": True,  # SAFE SANDBOX
                },
            }

            # Publish event
            await publish(AIRSPACE_MITIGATION_APPLIED_TOPIC, mitigation_event)
            capture_published_event(
                AIRSPACE_MITIGATION_APPLIED_TOPIC,
                mitigation_event["event_id"],
                {"fix_id": fix_id},
            )

            logger.info(f"✓ Airspace mitigation applied (Fix {fix_id})")
            return {"success": True, "action": "airspace_mitigation"}

        except Exception as e:
            logger.error(f"Error executing airspace action: {e}")
            capture_exception(e, {"fix_id": fix_id, "action_type": "airspace"})
            return {"success": False, "error": str(e)}

    async def _execute_power_action(
        self, action: Dict[str, Any], fix_id: str, correlation_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute a power recovery action."""
        try:
            target = action.get("target", {})
            params = action.get("params", {})
            sector_id = target.get("sector_id", sector_id)

            # Create system.action event for power recovery
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "actuator-agent",
                "severity": Severity.WARNING.value,
                "sector_id": sector_id,
                "summary": f"Power recovery action executed (Fix {fix_id})",
                "correlation_id": correlation_id,
                "details": {
                    "fix_id": fix_id,
                    "action_type": ActionType.POWER_RECOVERY_SIM.value,
                    "action": "power_recovery",
                    "target": target,
                    "params": params,
                    "simulation_mode": True,  # SAFE SANDBOX
                },
            }

            # Publish event
            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"fix_id": fix_id, "action_type": "power_recovery"},
            )

            logger.info(f"✓ Power recovery action executed (Fix {fix_id})")
            return {"success": True, "action": "power_recovery", "sector_id": sector_id}

        except Exception as e:
            logger.error(f"Error executing power action: {e}")
            capture_exception(e, {"fix_id": fix_id, "action_type": "power"})
            return {"success": False, "error": str(e)}

    async def _execute_action(
        self, action: Dict[str, Any], fix_id: str, correlation_id: str, sector_id: str
    ) -> Dict[str, Any]:
        """Execute a single action based on its type."""
        action_type = action.get("type", "")

        if action_type == ActionType.TRANSIT_REROUTE_SIM.value:
            return await self._execute_transit_action(action, fix_id, correlation_id, sector_id)
        elif action_type == ActionType.TRAFFIC_ADVISORY_SIM.value:
            return await self._execute_traffic_action(action, fix_id, correlation_id, sector_id)
        elif action_type == ActionType.AIRSPACE_MITIGATION_SIM.value:
            return await self._execute_airspace_action(action, fix_id, correlation_id, sector_id)
        elif action_type == ActionType.POWER_RECOVERY_SIM.value:
            return await self._execute_power_action(action, fix_id, correlation_id, sector_id)
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {"success": False, "error": f"Unknown action type: {action_type}"}

    async def _publish_deploy_started(self, fix_details: Dict[str, Any], correlation_id: str, sector_id: str) -> None:
        """Publish fix.deploy_started event."""
        deploy_started_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "actuator-agent",
            "severity": Severity.WARNING.value,
            "sector_id": sector_id,
            "summary": f"Deployment started for fix {fix_details['fix_id']}",
            "correlation_id": correlation_id,
            "details": {
                **fix_details,
                "deploy_started_at": datetime.utcnow().isoformat() + "Z",
            },
        }

        await publish(FIX_DEPLOY_STARTED_TOPIC, deploy_started_event)
        capture_published_event(
            FIX_DEPLOY_STARTED_TOPIC,
            deploy_started_event["event_id"],
            {"fix_id": fix_details["fix_id"]},
        )
        logger.info(f"Published fix.deploy_started for {fix_details['fix_id']}")

    async def _publish_deploy_succeeded(
        self, fix_details: Dict[str, Any], correlation_id: str, sector_id: str, actions_executed: List[Dict[str, Any]]
    ) -> None:
        """Publish fix.deploy_succeeded event."""
        deploy_succeeded_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "actuator-agent",
            "severity": Severity.INFO.value,
            "sector_id": sector_id,
            "summary": f"Deployment succeeded for fix {fix_details['fix_id']}",
            "correlation_id": correlation_id,
            "details": {
                **fix_details,
                "deploy_succeeded_at": datetime.utcnow().isoformat() + "Z",
                "actions_executed": actions_executed,
            },
        }

        await publish(FIX_DEPLOY_SUCCEEDED_TOPIC, deploy_succeeded_event)
        capture_published_event(
            FIX_DEPLOY_SUCCEEDED_TOPIC,
            deploy_succeeded_event["event_id"],
            {"fix_id": fix_details["fix_id"]},
        )
        logger.info(f"Published fix.deploy_succeeded for {fix_details['fix_id']}")

    async def _publish_deploy_failed(
        self, fix_details: Dict[str, Any], correlation_id: str, sector_id: str, error: str
    ) -> None:
        """Publish fix.deploy_failed event."""
        deploy_failed_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "actuator-agent",
            "severity": Severity.CRITICAL.value,
            "sector_id": sector_id,
            "summary": f"Deployment failed for fix {fix_details['fix_id']}: {error}",
            "correlation_id": correlation_id,
            "details": {
                **fix_details,
                "deploy_failed_at": datetime.utcnow().isoformat() + "Z",
                "error": error,
            },
        }

        await publish(FIX_DEPLOY_FAILED_TOPIC, deploy_failed_event)
        capture_published_event(
            FIX_DEPLOY_FAILED_TOPIC,
            deploy_failed_event["event_id"],
            {"fix_id": fix_details["fix_id"]},
        )
        logger.error(f"Published fix.deploy_failed for {fix_details['fix_id']}: {error}")

    async def _handle_deploy_request(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle fix.deploy_requested event."""
        try:
            capture_received_event(topic, payload.get("event_id", "unknown"))

            fix_details = payload.get("details", {})
            fix_id = fix_details.get("fix_id")
            correlation_id = payload.get("correlation_id") or fix_details.get("correlation_id", "unknown")
            sector_id = payload.get("sector_id", "unknown")

            if not fix_id:
                logger.error("Missing fix_id in deploy_requested event")
                return

            logger.info("=" * 80)
            logger.info(f"DEPLOY REQUEST RECEIVED: Fix {fix_id}")
            logger.info("=" * 80)

            # IDEMPOTENCY CHECK: Check if already deployed
            existing_deployment = await self._check_deployment_status(fix_id)
            if existing_deployment:
                status = existing_deployment.get("status")
                if status in ["started", "succeeded"]:
                    logger.warning(
                        f"Fix {fix_id} already deployed (status: {status}). Skipping deployment (idempotent)."
                    )
                    return
                elif status == "failed":
                    logger.info(f"Fix {fix_id} previously failed. Retrying deployment...")

            # Record deployment start
            await self._record_deployment_start(fix_id, fix_details)

            # Publish deploy_started event
            await self._publish_deploy_started(fix_details, correlation_id, sector_id)

            # Execute all actions in the fix
            actions = fix_details.get("actions", [])
            if not actions:
                error_msg = "No actions to execute"
                logger.error(f"Fix {fix_id}: {error_msg}")
                await self._publish_deploy_failed(fix_details, correlation_id, sector_id, error_msg)
                await self._record_deployment_failure(fix_id, error_msg)
                return

            logger.info(f"Executing {len(actions)} action(s) for fix {fix_id}...")
            actions_executed = []
            failed_actions = []

            for idx, action in enumerate(actions, 1):
                logger.info(f"  [{idx}/{len(actions)}] Executing action: {action.get('type', 'UNKNOWN')}")
                result = await self._execute_action(action, fix_id, correlation_id, sector_id)
                actions_executed.append(result)

                if not result.get("success"):
                    failed_actions.append({
                        "action_index": idx,
                        "action_type": action.get("type"),
                        "error": result.get("error", "Unknown error"),
                    })

            # Check if all actions succeeded
            if failed_actions:
                error_msg = f"Some actions failed: {json.dumps(failed_actions)}"
                logger.error(f"Fix {fix_id}: {error_msg}")
                await self._publish_deploy_failed(fix_details, correlation_id, sector_id, error_msg)
                await self._record_deployment_failure(fix_id, error_msg)
            else:
                logger.info(f"✓ All actions executed successfully for fix {fix_id}")
                await self._publish_deploy_succeeded(fix_details, correlation_id, sector_id, actions_executed)
                await self._record_deployment_success(fix_id, actions_executed)

            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error handling deploy request: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "payload": payload})
            
            # Try to publish deploy_failed if we have fix_id
            try:
                fix_details = payload.get("details", {})
                fix_id = fix_details.get("fix_id")
                if fix_id:
                    correlation_id = payload.get("correlation_id", "unknown")
                    sector_id = payload.get("sector_id", "unknown")
                    await self._publish_deploy_failed(fix_details, correlation_id, sector_id, str(e))
                    await self._record_deployment_failure(fix_id, str(e))
            except Exception as e2:
                logger.error(f"Error publishing deploy_failed: {e2}")

    async def run(self) -> None:
        """Main run loop for the actuator agent."""
        # Initialize Sentry
        init_sentry()
        capture_startup("actuator-agent")

        # Connect to MongoDB
        try:
            await self._connect_mongodb()
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.warning("Continuing without MongoDB (deployment status tracking disabled)")

        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        await broker.connect()
        logger.info("✓ Connected to message broker")

        # Subscribe to fix.deploy_requested
        logger.info(f"Subscribing to {FIX_DEPLOY_REQUESTED_TOPIC}...")
        await subscribe(FIX_DEPLOY_REQUESTED_TOPIC, self._handle_deploy_request)
        logger.info(f"✓ Subscribed to {FIX_DEPLOY_REQUESTED_TOPIC}")

        logger.info("=" * 80)
        logger.info("ACTUATOR AGENT RUNNING")
        logger.info("=" * 80)
        logger.info("Waiting for fix.deploy_requested events...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal. Shutting down...")
        finally:
            if self.mongo_client:
                self.mongo_client.close()
            await broker.disconnect()
            logger.info("Actuator agent stopped")


async def main():
    """Main entry point."""
    agent = ActuatorAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

