"""
Trajectory Insight Agent

Subscribes to airspace.flight.parsed events, collects flights by correlation_id,
analyzes trajectories, and publishes conflict, hotspot, solution, and report events.

Ensures idempotency by tracking processed plan_ids in MongoDB with TTL.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.schema import (
    AirspaceConflictDetectedEvent,
    AirspaceHotspotDetectedEvent,
    AirspaceSolutionProposedEvent,
    AirspaceReportReadyEvent,
    Severity,
)
from agents.shared.constants import (
    AIRSPACE_FLIGHT_PARSED_TOPIC,
    AIRSPACE_CONFLICT_DETECTED_TOPIC,
    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
    AIRSPACE_SOLUTION_PROPOSED_TOPIC,
    AIRSPACE_REPORT_READY_TOPIC,
    GEO_INCIDENT_TOPIC,
    GEO_RISK_AREA_TOPIC,
)
from agents.shared.config import get_mongodb_config
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_published_event,
    capture_exception,
    add_breadcrumb,
    set_tag,
)
from trajectory_insight import analyze
from trajectory_insight.solution_generators import generate_solutions_rules, generate_solutions_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
PLAN_WINDOW_SECONDS = int(os.getenv("PLAN_WINDOW_SECONDS", "60"))  # Wait time for collecting flights
SAMPLE_STEP_SECONDS = int(os.getenv("SAMPLE_STEP_SECONDS", "60"))  # Trajectory sampling step
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))  # 24 hours default
AUTONOMY_MODE = os.getenv("AUTONOMY_MODE", "RULES").upper()  # RULES, LLM, or AGENTIC

# MongoDB collection for idempotency tracking
IDEMPOTENCY_COLLECTION = "processed_plans"


class TrajectoryInsightAgent:
    """Agent that analyzes flight trajectories and publishes insights."""

    def __init__(self):
        """Initialize the trajectory insight agent."""
        self.mongo_client = None
        self.mongo_db = None
        self.idempotency_collection = None
        self.connected = False

        # Flight collection: correlation_id -> list of flights
        self.flight_collections: Dict[str, Dict[str, Any]] = {}
        # Timers for processing collections
        self.collection_timers: Dict[str, asyncio.Task] = {}

    async def _connect_mongodb(self) -> None:
        """Connect to MongoDB for idempotency tracking."""
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
                serverSelectionTimeoutMS=5000,
            )

            # Test connection
            self.mongo_client.admin.command("ping")
            logger.info("Connected to MongoDB")

            # Get database and collection
            self.mongo_db = self.mongo_client[config["database"]]
            self.idempotency_collection = self.mongo_db[IDEMPOTENCY_COLLECTION]

            # Create TTL index on processed_at field
            try:
                self.idempotency_collection.create_index(
                    "processed_at",
                    expireAfterSeconds=IDEMPOTENCY_TTL_SECONDS,
                )
                logger.info(f"Created TTL index on processed_at (TTL: {IDEMPOTENCY_TTL_SECONDS}s)")
            except Exception as e:
                logger.debug(f"Index may already exist: {e}")

            # Create index on plan_id for fast lookups
            try:
                self.idempotency_collection.create_index("plan_id", unique=True)
                logger.info("Created unique index on plan_id")
            except Exception as e:
                logger.debug(f"Index may already exist: {e}")

            self.connected = True

        except ImportError:
            logger.error("pymongo not installed. Install with: pip install pymongo")
            raise
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}", exc_info=True)
            raise

    async def _is_plan_processed(self, plan_id: str) -> bool:
        """
        Check if a plan has already been processed (idempotency check).

        Args:
            plan_id: Plan identifier

        Returns:
            True if plan has been processed, False otherwise
        """
        if not self.connected:
            return False

        try:
            result = self.idempotency_collection.find_one({"plan_id": plan_id})
            return result is not None
        except Exception as e:
            logger.error(f"Error checking plan processing status: {e}")
            return False  # On error, allow processing (fail open)

    async def _mark_plan_processed(self, plan_id: str) -> None:
        """
        Mark a plan as processed in MongoDB.

        Args:
            plan_id: Plan identifier
        """
        if not self.connected:
            logger.warning("MongoDB not connected, skipping idempotency tracking")
            return

        try:
            self.idempotency_collection.insert_one({
                "plan_id": plan_id,
                "processed_at": datetime.utcnow(),
            })
            logger.debug(f"Marked plan {plan_id} as processed")
        except Exception as e:
            # If duplicate key error, that's okay (idempotency working)
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                logger.debug(f"Plan {plan_id} already marked as processed")
            else:
                logger.error(f"Error marking plan as processed: {e}")

    def _add_flight_to_collection(self, correlation_id: str, flight_data: Dict[str, Any]) -> None:
        """
        Add a flight to the collection for a correlation_id.

        Args:
            correlation_id: Correlation ID (plan identifier)
            flight_data: Flight parsed event data
        """
        if correlation_id not in self.flight_collections:
            self.flight_collections[correlation_id] = {
                "flights": [],
                "plan_id": None,
                "first_seen": datetime.utcnow(),
            }

        # Extract flight details from event
        details = flight_data.get("details", {})
        flight_record = {
            "flight_id": details.get("flight_id"),
            "callsign": details.get("callsign"),
            "aircraft_type": details.get("aircraft_type"),
            "origin": details.get("origin"),
            "destination": details.get("destination"),
            "departure_time": details.get("departure_time"),
            "arrival_time": details.get("arrival_time"),
            "route": details.get("route", []),
            "altitude": details.get("altitude"),
            "speed": details.get("speed"),
        }

        # Check if flight already in collection
        existing_flight_ids = [f.get("flight_id") for f in self.flight_collections[correlation_id]["flights"]]
        if flight_record["flight_id"] not in existing_flight_ids:
            self.flight_collections[correlation_id]["flights"].append(flight_record)
            logger.debug(
                f"Added flight {flight_record['flight_id']} to collection {correlation_id} "
                f"(total: {len(self.flight_collections[correlation_id]['flights'])})"
            )

        # Extract plan_id from event if available
        plan_id = details.get("plan_id")
        if plan_id:
            self.flight_collections[correlation_id]["plan_id"] = plan_id

    async def _process_collection(self, correlation_id: str) -> None:
        """
        Process a flight collection: analyze and publish events.

        Args:
            correlation_id: Correlation ID (plan identifier)
        """
        if correlation_id not in self.flight_collections:
            logger.warning(f"Collection {correlation_id} not found")
            return

        collection = self.flight_collections[correlation_id]
        flights = collection["flights"]
        plan_id = collection.get("plan_id") or correlation_id

        if not flights:
            logger.warning(f"No flights in collection {correlation_id}")
            # Clean up
            del self.flight_collections[correlation_id]
            return

        # Check idempotency
        if await self._is_plan_processed(plan_id):
            logger.info(f"Plan {plan_id} already processed, skipping (idempotency)")
            # Clean up
            del self.flight_collections[correlation_id]
            return

        logger.info(f"Processing collection {correlation_id}: {len(flights)} flights, plan_id={plan_id}")

        # Set Sentry tags
        set_tag("plan_id", plan_id)
        set_tag("autonomy_mode", AUTONOMY_MODE)

        try:
            # Add breadcrumb for processing start
            add_breadcrumb(
                message=f"Processing plan {plan_id} with {len(flights)} flights",
                category="plan.processing",
                level="info",
                data={"plan_id": plan_id, "flight_count": len(flights), "autonomy_mode": AUTONOMY_MODE},
            )

            # Analyze trajectories
            analysis_result = analyze(
                flights=flights,
                plan_window_seconds=PLAN_WINDOW_SECONDS,
                sample_step_seconds=SAMPLE_STEP_SECONDS,
            )

            conflicts = analysis_result.get("conflicts", [])
            hotspots = analysis_result.get("hotspots", [])
            violations = analysis_result.get("violations", [])
            summary = analysis_result.get("summary", {})

            # Generate solutions based on AUTONOMY_MODE
            logger.info(f"Generating solutions using AUTONOMY_MODE: {AUTONOMY_MODE}")
            if AUTONOMY_MODE == "RULES":
                solutions = generate_solutions_rules(conflicts, hotspots, flights)
            elif AUTONOMY_MODE == "LLM":
                solutions = generate_solutions_llm(conflicts, hotspots, flights)
            elif AUTONOMY_MODE == "AGENTIC":
                # In AGENTIC mode, solutions are generated by task agents via coordinator
                # Don't generate solutions here, they'll be published by coordinator
                solutions = []
                logger.info("AGENTIC mode: Solutions will be generated by task agents")
            else:
                logger.warning(f"Unknown AUTONOMY_MODE: {AUTONOMY_MODE}, falling back to RULES")
                solutions = generate_solutions_rules(conflicts, hotspots, flights)

            # Publish conflict events
            conflict_ids = []
            for conflict in conflicts:
                conflict_event = self._create_conflict_event(conflict, plan_id, correlation_id)
                conflict_id = conflict.get("conflict_id")

                # Add breadcrumb for publishing
                add_breadcrumb(
                    message=f"Publishing airspace.conflict.detected: {conflict_id}",
                    category="topic.publish",
                    level="info",
                    data={"topic": AIRSPACE_CONFLICT_DETECTED_TOPIC, "conflict_id": conflict_id, "plan_id": plan_id},
                )

                await publish(AIRSPACE_CONFLICT_DETECTED_TOPIC, conflict_event)
                capture_published_event(
                    AIRSPACE_CONFLICT_DETECTED_TOPIC,
                    conflict_event.get("event_id", "unknown"),
                    {"conflict_id": conflict_id, "plan_id": plan_id},
                )
                conflict_ids.append(conflict_id)
                logger.info(f"Published conflict event: {conflict_id}")

                # Publish geo.incident event for conflict
                geo_incident_event = self._create_geo_incident_from_conflict(conflict, correlation_id)
                await publish(GEO_INCIDENT_TOPIC, geo_incident_event)
                capture_published_event(
                    GEO_INCIDENT_TOPIC,
                    geo_incident_event.get("event_id", "unknown"),
                    {"conflict_id": conflict_id, "plan_id": plan_id},
                )
                logger.info(f"Published geo.incident event for conflict: {conflict_id}")

            # Publish hotspot events
            hotspot_ids = []
            for hotspot in hotspots:
                hotspot_event = self._create_hotspot_event(hotspot, plan_id, correlation_id)
                hotspot_id = hotspot.get("hotspot_id")

                # Add breadcrumb for publishing
                add_breadcrumb(
                    message=f"Publishing airspace.hotspot.detected: {hotspot_id}",
                    category="topic.publish",
                    level="info",
                    data={"topic": AIRSPACE_HOTSPOT_DETECTED_TOPIC, "hotspot_id": hotspot_id, "plan_id": plan_id},
                )

                await publish(AIRSPACE_HOTSPOT_DETECTED_TOPIC, hotspot_event)
                capture_published_event(
                    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
                    hotspot_event.get("event_id", "unknown"),
                    {"hotspot_id": hotspot_id, "plan_id": plan_id},
                )
                hotspot_ids.append(hotspot_id)
                logger.info(f"Published hotspot event: {hotspot_id}")

                # Publish geo.risk_area event for hotspot
                geo_risk_area_event = self._create_geo_risk_area_from_hotspot(hotspot, correlation_id)
                await publish(GEO_RISK_AREA_TOPIC, geo_risk_area_event)
                capture_published_event(
                    GEO_RISK_AREA_TOPIC,
                    geo_risk_area_event.get("event_id", "unknown"),
                    {"hotspot_id": hotspot_id, "plan_id": plan_id},
                )
                logger.info(f"Published geo.risk_area event for hotspot: {hotspot_id}")

            # Publish solution events
            solution_ids = []
            for solution in solutions:
                solution_event = self._create_solution_event(solution, plan_id, correlation_id)
                solution_id = solution.get("solution_id")

                # Add breadcrumb for publishing
                add_breadcrumb(
                    message=f"Publishing airspace.solution.proposed: {solution_id}",
                    category="topic.publish",
                    level="info",
                    data={"topic": AIRSPACE_SOLUTION_PROPOSED_TOPIC, "solution_id": solution_id, "plan_id": plan_id},
                )

                await publish(AIRSPACE_SOLUTION_PROPOSED_TOPIC, solution_event)
                capture_published_event(
                    AIRSPACE_SOLUTION_PROPOSED_TOPIC,
                    solution_event.get("event_id", "unknown"),
                    {"solution_id": solution_id, "plan_id": plan_id},
                )
                solution_ids.append(solution_id)
                logger.info(f"Published solution event: {solution_id}")

            # Publish report ready event
            report_event = self._create_report_event(
                plan_id=plan_id,
                correlation_id=correlation_id,
                summary=summary,
                conflict_ids=conflict_ids,
                hotspot_ids=hotspot_ids,
                solution_ids=solution_ids,
            )
            await publish(AIRSPACE_REPORT_READY_TOPIC, report_event)
            capture_published_event(
                AIRSPACE_REPORT_READY_TOPIC,
                report_event.get("event_id", "unknown"),
                {"plan_id": plan_id, "report_id": report_event["details"].get("report_id")},
            )
            logger.info(f"Published report ready event: {report_event['details'].get('report_id')}")

            # Mark plan as processed
            await self._mark_plan_processed(plan_id)

            logger.info(
                f"✓ Completed processing plan {plan_id}: "
                f"{len(conflicts)} conflicts, {len(hotspots)} hotspots, {len(solutions)} solutions"
            )

        except Exception as e:
            logger.error(f"Error processing collection {correlation_id}: {e}", exc_info=True)
            # Redact flight list from exception context
            capture_exception(
                e,
                {
                    "correlation_id": correlation_id,
                    "plan_id": plan_id,
                    "flight_count": len(flights),
                    # Do not include full flight list
                },
            )
        finally:
            # Clean up
            if correlation_id in self.flight_collections:
                del self.flight_collections[correlation_id]
            if correlation_id in self.collection_timers:
                del self.collection_timers[correlation_id]

    def _create_conflict_event(
        self,
        conflict: Dict[str, Any],
        plan_id: str,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Create an airspace.conflict.detected event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "trajectory-insight-agent",
            "severity": Severity.WARNING.value if conflict.get("severity_level") in ["high", "critical"] else Severity.INFO.value,
            "sector_id": "airspace-sector-1",
            "summary": f"Conflict {conflict.get('conflict_id')} detected between flights",
            "correlation_id": correlation_id,
            "details": conflict,
        }

    def _create_hotspot_event(
        self,
        hotspot: Dict[str, Any],
        plan_id: str,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Create an airspace.hotspot.detected event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "trajectory-insight-agent",
            "severity": Severity.WARNING.value if hotspot.get("severity") in ["high", "critical"] else Severity.INFO.value,
            "sector_id": "airspace-sector-1",
            "summary": f"Hotspot {hotspot.get('hotspot_id')} detected",
            "correlation_id": correlation_id,
            "details": hotspot,
        }

    def _create_geo_incident_from_conflict(
        self,
        conflict: Dict[str, Any],
        correlation_id: str,
    ) -> Dict[str, Any]:
        """
        Create a geo.incident event from a conflict.
        
        Args:
            conflict: Conflict dictionary with conflict_location and flight_ids
            correlation_id: Plan ID (correlation_id) to carry through
            
        Returns:
            Dictionary containing geo.incident event data
        """
        conflict_id = conflict.get("conflict_id", "UNKNOWN")
        conflict_location = conflict.get("conflict_location", {})
        flight_ids = conflict.get("flight_ids", [])
        
        # Extract location (midpoint of closest approach)
        lat = conflict_location.get("latitude", 0.0)
        lon = conflict_location.get("longitude", 0.0)
        
        # Determine severity
        severity_level = conflict.get("severity_level", "medium")
        if severity_level in ["high", "critical"]:
            severity = Severity.ERROR.value
        elif severity_level == "medium":
            severity = Severity.WARNING.value
        else:
            severity = Severity.INFO.value
        
        # Create label with flight IDs
        flight_ids_str = ", ".join(flight_ids[:3])  # Limit to first 3 for label
        if len(flight_ids) > 3:
            flight_ids_str += f" (+{len(flight_ids) - 3} more)"
        
        incident_id = f"GEO-{conflict_id}"
        
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "trajectory-insight-agent",
            "severity": severity,
            "sector_id": "airspace-sector-1",
            "summary": f"Conflict detected: {flight_ids_str}",
            "correlation_id": correlation_id,
            "details": {
                "id": incident_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],  # [longitude, latitude]
                },
                "style": {
                    "color": "#FF0000",  # Bright red
                    "opacity": 0.7,
                    "outline": True,
                },
                "incident_type": "airspace_conflict",
                "description": f"Airspace conflict {conflict_id} between flights {flight_ids_str} at ({lat:.4f}, {lon:.4f})",
                "status": "active",
            },
        }

    def _create_geo_risk_area_from_hotspot(
        self,
        hotspot: Dict[str, Any],
        correlation_id: str,
    ) -> Dict[str, Any]:
        """
        Create a geo.risk_area event from a hotspot.
        
        Args:
            hotspot: Hotspot dictionary with location and affected_flights
            correlation_id: Plan ID (correlation_id) to carry through
            
        Returns:
            Dictionary containing geo.risk_area event data
        """
        hotspot_id = hotspot.get("hotspot_id", "UNKNOWN")
        location = hotspot.get("location", {})
        affected_flights = hotspot.get("affected_flights", [])
        severity = hotspot.get("severity", "medium")
        density = hotspot.get("density", 0.0)
        current_count = hotspot.get("current_count", 0)
        
        # Extract location (hotspot centroid)
        lat = location.get("latitude", 0.0)
        lon = location.get("longitude", 0.0)
        radius_nm = location.get("radius_nm", 25.0)  # Default 25 nautical miles
        
        # Convert nautical miles to meters (1 nm = 1852 meters)
        radius_meters_base = radius_nm * 1852.0
        
        # Determine if regional (10-30 km) or local (1-5 km) based on severity and density
        # Regional hotspots: high severity or high density
        # Local hotspots: low/medium severity or low density
        is_regional = severity in ["high", "critical"] or density > 0.7 or current_count >= 5
        
        if is_regional:
            # Regional hotspot: 10-30 km radius
            radius_meters = min(max(radius_meters_base, 10000), 30000)
        else:
            # Local hotspot: 1-5 km radius
            radius_meters = min(max(radius_meters_base, 1000), 5000)
        
        # Determine severity level
        if severity in ["high", "critical"]:
            severity_value = Severity.ERROR.value
        elif severity == "medium":
            severity_value = Severity.WARNING.value
        else:
            severity_value = Severity.INFO.value
        
        risk_area_id = f"GEO-{hotspot_id}"
        
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "trajectory-insight-agent",
            "severity": severity_value,
            "sector_id": "airspace-sector-1",
            "summary": f"Hotspot risk area: {hotspot_id} ({current_count} flights)",
            "correlation_id": correlation_id,
            "details": {
                "id": risk_area_id,
                "geometry": {
                    "type": "Circle",
                    "coordinates": [lon, lat],  # [longitude, latitude]
                    "radius_meters": radius_meters,
                },
                "style": {
                    "color": "red",
                    "opacity": 0.35,  # As specified
                    "outline": True,
                },
                "risk_level": severity,
                "risk_type": "airspace_congestion",
                "description": f"Airspace congestion hotspot {hotspot_id} affecting {current_count} flights (density: {density:.2f} flights/hour)",
            },
        }

    def _create_solution_event(
        self,
        solution: Dict[str, Any],
        plan_id: str,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Create an airspace.solution.proposed event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "trajectory-insight-agent",
            "severity": Severity.INFO.value,
            "sector_id": "airspace-sector-1",
            "summary": f"Solution {solution.get('solution_id')} proposed",
            "correlation_id": correlation_id,
            "details": solution,
        }

    def _create_report_event(
        self,
        plan_id: str,
        correlation_id: str,
        summary: Dict[str, Any],
        conflict_ids: List[str],
        hotspot_ids: List[str],
        solution_ids: List[str],
    ) -> Dict[str, Any]:
        """Create an airspace.report.ready event."""
        report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

        # Calculate date range from summary or use defaults
        analysis_timestamp = summary.get("analysis_timestamp", datetime.utcnow().isoformat() + "Z")
        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)

        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "trajectory-insight-agent",
            "severity": Severity.INFO.value,
            "sector_id": "airspace-sector-1",
            "summary": f"Trajectory analysis report {report_id} ready for plan {plan_id}",
            "correlation_id": correlation_id,
            "details": {
                "report_id": report_id,
                "report_type": "trajectory_analysis",
                "report_period_start": period_start.isoformat() + "Z",
                "report_period_end": period_end.isoformat() + "Z",
                "report_url": f"/reports/{report_id}.json",
                "report_format": "JSON",
                "total_flights": summary.get("total_flights", 0),
                "conflicts_detected": summary.get("conflicts_detected", 0),
                "hotspots_detected": summary.get("hotspots_detected", 0),
                "solutions_proposed": summary.get("solutions_proposed", 0),
                "generated_by": "trajectory-insight-agent",
                "report_size": len(json.dumps(summary).encode("utf-8")),
                "conflict_references": conflict_ids,
                "hotspot_references": hotspot_ids,
                "solution_references": solution_ids,
            },
        }

    async def _schedule_collection_processing(self, correlation_id: str) -> None:
        """
        Schedule processing of a collection after PLAN_WINDOW_SECONDS.

        Args:
            correlation_id: Correlation ID to process
        """
        # Cancel existing timer if any
        if correlation_id in self.collection_timers:
            self.collection_timers[correlation_id].cancel()

        # Create new timer
        async def process_after_delay():
            await asyncio.sleep(PLAN_WINDOW_SECONDS)
            await self._process_collection(correlation_id)

        self.collection_timers[correlation_id] = asyncio.create_task(process_after_delay())
        logger.debug(f"Scheduled processing of {correlation_id} after {PLAN_WINDOW_SECONDS}s")

    async def _handle_flight_parsed(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Handle airspace.flight.parsed events.

        Args:
            topic: Event topic
            payload: Event payload
        """
        try:
            event_id = payload.get("event_id", "unknown")
            correlation_id = payload.get("correlation_id")
            flight_id = payload.get("details", {}).get("flight_id", "unknown")
            plan_id = payload.get("details", {}).get("plan_id")

            # Add breadcrumb for receiving event
            add_breadcrumb(
                message=f"Received airspace.flight.parsed: {flight_id}",
                category="topic.receive",
                level="info",
                data={"topic": topic, "event_id": event_id, "flight_id": flight_id, "plan_id": plan_id},
            )

            capture_received_event(topic, event_id)

            if not correlation_id:
                logger.warning("Received flight.parsed event without correlation_id, skipping")
                return

            # Add flight to collection
            self._add_flight_to_collection(correlation_id, payload)

            # Schedule processing (will reset timer if called multiple times)
            await self._schedule_collection_processing(correlation_id)

        except Exception as e:
            logger.error(f"Error handling flight.parsed event: {e}", exc_info=True)
            # Redact full payload from exception context
            capture_exception(
                e,
                {
                    "topic": topic,
                    "event_type": "flight.parsed",
                    "event_id": payload.get("event_id", "unknown"),
                    # Do not include full payload
                },
            )

    async def run(self) -> None:
        """Run the trajectory insight agent."""
        logger.info("=" * 80)
        logger.info("TRAJECTORY INSIGHT AGENT")
        logger.info("=" * 80)
        logger.info(f"Configuration:")
        logger.info(f"  PLAN_WINDOW_SECONDS: {PLAN_WINDOW_SECONDS}")
        logger.info(f"  SAMPLE_STEP_SECONDS: {SAMPLE_STEP_SECONDS}")
        logger.info(f"  IDEMPOTENCY_TTL_SECONDS: {IDEMPOTENCY_TTL_SECONDS}")
        logger.info(f"  AUTONOMY_MODE: {AUTONOMY_MODE}")
        logger.info("=" * 80)

        # Connect to MongoDB
        try:
            await self._connect_mongodb()
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}. Idempotency tracking disabled.")
            self.connected = False

        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        logger.info("Connected to message broker")

        # Subscribe to flight.parsed events
        logger.info(f"Subscribing to {AIRSPACE_FLIGHT_PARSED_TOPIC}...")
        await subscribe(AIRSPACE_FLIGHT_PARSED_TOPIC, self._handle_flight_parsed)
        logger.info("Subscribed to flight.parsed events")

        logger.info("=" * 80)
        logger.info("Trajectory Insight Agent running...")
        logger.info("Waiting for flight.parsed events...")
        logger.info("=" * 80)

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Clean up
            if self.mongo_client:
                self.mongo_client.close()
            await broker.disconnect()
            logger.info("Disconnected")


async def main() -> None:
    """Main entry point."""
    # Initialize Sentry
    init_sentry("trajectory_insight_agent", autonomy_mode=AUTONOMY_MODE)
    # Set service_name and autonomy_mode tags
    set_tag("service_name", "trajectory_insight_agent")
    set_tag("autonomy_mode", AUTONOMY_MODE)
    capture_startup(
        "trajectory_insight_agent",
        {
            "service_type": "trajectory_analysis",
            "plan_window_seconds": PLAN_WINDOW_SECONDS,
            "sample_step_seconds": SAMPLE_STEP_SECONDS,
            "autonomy_mode": AUTONOMY_MODE,
        },
    )

    agent = TrajectoryInsightAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

