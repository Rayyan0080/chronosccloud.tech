"""
Defense Verifier Agent

Subscribes to defense.action.deployed events and monitors threat indicators for improvement.
If indicators normalize, publishes defense.threat.resolved.
Otherwise, suggests escalation or rollback.
Logs everything in Audit timeline.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.config import get_mongodb_config
from agents.shared.constants import (
    DEFENSE_ACTION_DEPLOYED_TOPIC,
    DEFENSE_THREAT_RESOLVED_TOPIC,
    DEFENSE_THREAT_DETECTED_TOPIC,
    DEFENSE_THREAT_ESCALATED_TOPIC,
    GEO_INCIDENT_TOPIC,
    GEO_RISK_AREA_TOPIC,
    AIRSPACE_CONFLICT_DETECTED_TOPIC,
    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
    TRANSIT_DISRUPTION_RISK_TOPIC,
    POWER_FAILURE_TOPIC,
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
VERIFICATION_STATUS_COLLECTION = os.getenv("DEFENSE_VERIFICATION_STATUS_COLLECTION", "defense_verifications")

# Verification window (monitor for 10 minutes after deployment)
VERIFICATION_WINDOW_SECONDS = 600  # 10 minutes

# Thresholds for normalization
NORMALIZATION_THRESHOLD = {
    "event_count_reduction": 0.5,  # 50% reduction in threat-related events
    "severity_reduction": 1,  # Severity reduced by at least 1 level
    "confidence_reduction": 0.2,  # Confidence reduced by at least 0.2
}


class DefenseVerifierAgent:
    """Verifies that deployed defense actions have normalized threat indicators."""

    def __init__(self):
        """Initialize the defense verifier agent."""
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
            self.verification_collection.create_index("threat_id", unique=True)
            self.verification_collection.create_index("action_id")
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

    async def _record_verification_start(
        self, threat_id: str, action_id: str, action_details: Dict[str, Any]
    ) -> None:
        """Record that verification has started."""
        if not self.connected:
            return

        try:
            self.verification_collection.update_one(
                {"threat_id": threat_id},
                {
                    "$set": {
                        "threat_id": threat_id,
                        "action_id": action_id,
                        "status": "in_progress",
                        "action_details": action_details,
                        "started_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "timeline": [
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                "status": "verification_started",
                                "message": f"Verification process initiated for threat {threat_id}",
                            }
                        ],
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Error recording verification start: {e}")
            capture_exception(e, {"threat_id": threat_id, "operation": "record_verification_start"})

    async def _update_verification_timeline(
        self, threat_id: str, status: str, message: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update verification timeline."""
        if not self.connected:
            return

        try:
            timeline_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": status,
                "message": message,
            }
            if data:
                timeline_entry["data"] = data

            self.verification_collection.update_one(
                {"threat_id": threat_id},
                {
                    "$push": {"timeline": timeline_entry},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )
        except Exception as e:
            logger.error(f"Error updating verification timeline: {e}")

    async def _record_verification_result(
        self,
        threat_id: str,
        resolved: bool,
        indicators: Dict[str, Any],
        resolution_status: Optional[str] = None,
        escalation_suggestion: Optional[str] = None,
    ) -> None:
        """Record verification result."""
        if not self.connected:
            return

        try:
            status = "resolved" if resolved else "needs_attention"
            update_data = {
                "status": status,
                "resolved": resolved,
                "indicators": indicators,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            if resolution_status:
                update_data["resolution_status"] = resolution_status
            if escalation_suggestion:
                update_data["escalation_suggestion"] = escalation_suggestion

            self.verification_collection.update_one(
                {"threat_id": threat_id},
                {"$set": update_data},
            )
        except Exception as e:
            logger.error(f"Error recording verification result: {e}")
            capture_exception(e, {"threat_id": threat_id, "operation": "record_verification_result"})

    async def _get_threat_baseline(self, threat_id: str, detected_at: datetime) -> Dict[str, Any]:
        """
        Get baseline threat indicators from the original threat detection.
        
        Returns:
            Baseline metrics (severity, confidence, event_count, etc.)
        """
        try:
            # Find the original threat.detected event
            threat_event = self.mongo_collection.find_one({
                "topic": DEFENSE_THREAT_DETECTED_TOPIC,
                "payload.details.threat_id": threat_id,
            })

            if not threat_event:
                logger.warning(f"Original threat event not found for {threat_id}")
                return {
                    "severity": "unknown",
                    "confidence_score": 0.0,
                    "event_count": 0,
                }

            details = threat_event.get("payload", {}).get("details", {})
            return {
                "severity": details.get("severity", "unknown"),
                "confidence_score": details.get("confidence_score", 0.0),
                "threat_type": details.get("threat_type", "unknown"),
                "sources": details.get("sources", []),
                "detected_at": detected_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting threat baseline: {e}")
            return {
                "severity": "unknown",
                "confidence_score": 0.0,
                "event_count": 0,
            }

    async def _query_threat_indicators(
        self, threat_id: str, threat_type: str, sources: List[str], deploy_time: datetime
    ) -> Dict[str, Any]:
        """
        Query threat indicators after deployment.
        
        Returns:
            Current threat indicators (event_count, severity, confidence, etc.)
        """
        try:
            # Calculate time window
            start_time = deploy_time
            end_time = deploy_time + timedelta(seconds=VERIFICATION_WINDOW_SECONDS)
            now = datetime.now(timezone.utc)
            if end_time > now:
                end_time = now  # Don't query future events

            # Query for threat-related events in the verification window
            # Based on threat type and sources, query relevant event topics
            threat_topics = []
            
            if "airspace" in threat_type.lower() or "airspace" in sources:
                threat_topics.extend([
                    AIRSPACE_CONFLICT_DETECTED_TOPIC,
                    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
                ])
            
            if "transit" in sources:
                threat_topics.extend([
                    TRANSIT_DISRUPTION_RISK_TOPIC,
                ])
            
            if "power" in sources or "infra" in sources:
                threat_topics.extend([
                    POWER_FAILURE_TOPIC,
                ])
            
            # Always check for geo incidents and risk areas
            threat_topics.extend([
                GEO_INCIDENT_TOPIC,
                GEO_RISK_AREA_TOPIC,
            ])

            # Query events in the time window
            events = self.mongo_collection.find({
                "topic": {"$in": threat_topics},
                "timestamp": {"$gte": start_time, "$lte": end_time},
            }).sort("timestamp", -1)

            event_list = list(events)
            event_count = len(event_list)

            # Calculate severity distribution
            severity_counts = {}
            max_severity = "info"
            severity_levels = ["info", "warning", "moderate", "high", "critical"]
            
            for event in event_list:
                severity = event.get("payload", {}).get("severity", "info")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                # Track max severity
                if severity in severity_levels:
                    current_idx = severity_levels.index(severity)
                    max_idx = severity_levels.index(max_severity) if max_severity in severity_levels else 0
                    if current_idx > max_idx:
                        max_severity = severity

            # Check for new threat detections
            new_threats = self.mongo_collection.find({
                "topic": DEFENSE_THREAT_DETECTED_TOPIC,
                "payload.details.threat_id": {"$ne": threat_id},  # Exclude the original threat
                "timestamp": {"$gte": start_time, "$lte": end_time},
            })
            new_threat_count = len(list(new_threats))

            return {
                "event_count": event_count,
                "new_threat_count": new_threat_count,
                "max_severity": max_severity,
                "severity_distribution": severity_counts,
                "time_window_start": start_time.isoformat(),
                "time_window_end": end_time.isoformat(),
                "topics_queried": threat_topics,
            }
        except Exception as e:
            logger.error(f"Error querying threat indicators: {e}")
            capture_exception(e, {"threat_id": threat_id, "operation": "query_threat_indicators"})
            return {
                "event_count": 0,
                "new_threat_count": 0,
                "max_severity": "unknown",
                "error": str(e),
            }

    def _check_normalization(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> tuple[bool, str, Optional[str]]:
        """
        Check if threat indicators have normalized.
        
        Returns:
            Tuple of (is_normalized, reason, escalation_suggestion)
        """
        # Check event count reduction
        baseline_count = baseline.get("event_count", 0)
        current_count = current.get("event_count", 0)
        
        if baseline_count > 0:
            reduction_ratio = (baseline_count - current_count) / baseline_count
            if reduction_ratio >= NORMALIZATION_THRESHOLD["event_count_reduction"]:
                return True, f"Event count reduced by {reduction_ratio*100:.1f}%", None
        
        # Check severity reduction
        baseline_severity = baseline.get("severity", "unknown")
        current_severity = current.get("max_severity", "unknown")
        
        severity_levels = ["info", "warning", "moderate", "high", "critical"]
        if baseline_severity in severity_levels and current_severity in severity_levels:
            baseline_idx = severity_levels.index(baseline_severity)
            current_idx = severity_levels.index(current_severity)
            if current_idx < baseline_idx:
                reduction = baseline_idx - current_idx
                if reduction >= NORMALIZATION_THRESHOLD["severity_reduction"]:
                    return True, f"Severity reduced from {baseline_severity} to {current_severity}", None
        
        # Check for new threats
        new_threat_count = current.get("new_threat_count", 0)
        if new_threat_count > 0:
            return False, f"{new_threat_count} new threat(s) detected", "Consider escalating threat assessment"
        
        # Check if events are still occurring
        if current_count > 0:
            # Events still occurring but not reduced enough
            if baseline_count > 0:
                reduction_ratio = (baseline_count - current_count) / baseline_count
                if reduction_ratio < NORMALIZATION_THRESHOLD["event_count_reduction"]:
                    return False, f"Event count only reduced by {reduction_ratio*100:.1f}% (threshold: {NORMALIZATION_THRESHOLD['event_count_reduction']*100}%)", "Consider additional protective actions or escalation"
        
        # If no events in window, consider normalized
        if current_count == 0 and baseline_count > 0:
            return True, "No threat-related events detected in verification window", None
        
        # Default: not normalized if we can't determine
        return False, "Threat indicators have not normalized sufficiently", "Monitor closely and consider escalation if threat persists"

    async def _publish_threat_resolved(
        self, threat_id: str, sector_id: str, resolution_notes: str
    ) -> None:
        """Publish defense.threat.resolved event."""
        resolved_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "defense-verifier-agent",
            "severity": Severity.INFO.value,
            "sector_id": sector_id,
            "summary": f"Threat {threat_id} resolved",
            "correlation_id": threat_id,
            "details": {
                "threat_id": threat_id,
                "resolution_status": "resolved",
                "resolution_notes": resolution_notes,
                "resolved_by": "defense-verifier-agent",
                "resolved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        }

        await publish(DEFENSE_THREAT_RESOLVED_TOPIC, resolved_event)
        capture_published_event(
            DEFENSE_THREAT_RESOLVED_TOPIC,
            resolved_event["event_id"],
            {"threat_id": threat_id},
        )
        logger.info(f"Published defense.threat.resolved for {threat_id}")

    async def _handle_action_deployed(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle defense.action.deployed event."""
        try:
            capture_received_event(topic, payload.get("event_id", "unknown"))

            action_details = payload.get("details", {})
            action_id = action_details.get("action_id")
            threat_id = action_details.get("threat_id")
            deployment_status = action_details.get("deployment_status", "unknown")
            sector_id = payload.get("sector_id", "unknown")

            if not action_id:
                logger.error("Missing action_id in defense.action.deployed event")
                return

            if not threat_id:
                logger.error("Missing threat_id in defense.action.deployed event")
                return

            # Only verify successful deployments
            if deployment_status != "success":
                logger.info(f"Skipping verification for action {action_id} (status: {deployment_status})")
                return

            logger.info("=" * 80)
            logger.info(f"DEFENSE ACTION DEPLOYED: Action {action_id} for Threat {threat_id}")
            logger.info("=" * 80)

            # Record verification start
            await self._record_verification_start(threat_id, action_id, action_details)
            await self._update_verification_timeline(
                threat_id,
                "monitoring_started",
                f"Started monitoring threat indicators for threat {threat_id}",
            )

            # Get threat baseline
            detected_at = datetime.now(timezone.utc)  # Will be updated from threat event
            baseline = await self._get_threat_baseline(threat_id, detected_at)
            
            if baseline.get("detected_at"):
                detected_at = datetime.fromisoformat(baseline["detected_at"].replace("Z", "+00:00"))
            
            await self._update_verification_timeline(
                threat_id,
                "baseline_established",
                f"Baseline established: severity={baseline.get('severity')}, confidence={baseline.get('confidence_score')}",
                {"baseline": baseline},
            )

            # Wait for verification window (or check immediately if window has passed)
            deploy_time = datetime.fromisoformat(
                action_details.get("deployed_at", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")
            )
            wait_until = deploy_time + timedelta(seconds=VERIFICATION_WINDOW_SECONDS)
            now = datetime.now(timezone.utc)
            
            if wait_until > now:
                wait_seconds = (wait_until - now).total_seconds()
                logger.info(f"Waiting {wait_seconds:.0f} seconds for verification window to complete...")
                await self._update_verification_timeline(
                    threat_id,
                    "waiting_for_window",
                    f"Waiting {wait_seconds:.0f} seconds for verification window to complete",
                )
                await asyncio.sleep(wait_seconds)
            else:
                logger.info("Verification window has already passed, checking immediately")

            # Query current threat indicators
            await self._update_verification_timeline(
                threat_id,
                "querying_indicators",
                "Querying current threat indicators",
            )
            
            current = await self._query_threat_indicators(
                threat_id,
                baseline.get("threat_type", "unknown"),
                baseline.get("sources", []),
                deploy_time,
            )

            await self._update_verification_timeline(
                threat_id,
                "indicators_queried",
                f"Current indicators: {current.get('event_count')} events, max_severity={current.get('max_severity')}",
                {"current_indicators": current},
            )

            # Check normalization
            is_normalized, reason, escalation_suggestion = self._check_normalization(baseline, current)

            if is_normalized:
                # Threat resolved
                resolution_notes = f"Threat indicators normalized: {reason}"
                await self._update_verification_timeline(
                    threat_id,
                    "threat_resolved",
                    resolution_notes,
                )
                await self._record_verification_result(
                    threat_id,
                    resolved=True,
                    indicators=current,
                    resolution_status="resolved",
                )
                await self._publish_threat_resolved(threat_id, sector_id, resolution_notes)
                logger.info(f"✓ Threat {threat_id} resolved: {reason}")
            else:
                # Threat not normalized - suggest escalation or rollback
                await self._update_verification_timeline(
                    threat_id,
                    "needs_attention",
                    f"Threat indicators not normalized: {reason}",
                    {"escalation_suggestion": escalation_suggestion},
                )
                await self._record_verification_result(
                    threat_id,
                    resolved=False,
                    indicators=current,
                    escalation_suggestion=escalation_suggestion,
                )
                logger.warning(f"⚠ Threat {threat_id} not normalized: {reason}")
                if escalation_suggestion:
                    logger.warning(f"  Suggestion: {escalation_suggestion}")

        except Exception as e:
            logger.error(f"Error handling defense.action.deployed: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "payload": payload})
            
            # Update timeline with error
            try:
                threat_id = payload.get("details", {}).get("threat_id", "unknown")
                await self._update_verification_timeline(
                    threat_id,
                    "error",
                    f"Verification error: {str(e)}",
                )
            except:
                pass

    async def run(self) -> None:
        """Main run loop for the defense verifier agent."""
        logger.info("=" * 80)
        logger.info("DEFENSE VERIFIER AGENT STARTING")
        logger.info("=" * 80)

        init_sentry("defense_verifier")
        capture_startup("defense_verifier")

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

        # Subscribe to defense.action.deployed
        logger.info(f"Subscribing to {DEFENSE_ACTION_DEPLOYED_TOPIC}...")
        await subscribe(DEFENSE_ACTION_DEPLOYED_TOPIC, self._handle_action_deployed)
        logger.info(f"✓ Subscribed to {DEFENSE_ACTION_DEPLOYED_TOPIC}")

        logger.info("=" * 80)
        logger.info("DEFENSE VERIFIER AGENT RUNNING")
        logger.info("=" * 80)
        logger.info("Waiting for defense.action.deployed events...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal. Shutting down...")
        finally:
            if self.mongo_client:
                self.mongo_client.close()
            await broker.disconnect()
            logger.info("Defense verifier agent stopped")


async def main():
    """Main entry point."""
    agent = DefenseVerifierAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

