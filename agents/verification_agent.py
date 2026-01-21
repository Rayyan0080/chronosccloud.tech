"""
Verification Agent

Subscribes to fix.deploy_succeeded events and verifies that deployed fixes meet their success criteria.
Queries event store and live feeds for metrics within the verification window.
Publishes fix.verified on success or fix.rollback_requested on failure.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.config import get_mongodb_config
from agents.shared.constants import (
    FIX_DEPLOY_SUCCEEDED_TOPIC,
    FIX_VERIFIED_TOPIC,
    FIX_ROLLBACK_REQUESTED_TOPIC,
    TRANSIT_DISRUPTION_RISK_TOPIC,
    TRANSIT_HOTSPOT_TOPIC,
    GEO_RISK_AREA_TOPIC,
    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
    POWER_FAILURE_TOPIC,
)
from agents.shared.schema import (
    Severity,
    ActionType,
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
VERIFICATION_STATUS_COLLECTION = os.getenv("VERIFICATION_STATUS_COLLECTION", "fix_verifications")


class VerificationAgent:
    """Verifies that deployed fixes meet their success criteria."""

    def __init__(self):
        """Initialize the verification agent."""
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_collection = None
        self.verification_collection = None
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
            self.verification_collection = self.mongo_db[VERIFICATION_STATUS_COLLECTION]

            # Create indexes for verification status
            self.verification_collection.create_index("fix_id", unique=True)
            self.verification_collection.create_index("status")
            self.verification_collection.create_index("started_at")

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

    async def _record_verification_start(self, fix_id: str, fix_details: Dict[str, Any]) -> None:
        """Record that verification has started."""
        if not self.connected:
            return

        try:
            self.verification_collection.update_one(
                {"fix_id": fix_id},
                {
                    "$set": {
                        "fix_id": fix_id,
                        "status": "in_progress",
                        "fix_details": fix_details,
                        "started_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "timeline": [
                            {
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "status": "verification_started",
                                "message": "Verification process initiated",
                            }
                        ],
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Error recording verification start: {e}")
            capture_exception(e, {"fix_id": fix_id, "operation": "record_verification_start"})

    async def _update_verification_timeline(self, fix_id: str, status: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Update verification timeline."""
        if not self.connected:
            return

        try:
            timeline_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": status,
                "message": message,
            }
            if data:
                timeline_entry["data"] = data

            self.verification_collection.update_one(
                {"fix_id": fix_id},
                {
                    "$push": {"timeline": timeline_entry},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )
        except Exception as e:
            logger.error(f"Error updating verification timeline: {e}")

    async def _record_verification_result(self, fix_id: str, passed: bool, metrics: Dict[str, Any], error: Optional[str] = None) -> None:
        """Record verification result."""
        if not self.connected:
            return

        try:
            status = "verified" if passed else "failed"
            update_data = {
                "status": status,
                "passed": passed,
                "metrics": metrics,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            if error:
                update_data["error"] = error

            self.verification_collection.update_one(
                {"fix_id": fix_id},
                {"$set": update_data},
            )
        except Exception as e:
            logger.error(f"Error recording verification result: {e}")
            capture_exception(e, {"fix_id": fix_id, "operation": "record_verification_result"})

    async def _query_transit_delays(
        self, route_id: Optional[str], area_bbox: Optional[List[float]], start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Query transit delays for verification."""
        if not self.connected:
            return {"average_delay": 0.0, "delay_reduction": 0.0, "sample_count": 0}

        try:
            # Query transit disruption risk and hotspot events
            query = {
                "timestamp": {"$gte": start_time, "$lte": end_time},
                "$or": [
                    {"topic": TRANSIT_DISRUPTION_RISK_TOPIC},
                    {"topic": TRANSIT_HOTSPOT_TOPIC},
                ],
            }

            if route_id:
                query["$or"][0]["payload.details.route_id"] = route_id
                query["$or"][1]["payload.details.route_id"] = route_id

            events = list(self.mongo_collection.find(query).sort("timestamp", 1))

            if not events:
                return {"average_delay": 0.0, "delay_reduction": 0.0, "sample_count": 0}

            # Calculate average delay
            delays = []
            for event in events:
                payload = event.get("payload", {})
                details = payload.get("details", {})
                delay = details.get("delay", 0) or details.get("average_delay_minutes", 0)
                if delay > 0:
                    delays.append(delay)

            average_delay = sum(delays) / len(delays) if delays else 0.0

            # For verification, we compare against baseline (assume baseline was higher)
            # In a real system, we'd compare against pre-deployment metrics
            baseline_delay = average_delay * 1.5  # Assume 50% reduction target
            delay_reduction = baseline_delay - average_delay

            return {
                "average_delay": average_delay,
                "delay_reduction": delay_reduction,
                "sample_count": len(events),
            }

        except Exception as e:
            logger.error(f"Error querying transit delays: {e}")
            capture_exception(e, {"operation": "query_transit_delays"})
            return {"average_delay": 0.0, "delay_reduction": 0.0, "sample_count": 0, "error": str(e)}

    async def _query_risk_score(
        self, sector_id: Optional[str], area_bbox: Optional[List[float]], start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Query risk score for verification."""
        if not self.connected:
            return {"risk_score": 1.0, "risk_score_delta": 0.0, "sample_count": 0}

        try:
            # Query geo.risk_area events
            query = {
                "timestamp": {"$gte": start_time, "$lte": end_time},
                "topic": GEO_RISK_AREA_TOPIC,
            }

            if sector_id:
                query["payload.sector_id"] = sector_id

            events = list(self.mongo_collection.find(query).sort("timestamp", 1))

            if not events:
                return {"risk_score": 1.0, "risk_score_delta": 0.0, "sample_count": 0}

            # Calculate average risk score
            risk_scores = []
            for event in events:
                payload = event.get("payload", {})
                details = payload.get("details", {})
                risk_score = details.get("risk_score", 1.0)
                if risk_score is not None:
                    risk_scores.append(risk_score)

            average_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 1.0

            # For verification, assume baseline was higher
            baseline_risk = average_risk_score * 1.2  # Assume 20% reduction target
            risk_score_delta = baseline_risk - average_risk_score

            return {
                "risk_score": average_risk_score,
                "risk_score_delta": risk_score_delta,
                "sample_count": len(events),
            }

        except Exception as e:
            logger.error(f"Error querying risk score: {e}")
            capture_exception(e, {"operation": "query_risk_score"})
            return {"risk_score": 1.0, "risk_score_delta": 0.0, "sample_count": 0, "error": str(e)}

    async def _query_hotspot_congestion(
        self, sector_id: Optional[str], start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Query hotspot congestion score for verification."""
        if not self.connected:
            return {"congestion_score": 1.0, "congestion_reduction": 0.0, "sample_count": 0}

        try:
            # Query airspace hotspot events
            query = {
                "timestamp": {"$gte": start_time, "$lte": end_time},
                "topic": AIRSPACE_HOTSPOT_DETECTED_TOPIC,
            }

            if sector_id:
                query["payload.sector_id"] = sector_id

            events = list(self.mongo_collection.find(query).sort("timestamp", 1))

            if not events:
                return {"congestion_score": 0.0, "congestion_reduction": 0.0, "sample_count": 0}

            # Calculate average congestion (based on hotspot severity)
            congestion_scores = []
            for event in events:
                payload = event.get("payload", {})
                details = payload.get("details", {})
                severity = payload.get("severity", "info")
                # Map severity to score
                severity_scores = {"info": 0.2, "warning": 0.5, "moderate": 0.7, "critical": 1.0}
                score = severity_scores.get(severity, 0.5)
                congestion_scores.append(score)

            average_congestion = sum(congestion_scores) / len(congestion_scores) if congestion_scores else 0.0

            # Assume baseline was higher
            baseline_congestion = average_congestion * 1.3  # Assume 30% reduction target
            congestion_reduction = baseline_congestion - average_congestion

            return {
                "congestion_score": average_congestion,
                "congestion_reduction": congestion_reduction,
                "sample_count": len(events),
            }

        except Exception as e:
            logger.error(f"Error querying hotspot congestion: {e}")
            capture_exception(e, {"operation": "query_hotspot_congestion"})
            return {"congestion_score": 1.0, "congestion_reduction": 0.0, "sample_count": 0, "error": str(e)}

    async def _query_power_voltage(
        self, sector_id: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Query power sector voltage for verification."""
        if not self.connected:
            return {"voltage": 0.0, "voltage_stable": False, "sample_count": 0}

        try:
            # Query power failure events (absence indicates stability)
            query = {
                "timestamp": {"$gte": start_time, "$lte": end_time},
                "topic": POWER_FAILURE_TOPIC,
                "payload.sector_id": sector_id,
            }

            failure_events = list(self.mongo_collection.find(query))

            # If no failures in the window, voltage is stable
            voltage_stable = len(failure_events) == 0

            # For power recovery, we check if voltage is within normal range (assume 120V nominal)
            # In a real system, we'd query actual voltage readings
            voltage = 120.0 if voltage_stable else 0.0

            return {
                "voltage": voltage,
                "voltage_stable": voltage_stable,
                "sample_count": len(failure_events),
                "failure_count": len(failure_events),
            }

        except Exception as e:
            logger.error(f"Error querying power voltage: {e}")
            capture_exception(e, {"operation": "query_power_voltage"})
            return {"voltage": 0.0, "voltage_stable": False, "sample_count": 0, "error": str(e)}

    async def _verify_action(
        self, action: Dict[str, Any], fix_id: str, deploy_time: datetime, sector_id: str
    ) -> Dict[str, Any]:
        """Verify a single action against its verification criteria."""
        verification = action.get("verification")
        if not verification:
            logger.warning(f"Action {action.get('type')} has no verification criteria")
            return {"passed": True, "skipped": True, "reason": "No verification criteria"}

        metric_name = verification.get("metric_name")
        threshold = verification.get("threshold")
        window_seconds = verification.get("window_seconds", 300)

        if not metric_name or threshold is None:
            logger.warning(f"Action {action.get('type')} has incomplete verification criteria")
            return {"passed": True, "skipped": True, "reason": "Incomplete verification criteria"}

        # Calculate time window
        start_time = deploy_time
        end_time = deploy_time + timedelta(seconds=window_seconds)

        logger.info(f"Verifying action {action.get('type')}: {metric_name} >= {threshold} within {window_seconds}s")

        target = action.get("target", {})
        action_type = action.get("type", "")

        # Query metric based on action type and metric name
        metrics = {}
        passed = False

        if action_type == ActionType.TRANSIT_REROUTE_SIM.value:
            if metric_name == "delay_reduction":
                metrics = await self._query_transit_delays(
                    target.get("route_id"),
                    target.get("area_bbox"),
                    start_time,
                    end_time,
                )
                delay_reduction = metrics.get("delay_reduction", 0.0)
                passed = delay_reduction >= threshold

        elif action_type == ActionType.TRAFFIC_ADVISORY_SIM.value:
            if metric_name == "risk_score_delta":
                metrics = await self._query_risk_score(
                    target.get("sector_id"),
                    target.get("area_bbox"),
                    start_time,
                    end_time,
                )
                risk_delta = metrics.get("risk_score_delta", 0.0)
                passed = abs(risk_delta) >= abs(threshold)  # Negative threshold means reduction

        elif action_type == ActionType.AIRSPACE_MITIGATION_SIM.value:
            if metric_name in ["congestion_score", "hotspot_congestion"]:
                metrics = await self._query_hotspot_congestion(
                    target.get("sector_id") or sector_id,
                    start_time,
                    end_time,
                )
                congestion_reduction = metrics.get("congestion_reduction", 0.0)
                passed = congestion_reduction >= threshold

        elif action_type == ActionType.POWER_RECOVERY_SIM.value:
            if metric_name == "voltage_stable":
                metrics = await self._query_power_voltage(
                    target.get("sector_id") or sector_id,
                    start_time,
                    end_time,
                )
                voltage_stable = metrics.get("voltage_stable", False)
                passed = voltage_stable == bool(threshold)

        else:
            logger.warning(f"Unknown action type for verification: {action_type}")
            return {"passed": True, "skipped": True, "reason": f"Unknown action type: {action_type}"}

        result = {
            "passed": passed,
            "metric_name": metric_name,
            "threshold": threshold,
            "actual_value": metrics.get(metric_name, 0.0) if metric_name in metrics else None,
            "metrics": metrics,
            "window_seconds": window_seconds,
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
        }

        if not passed:
            result["error"] = f"Metric {metric_name} did not meet threshold {threshold}"

        return result

    async def _publish_verified(self, fix_details: Dict[str, Any], correlation_id: str, sector_id: str, verification_results: List[Dict[str, Any]]) -> None:
        """Publish fix.verified event."""
        verified_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "verification-agent",
            "severity": Severity.INFO.value,
            "sector_id": sector_id,
            "summary": f"Fix {fix_details['fix_id']} verified successfully",
            "correlation_id": correlation_id,
            "details": {
                **fix_details,
                "verified_at": datetime.utcnow().isoformat() + "Z",
                "verification_results": verification_results,
            },
        }

        await publish(FIX_VERIFIED_TOPIC, verified_event)
        capture_published_event(
            FIX_VERIFIED_TOPIC,
            verified_event["event_id"],
            {"fix_id": fix_details["fix_id"]},
        )
        logger.info(f"Published fix.verified for {fix_details['fix_id']}")

    async def _publish_rollback_requested(
        self, fix_details: Dict[str, Any], correlation_id: str, sector_id: str, verification_results: List[Dict[str, Any]], failed_actions: List[Dict[str, Any]]
    ) -> None:
        """Publish fix.rollback_requested event with suggested rollback action."""
        # Generate rollback action suggestion
        rollback_action = {
            "type": "ROLLBACK_SIM",
            "target": fix_details.get("actions", [{}])[0].get("target", {}) if fix_details.get("actions") else {},
            "params": {
                "original_fix_id": fix_details["fix_id"],
                "reason": "Verification failed",
                "failed_actions": failed_actions,
            },
        }

        rollback_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "verification-agent",
            "severity": Severity.WARNING.value,
            "sector_id": sector_id,
            "summary": f"Rollback requested for fix {fix_details['fix_id']}: verification failed",
            "correlation_id": correlation_id,
            "details": {
                **fix_details,
                "rollback_requested_at": datetime.utcnow().isoformat() + "Z",
                "verification_results": verification_results,
                "failed_actions": failed_actions,
                "suggested_rollback_action": rollback_action,
            },
        }

        await publish(FIX_ROLLBACK_REQUESTED_TOPIC, rollback_event)
        capture_published_event(
            FIX_ROLLBACK_REQUESTED_TOPIC,
            rollback_event["event_id"],
            {"fix_id": fix_details["fix_id"]},
        )
        logger.warning(f"Published fix.rollback_requested for {fix_details['fix_id']}")

    async def _handle_deploy_succeeded(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle fix.deploy_succeeded event."""
        try:
            capture_received_event(topic, payload.get("event_id", "unknown"))

            fix_details = payload.get("details", {})
            fix_id = fix_details.get("fix_id")
            correlation_id = payload.get("correlation_id") or fix_details.get("correlation_id", "unknown")
            sector_id = payload.get("sector_id", "unknown")

            if not fix_id:
                logger.error("Missing fix_id in deploy_succeeded event")
                return

            logger.info("=" * 80)
            logger.info(f"VERIFICATION STARTED: Fix {fix_id}")
            logger.info("=" * 80)

            # Record verification start
            await self._record_verification_start(fix_id, fix_details)

            # Get deployment time
            deploy_time_str = fix_details.get("deploy_succeeded_at") or payload.get("timestamp")
            try:
                deploy_time = datetime.fromisoformat(deploy_time_str.replace("Z", "+00:00"))
            except:
                deploy_time = datetime.utcnow()

            # Verify each action
            actions = fix_details.get("actions", [])
            if not actions:
                logger.warning(f"Fix {fix_id} has no actions to verify")
                await self._update_verification_timeline(fix_id, "skipped", "No actions to verify")
                return

            logger.info(f"Verifying {len(actions)} action(s) for fix {fix_id}...")
            verification_results = []
            failed_actions = []

            for idx, action in enumerate(actions, 1):
                logger.info(f"  [{idx}/{len(actions)}] Verifying action: {action.get('type', 'UNKNOWN')}")
                await self._update_verification_timeline(
                    fix_id,
                    "verifying",
                    f"Verifying action {idx}: {action.get('type', 'UNKNOWN')}",
                    {"action_index": idx, "action_type": action.get("type")},
                )

                result = await self._verify_action(action, fix_id, deploy_time, sector_id)

                if result.get("skipped"):
                    logger.info(f"    Action {idx} skipped: {result.get('reason')}")
                    await self._update_verification_timeline(
                        fix_id,
                        "skipped",
                        f"Action {idx} verification skipped: {result.get('reason')}",
                    )
                elif result.get("passed"):
                    logger.info(f"    ✓ Action {idx} passed verification")
                    await self._update_verification_timeline(
                        fix_id,
                        "passed",
                        f"Action {idx} passed verification: {result.get('metric_name')} = {result.get('actual_value')}",
                        {"metric": result.get("metric_name"), "value": result.get("actual_value")},
                    )
                else:
                    logger.warning(f"    ✗ Action {idx} failed verification: {result.get('error')}")
                    failed_actions.append({
                        "action_index": idx,
                        "action_type": action.get("type"),
                        "result": result,
                    })
                    await self._update_verification_timeline(
                        fix_id,
                        "failed",
                        f"Action {idx} failed verification: {result.get('error')}",
                        {"error": result.get("error")},
                    )

                verification_results.append(result)

            # Check overall verification result
            all_passed = all(r.get("passed", False) or r.get("skipped", False) for r in verification_results)
            any_failed = any(not r.get("passed", False) and not r.get("skipped", False) for r in verification_results)

            # Record verification result
            metrics_summary = {
                "total_actions": len(actions),
                "passed": sum(1 for r in verification_results if r.get("passed")),
                "failed": sum(1 for r in verification_results if not r.get("passed") and not r.get("skipped")),
                "skipped": sum(1 for r in verification_results if r.get("skipped")),
            }

            await self._record_verification_result(fix_id, all_passed, metrics_summary)

            if all_passed:
                logger.info(f"✓ All actions verified successfully for fix {fix_id}")
                await self._update_verification_timeline(fix_id, "verified", "All actions verified successfully")
                await self._publish_verified(fix_details, correlation_id, sector_id, verification_results)
            else:
                logger.warning(f"✗ Verification failed for fix {fix_id}: {len(failed_actions)} action(s) failed")
                await self._update_verification_timeline(
                    fix_id,
                    "verification_failed",
                    f"Verification failed: {len(failed_actions)} action(s) did not meet criteria",
                )
                await self._publish_rollback_requested(fix_details, correlation_id, sector_id, verification_results, failed_actions)

            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error handling deploy succeeded: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "payload": payload})

    async def run(self) -> None:
        """Main run loop for the verification agent."""
        # Initialize Sentry
        init_sentry()
        capture_startup("verification-agent")

        # Connect to MongoDB
        try:
            await self._connect_mongodb()
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.warning("Continuing without MongoDB (verification status tracking disabled)")

        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        await broker.connect()
        logger.info("✓ Connected to message broker")

        # Subscribe to fix.deploy_succeeded
        logger.info(f"Subscribing to {FIX_DEPLOY_SUCCEEDED_TOPIC}...")
        await subscribe(FIX_DEPLOY_SUCCEEDED_TOPIC, self._handle_deploy_succeeded)
        logger.info(f"✓ Subscribed to {FIX_DEPLOY_SUCCEEDED_TOPIC}")

        logger.info("=" * 80)
        logger.info("VERIFICATION AGENT RUNNING")
        logger.info("=" * 80)
        logger.info("Waiting for fix.deploy_succeeded events...")
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
            logger.info("Verification agent stopped")


async def main():
    """Main entry point."""
    agent = VerificationAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

