"""
Flight Plan Ingestor Service

SYNTHETIC DATA - NOT FOR OPERATIONAL USE

Ingests flight plan JSON files and publishes airspace events.
Accepts file path from CLI or reads from stdin.

WARNING: This is a SYNTHETIC data generator for demonstration purposes only.
DO NOT use this for operational air traffic control or real flight planning.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.schema import (
    AirspacePlanUploadedEvent,
    AirspaceFlightParsedEvent,
    Severity,
)
from agents.shared.constants import (
    AIRSPACE_PLAN_UPLOADED_TOPIC,
    AIRSPACE_FLIGHT_PARSED_TOPIC,
)
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_published_event,
    capture_exception,
    add_breadcrumb,
    set_tag,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# SYNTHETIC DATA DISCLAIMER
SYNTHETIC_DISCLAIMER = """
================================================================================
                    ⚠️  SYNTHETIC DATA WARNING  ⚠️
================================================================================
This system processes SYNTHETIC flight plan data for demonstration purposes.

DO NOT USE FOR OPERATIONAL AIR TRAFFIC CONTROL OR REAL FLIGHT PLANNING.

All data is simulated and should not be used for:
- Real-time air traffic management
- Flight safety decisions
- Operational planning
- Regulatory compliance

This is a DEMO SYSTEM ONLY.
================================================================================
"""


class FlightPlanValidator:
    """Validates flight plan JSON against synthetic schema."""

    REQUIRED_FIELDS = [
        "ACID",  # Aircraft ID / Callsign
        "Plane type",  # Aircraft type
        "route",  # Route waypoints
        "altitude",  # Cruising altitude
        "departure airport",  # Origin airport code
        "arrival airport",  # Destination airport code
        "departure time",  # Departure timestamp
        "aircraft speed",  # Speed in knots
        "passengers",  # Number of passengers
        "is_cargo",  # Boolean cargo flag
    ]

    @staticmethod
    def validate_flight(flight: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single flight record.

        Args:
            flight: Flight record dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        for field in FlightPlanValidator.REQUIRED_FIELDS:
            if field not in flight:
                errors.append(f"Missing required field: {field}")

        # Validate specific field types
        if "ACID" in flight and not isinstance(flight["ACID"], str):
            errors.append("ACID must be a string")

        if "Plane type" in flight and not isinstance(flight["Plane type"], str):
            errors.append("Plane type must be a string")

        if "route" in flight:
            if not isinstance(flight["route"], list):
                errors.append("route must be a list")
            elif len(flight["route"]) < 2:
                errors.append("route must contain at least 2 waypoints")

        if "altitude" in flight:
            if not isinstance(flight["altitude"], (int, float)):
                errors.append("altitude must be a number")
            elif flight["altitude"] < 0 or flight["altitude"] > 50000:
                errors.append("altitude must be between 0 and 50000 feet")

        if "departure airport" in flight and not isinstance(flight["departure airport"], str):
            errors.append("departure airport must be a string")

        if "arrival airport" in flight and not isinstance(flight["arrival airport"], str):
            errors.append("arrival airport must be a string")

        if "departure time" in flight:
            if not isinstance(flight["departure time"], str):
                errors.append("departure time must be a string (ISO 8601)")

        if "aircraft speed" in flight:
            if not isinstance(flight["aircraft speed"], (int, float)):
                errors.append("aircraft speed must be a number")
            elif flight["aircraft speed"] < 0 or flight["aircraft speed"] > 1000:
                errors.append("aircraft speed must be between 0 and 1000 knots")

        if "passengers" in flight:
            if not isinstance(flight["passengers"], int):
                errors.append("passengers must be an integer")
            elif flight["passengers"] < 0:
                errors.append("passengers must be non-negative")

        if "is_cargo" in flight and not isinstance(flight["is_cargo"], bool):
            errors.append("is_cargo must be a boolean")

        return len(errors) == 0, errors

    @staticmethod
    def validate_plan(plan_data: Dict[str, Any]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Validate flight plan structure and all flights.

        Args:
            plan_data: Flight plan dictionary (should contain 'flights' array)

        Returns:
            Tuple of (is_valid, list_of_errors, list_of_valid_flights)
        """
        errors = []
        valid_flights = []

        # Check if plan has flights array
        if "flights" not in plan_data:
            errors.append("Flight plan must contain 'flights' array")
            return False, errors, valid_flights

        if not isinstance(plan_data["flights"], list):
            errors.append("'flights' must be an array")
            return False, errors, valid_flights

        if len(plan_data["flights"]) == 0:
            errors.append("Flight plan must contain at least one flight")
            return False, errors, valid_flights

        # Validate each flight
        for idx, flight in enumerate(plan_data["flights"]):
            if not isinstance(flight, dict):
                errors.append(f"Flight at index {idx} must be an object")
                continue

            is_valid, flight_errors = FlightPlanValidator.validate_flight(flight)
            if is_valid:
                valid_flights.append(flight)
            else:
                errors.extend([f"Flight {idx}: {e}" for e in flight_errors])

        return len(errors) == 0, errors, valid_flights


def calculate_arrival_time(
    departure_time: str,
    route: List[str],
    speed: float,
    altitude: float,
) -> str:
    """
    Calculate estimated arrival time based on route and speed.

    Args:
        departure_time: Departure time (ISO 8601)
        route: List of waypoints
        speed: Aircraft speed in knots
        altitude: Cruising altitude in feet

    Returns:
        Estimated arrival time (ISO 8601)
    """
    try:
        dep_time = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
        
        # Rough estimate: assume 100nm per waypoint segment at cruising speed
        # This is synthetic, so we use a simple heuristic
        waypoint_segments = max(1, len(route) - 1)
        estimated_hours = (waypoint_segments * 100) / max(speed, 100)  # Avoid division by zero
        
        arr_time = dep_time + timedelta(hours=estimated_hours)
        return arr_time.isoformat().replace("+00:00", "Z")
    except Exception:
        # Fallback: add 3 hours if calculation fails
        try:
            dep_time = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
            arr_time = dep_time + timedelta(hours=3)
            return arr_time.isoformat().replace("+00:00", "Z")
        except Exception:
            # Last resort: return departure time + 3 hours as string
            return (datetime.utcnow() + timedelta(hours=3)).isoformat() + "Z"


def normalize_flight_to_parsed_event(
    flight: Dict[str, Any],
    plan_id: str,
    correlation_id: str,
) -> Dict[str, Any]:
    """
    Convert a flight record to an airspace.flight.parsed event.

    Args:
        flight: Flight record from JSON
        plan_id: Parent flight plan ID
        correlation_id: Correlation ID for linking events

    Returns:
        Event dictionary ready for publishing
    """
    # Generate flight ID from ACID or create one
    flight_id = f"FLT-{flight.get('ACID', str(uuid4())[:8].upper())}"

    # Calculate arrival time if not provided
    arrival_time = calculate_arrival_time(
        flight.get("departure time", datetime.utcnow().isoformat() + "Z"),
        flight.get("route", []),
        flight.get("aircraft speed", 450.0),
        flight.get("altitude", 35000.0),
    )

    # Build event
    event_data = {
        "event_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "flight-plan-ingestor",
        "severity": Severity.INFO.value,
        "sector_id": "airspace-sector-1",  # Default sector
        "summary": f"Flight {flight_id} parsed from plan {plan_id}",
        "correlation_id": correlation_id,
        "details": {
            "flight_id": flight_id,
            "plan_id": plan_id,
            "callsign": flight.get("ACID"),
            "aircraft_type": flight.get("Plane type"),
            "origin": flight.get("departure airport"),
            "destination": flight.get("arrival airport"),
            "departure_time": flight.get("departure time"),
            "arrival_time": arrival_time,
            "route": flight.get("route", []),
            "altitude": float(flight.get("altitude", 0)),
            "speed": float(flight.get("aircraft speed", 0)),
            "parse_status": "success",
            "parse_errors": [],
        },
    }

    return event_data


def create_plan_uploaded_event(
    plan_id: str,
    file_path: Optional[str],
    flight_count: int,
    date_range: Dict[str, str],
    correlation_id: str,
) -> Dict[str, Any]:
    """
    Create an airspace.plan.uploaded event.

    Args:
        plan_id: Flight plan identifier
        file_path: Path to the uploaded file (if any)
        flight_count: Number of flights in the plan
        date_range: Dictionary with 'start' and 'end' timestamps
        correlation_id: Correlation ID for linking events

    Returns:
        Event dictionary ready for publishing
    """
    file_size = None
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)

    event_data = {
        "event_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "flight-plan-ingestor",
        "severity": Severity.INFO.value,
        "sector_id": "airspace-sector-1",
        "summary": f"Flight plan {plan_id} uploaded with {flight_count} flights",
        "correlation_id": correlation_id,
        "details": {
            "plan_id": plan_id,
            "plan_name": f"Flight Plan {plan_id}",
            "file_path": file_path,
            "file_size": file_size,
            "file_format": "JSON",
            "upload_timestamp": datetime.utcnow().isoformat() + "Z",
            "uploaded_by": "flight-plan-ingestor",
            "flight_count": flight_count,
        },
    }

    return event_data


def extract_date_range(flights: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract date range from flight departure times.

    Args:
        flights: List of flight records

    Returns:
        Dictionary with 'start' and 'end' timestamps
    """
    departure_times = []
    for flight in flights:
        dep_time = flight.get("departure time")
        if dep_time:
            try:
                dt = datetime.fromisoformat(dep_time.replace("Z", "+00:00"))
                departure_times.append(dt)
            except Exception:
                pass

    if not departure_times:
        # Default to today
        now = datetime.utcnow()
        return {
            "start": now.isoformat() + "Z",
            "end": (now + timedelta(hours=24)).isoformat() + "Z",
        }

    start_time = min(departure_times)
    end_time = max(departure_times)

    return {
        "start": start_time.isoformat().replace("+00:00", "Z"),
        "end": end_time.isoformat().replace("+00:00", "Z"),
    }


async def ingest_flight_plan(
    plan_data: Dict[str, Any],
    file_path: Optional[str] = None,
) -> None:
    """
    Ingest a flight plan and publish events.

    Args:
        plan_data: Flight plan dictionary
        file_path: Optional file path for metadata
    """
    logger.info("=" * 80)
    logger.info(SYNTHETIC_DISCLAIMER)
    logger.info("=" * 80)

    # Validate flight plan
    logger.info("Validating flight plan...")
    is_valid, errors, valid_flights = FlightPlanValidator.validate_plan(plan_data)

    if not is_valid:
        logger.error("Flight plan validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        # Redact flight list from exception context
        capture_exception(
            ValueError(f"Flight plan validation failed: {len(errors)} errors"),
            {
                "error_count": len(errors),
                "validation_errors": errors[:10],  # Only first 10 errors
                # Do not include full flight list
            },
        )
        raise ValueError(f"Flight plan validation failed: {len(errors)} errors")

    logger.info(f"✓ Flight plan validated: {len(valid_flights)} flights")

    # Generate plan ID and correlation ID
    plan_id = f"PLAN-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    correlation_id = str(uuid4())

    # Extract date range
    date_range = extract_date_range(valid_flights)

    # Connect to message broker
    logger.info("Connecting to message broker...")
    broker = await get_broker()
    logger.info("Connected to message broker")

    # Set Sentry tags
    set_tag("plan_id", plan_id)

    # Publish plan.uploaded event
    logger.info("=" * 80)
    logger.info("Publishing airspace.plan.uploaded event...")
    logger.info("=" * 80)

    plan_event = create_plan_uploaded_event(
        plan_id=plan_id,
        file_path=file_path,
        flight_count=len(valid_flights),
        date_range=date_range,
        correlation_id=correlation_id,
    )

    # Add breadcrumb for publishing
    add_breadcrumb(
        message=f"Publishing airspace.plan.uploaded for plan {plan_id}",
        category="topic.publish",
        level="info",
        data={"topic": AIRSPACE_PLAN_UPLOADED_TOPIC, "plan_id": plan_id, "flight_count": len(valid_flights)},
    )

    await publish(AIRSPACE_PLAN_UPLOADED_TOPIC, plan_event)
    capture_published_event(
        AIRSPACE_PLAN_UPLOADED_TOPIC,
        plan_event.get("event_id", "unknown"),
        {"plan_id": plan_id, "flight_count": len(valid_flights)},
    )

    logger.info(f"✓ Published plan.uploaded event: {plan_id}")
    logger.info(f"  Flights: {len(valid_flights)}")
    logger.info(f"  Date range: {date_range['start']} to {date_range['end']}")

    # Publish flight.parsed events
    logger.info("=" * 80)
    logger.info(f"Publishing {len(valid_flights)} airspace.flight.parsed events...")
    logger.info("=" * 80)

    for idx, flight in enumerate(valid_flights, 1):
        try:
            flight_event = normalize_flight_to_parsed_event(
                flight=flight,
                plan_id=plan_id,
                correlation_id=correlation_id,
            )

            flight_id = flight_event["details"].get("flight_id")
            callsign = flight.get("ACID", "UNKNOWN")

            # Add breadcrumb for publishing
            add_breadcrumb(
                message=f"Publishing airspace.flight.parsed for flight {callsign}",
                category="topic.publish",
                level="info",
                data={"topic": AIRSPACE_FLIGHT_PARSED_TOPIC, "flight_id": flight_id, "plan_id": plan_id, "callsign": callsign},
            )

            await publish(AIRSPACE_FLIGHT_PARSED_TOPIC, flight_event)
            capture_published_event(
                AIRSPACE_FLIGHT_PARSED_TOPIC,
                flight_event.get("event_id", "unknown"),
                {
                    "flight_id": flight_id,
                    "plan_id": plan_id,
                },
            )

            logger.info(f"✓ [{idx}/{len(valid_flights)}] Published flight.parsed: {callsign}")

        except Exception as e:
            logger.error(f"✗ Failed to publish flight {idx}: {e}")
            # Redact flight data from exception context
            capture_exception(
                e,
                {
                    "flight_index": idx,
                    "plan_id": plan_id,
                    "callsign": flight.get("ACID", "UNKNOWN"),
                    # Do not include full flight object
                },
            )

    logger.info("=" * 80)
    logger.info("✓ Flight plan ingestion complete")
    logger.info("=" * 80)
    logger.info(SYNTHETIC_DISCLAIMER)
    logger.info("=" * 80)

    # Disconnect from broker
    await broker.disconnect()
    logger.info("Disconnected from message broker")


def load_flight_plan(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load flight plan from file or stdin.

    Args:
        file_path: Optional path to JSON file

    Returns:
        Flight plan dictionary
    """
    if file_path:
        logger.info(f"Loading flight plan from file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        logger.info("Reading flight plan from stdin...")
        return json.load(sys.stdin)


async def main() -> None:
    """Main entry point for the flight plan ingestor."""
    # Initialize Sentry
    init_sentry("flight_plan_ingestor")
    # Set service_name tag (autonomy_mode not applicable for ingestor)
    set_tag("service_name", "flight_plan_ingestor")
    capture_startup("flight_plan_ingestor", {"service_type": "data_ingestion"})

    parser = argparse.ArgumentParser(
        description="Flight Plan Ingestor - SYNTHETIC DATA ONLY - NOT FOR OPERATIONAL USE"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to flight plan JSON file (if not provided, reads from stdin)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the flight plan, do not publish events",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("FLIGHT PLAN INGESTOR")
    logger.info("=" * 80)
    logger.info(SYNTHETIC_DISCLAIMER)

    try:
        # Load flight plan
        plan_data = load_flight_plan(args.file)

        # Validate
        is_valid, errors, valid_flights = FlightPlanValidator.validate_plan(plan_data)

        if not is_valid:
            logger.error("Flight plan validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        logger.info(f"✓ Flight plan validated: {len(valid_flights)} flights")

        if args.validate_only:
            logger.info("Validation-only mode: not publishing events")
            sys.exit(0)

        # Ingest and publish events
        await ingest_flight_plan(plan_data, file_path=args.file)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        capture_exception(e, {"service": "flight_plan_ingestor", "error_type": "fatal"})
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

