"""
Event schema definitions and validation for Project Chronos.

This module provides Pydantic models for event validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class Severity(str, Enum):
    """Event severity levels."""
    INFO = "info"
    WARNING = "warning"
    MODERATE = "moderate"  # Renamed from ERROR for clarity
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """Base event structure with common fields."""
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event identifier (UUID)")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    source: str = Field(..., description="Source system or component that generated the event")
    severity: Severity = Field(..., description="Event severity level")
    sector_id: str = Field(..., description="Identifier for the affected sector/location")
    summary: str = Field(..., description="Brief description of the event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event-specific information")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for linking related events")

    @validator("timestamp")
    def validate_timestamp(cls, v):
        """Validate ISO 8601 timestamp format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("timestamp must be in ISO 8601 format")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }


# Power Failure Event
class PowerFailureDetails(BaseModel):
    """Details for power.failure events."""
    voltage: Optional[float] = Field(None, description="Voltage reading")
    current: Optional[float] = Field(None, description="Current reading")
    phase: Optional[str] = Field(None, description="Affected phase identifier")
    backup_status: Optional[str] = Field(None, description="Backup power system status")
    estimated_restore_time: Optional[str] = Field(None, description="Estimated restoration time (ISO 8601)")


class PowerFailureEvent(BaseEvent):
    """Power failure event schema."""
    details: PowerFailureDetails = Field(..., description="Power failure specific details")

    @classmethod
    def example_critical(cls) -> Dict[str, Any]:
        """Example critical power failure event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "power-monitoring-system",
            "severity": Severity.CRITICAL,
            "sector_id": "building-a-main",
            "summary": "Complete power failure detected in main building",
            "correlation_id": str(uuid4()),
            "details": {
                "voltage": 0,
                "current": 0,
                "phase": "all",
                "backup_status": "failed",
                "estimated_restore_time": (datetime.utcnow().replace(hour=16, minute=0, second=0, microsecond=0)).isoformat() + "Z"
            }
        }

    @classmethod
    def example_warning(cls) -> Dict[str, Any]:
        """Example warning power failure event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "power-monitoring-system",
            "severity": Severity.WARNING,
            "sector_id": "building-b-floor-3",
            "summary": "Phase 2 power failure detected",
            "correlation_id": str(uuid4()),
            "details": {
                "voltage": 0,
                "current": 0,
                "phase": "phase-2",
                "backup_status": "active",
                "estimated_restore_time": (datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0)).isoformat() + "Z"
            }
        }


# Recovery Plan Event
class RecoveryPlanStatus(str, Enum):
    """Recovery plan status values."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class RecoveryPlanDetails(BaseModel):
    """Details for recovery.plan events."""
    plan_id: str = Field(..., description="Recovery plan identifier")
    plan_name: str = Field(..., description="Recovery plan name")
    status: RecoveryPlanStatus = Field(..., description="Current plan status")
    steps: Optional[List[str]] = Field(None, description="List of recovery steps")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time (ISO 8601)")
    assigned_agents: Optional[List[str]] = Field(None, description="List of assigned agent IDs")


class RecoveryPlanEvent(BaseEvent):
    """Recovery plan event schema."""
    details: RecoveryPlanDetails = Field(..., description="Recovery plan specific details")

    @classmethod
    def example_active(cls) -> Dict[str, Any]:
        """Example active recovery plan event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "recovery-plan-coordinator",
            "severity": Severity.CRITICAL,
            "sector_id": "building-a-main",
            "summary": "Recovery plan RP-2024-001 activated for power restoration",
            "correlation_id": str(uuid4()),
            "details": {
                "plan_id": "RP-2024-001",
                "plan_name": "Main Building Power Restoration",
                "status": RecoveryPlanStatus.ACTIVE,
                "steps": [
                    "Assess damage",
                    "Isolate affected circuits",
                    "Restore backup power",
                    "Verify system integrity"
                ],
                "estimated_completion": (datetime.utcnow().replace(hour=16, minute=30, second=0, microsecond=0)).isoformat() + "Z",
                "assigned_agents": ["agent-001", "agent-002", "agent-005"]
            }
        }

    @classmethod
    def example_completed(cls) -> Dict[str, Any]:
        """Example completed recovery plan event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "recovery-plan-coordinator",
            "severity": Severity.INFO,
            "sector_id": "building-b-floor-3",
            "summary": "Recovery plan RP-2024-002 completed successfully",
            "correlation_id": str(uuid4()),
            "details": {
                "plan_id": "RP-2024-002",
                "plan_name": "Phase 2 Power Restoration",
                "status": RecoveryPlanStatus.COMPLETED,
                "steps": [
                    "Assess damage",
                    "Isolate affected circuits",
                    "Restore backup power",
                    "Verify system integrity"
                ],
                "estimated_completion": (datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0)).isoformat() + "Z",
                "assigned_agents": ["agent-003"]
            }
        }


# Operator Status Event
class OperatorStatus(str, Enum):
    """Operator status values."""
    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class OperatorStatusDetails(BaseModel):
    """Details for operator.status events."""
    operator_id: str = Field(..., description="Operator identifier")
    operator_name: str = Field(..., description="Operator name")
    status: OperatorStatus = Field(..., description="Current operator status")
    current_task: Optional[str] = Field(None, description="Current task identifier")
    location: Optional[str] = Field(None, description="Operator location")
    last_action: Optional[str] = Field(None, description="Last action performed")
    last_action_time: Optional[str] = Field(None, description="Last action timestamp (ISO 8601)")


class OperatorStatusEvent(BaseEvent):
    """Operator status event schema."""
    details: OperatorStatusDetails = Field(..., description="Operator status specific details")

    @classmethod
    def example_available(cls) -> Dict[str, Any]:
        """Example operator available event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "operator-status-monitor",
            "severity": Severity.INFO,
            "sector_id": "control-room-1",
            "summary": "Operator John Doe is now available",
            "correlation_id": str(uuid4()),
            "details": {
                "operator_id": "OP-001",
                "operator_name": "John Doe",
                "status": OperatorStatus.AVAILABLE,
                "current_task": None,
                "location": "control-room-1",
                "last_action": "completed_power_restoration",
                "last_action_time": (datetime.utcnow().replace(minute=30, second=0, microsecond=0)).isoformat() + "Z"
            }
        }

    @classmethod
    def example_offline(cls) -> Dict[str, Any]:
        """Example operator offline event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "operator-status-monitor",
            "severity": Severity.WARNING,
            "sector_id": "control-room-2",
            "summary": "Operator Jane Smith is offline",
            "correlation_id": str(uuid4()),
            "details": {
                "operator_id": "OP-002",
                "operator_name": "Jane Smith",
                "status": OperatorStatus.OFFLINE,
                "current_task": None,
                "location": None,
                "last_action": "acknowledged_alert",
                "last_action_time": (datetime.utcnow().replace(minute=55, second=0, microsecond=0)).isoformat() + "Z"
            }
        }


# Audit Decision Event
class DecisionType(str, Enum):
    """Decision type values."""
    AUTOMATED = "automated"
    MANUAL = "manual"
    HYBRID = "hybrid"


class DecisionOutcome(str, Enum):
    """Decision outcome values."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class AuditDecisionDetails(BaseModel):
    """Details for audit.decision events."""
    decision_id: str = Field(..., description="Decision identifier")
    decision_type: DecisionType = Field(..., description="Type of decision")
    decision_maker: str = Field(..., description="Agent ID or operator ID who made the decision")
    action: str = Field(..., description="Action taken")
    reasoning: Optional[str] = Field(None, description="Reasoning behind the decision")
    outcome: Optional[DecisionOutcome] = Field(None, description="Decision outcome")
    related_events: Optional[List[str]] = Field(None, description="List of related event IDs")


class AuditDecisionEvent(BaseEvent):
    """Audit decision event schema."""
    details: AuditDecisionDetails = Field(..., description="Audit decision specific details")

    @classmethod
    def example_automated(cls) -> Dict[str, Any]:
        """Example automated decision event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "autonomy-router",
            "severity": Severity.INFO,
            "sector_id": "building-a-main",
            "summary": "Automated decision to activate backup power system",
            "correlation_id": str(uuid4()),
            "details": {
                "decision_id": "DEC-2024-001",
                "decision_type": DecisionType.AUTOMATED,
                "decision_maker": "agent-001",
                "action": "activate_backup_power",
                "reasoning": "Power failure detected and backup system is operational",
                "outcome": DecisionOutcome.SUCCESS,
                "related_events": ["550e8400-e29b-41d4-a716-446655440000"]
            }
        }

    @classmethod
    def example_manual(cls) -> Dict[str, Any]:
        """Example manual decision event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "operator-dashboard",
            "severity": Severity.WARNING,
            "sector_id": "building-b-floor-3",
            "summary": "Manual decision to delay recovery plan execution",
            "correlation_id": str(uuid4()),
            "details": {
                "decision_id": "DEC-2024-002",
                "decision_type": DecisionType.MANUAL,
                "decision_maker": "OP-001",
                "action": "delay_recovery_plan",
                "reasoning": "Waiting for additional safety verification before proceeding",
                "outcome": DecisionOutcome.PENDING,
                "related_events": ["660e8400-e29b-41d4-a716-446655440000"]
            }
        }


# Airspace Domain Events

class AirspacePlanUploadedDetails(BaseModel):
    """Details for airspace.plan.uploaded events."""
    plan_id: str = Field(..., description="Flight plan identifier")
    plan_name: Optional[str] = Field(None, description="Flight plan name")
    file_path: Optional[str] = Field(None, description="Path to uploaded plan file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_format: Optional[str] = Field(None, description="File format (e.g., JSON, XML)")
    upload_timestamp: Optional[str] = Field(None, description="Upload timestamp (ISO 8601)")
    uploaded_by: Optional[str] = Field(None, description="User or system that uploaded the plan")
    flight_count: Optional[int] = Field(None, description="Number of flights in the plan")


class AirspacePlanUploadedEvent(BaseEvent):
    """Airspace plan uploaded event schema."""
    details: AirspacePlanUploadedDetails = Field(..., description="Plan upload specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example plan uploaded event."""
        plan_id = f"PLAN-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8]}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-plan-manager",
            "severity": Severity.INFO,
            "sector_id": "airspace-sector-1",
            "summary": f"Flight plan {plan_id} uploaded successfully",
            "correlation_id": str(uuid4()),
            "details": {
                "plan_id": plan_id,
                "plan_name": "Morning Rush Hour Plan",
                "file_path": "/uploads/flight_plans/2024-01-15_morning.json",
                "file_size": 245760,
                "file_format": "JSON",
                "upload_timestamp": datetime.utcnow().isoformat() + "Z",
                "uploaded_by": "operator-001",
                "flight_count": 127
            }
        }


class AircraftPositionDetails(BaseModel):
    """Details for airspace.aircraft.position events."""
    icao24: str = Field(..., description="ICAO 24-bit address")
    callsign: Optional[str] = Field(None, description="Aircraft callsign")
    latitude: float = Field(..., description="Aircraft latitude")
    longitude: float = Field(..., description="Aircraft longitude")
    altitude: Optional[float] = Field(None, description="Aircraft altitude in meters (barometric)")
    velocity: Optional[float] = Field(None, description="Aircraft velocity in m/s")
    heading: Optional[float] = Field(None, description="Aircraft heading in degrees")
    vertical_rate: Optional[float] = Field(None, description="Vertical rate in m/s")
    on_ground: Optional[bool] = Field(None, description="Whether aircraft is on ground")
    time_position: Optional[int] = Field(None, description="Unix timestamp of position")
    data_source: str = Field(default="ads-b", description="Data source (e.g., 'ads-b', 'opensky')")
    disclaimer: str = Field(default="ADS-B derived public feed - NOT official ATC data", description="Data disclaimer")


class AircraftPositionEvent(BaseEvent):
    """Aircraft position event schema."""
    details: AircraftPositionDetails = Field(..., description="Aircraft position specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example aircraft position event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "opensky_airspace",
            "severity": Severity.INFO,
            "sector_id": "ottawa-airspace",
            "summary": "Aircraft ACA123 position update",
            "correlation_id": None,
            "details": {
                "icao24": "a1b2c3",
                "callsign": "ACA123",
                "latitude": 45.4215,
                "longitude": -75.6972,
                "altitude": 10000.0,
                "velocity": 200.0,
                "heading": 180.0,
                "vertical_rate": 5.0,
                "on_ground": False,
                "time_position": int(datetime.utcnow().timestamp()),
                "data_source": "ads-b",
                "disclaimer": "ADS-B derived public feed - NOT official ATC data"
            }
        }


class AirspaceFlightParsedDetails(BaseModel):
    """Details for airspace.flight.parsed events."""
    flight_id: str = Field(..., description="Unique flight identifier")
    plan_id: str = Field(..., description="Parent flight plan identifier")
    callsign: Optional[str] = Field(None, description="Aircraft callsign")
    aircraft_type: Optional[str] = Field(None, description="Aircraft type/model")
    origin: Optional[str] = Field(None, description="Origin airport code")
    destination: Optional[str] = Field(None, description="Destination airport code")
    departure_time: Optional[str] = Field(None, description="Scheduled departure time (ISO 8601)")
    arrival_time: Optional[str] = Field(None, description="Scheduled arrival time (ISO 8601)")
    route: Optional[List[str]] = Field(None, description="List of waypoints in route")
    altitude: Optional[float] = Field(None, description="Cruising altitude in feet")
    speed: Optional[float] = Field(None, description="Cruising speed in knots")
    parse_status: Optional[str] = Field(None, description="Parse status (success|partial|failed)")
    parse_errors: Optional[List[str]] = Field(None, description="List of parse errors if any")


class AirspaceFlightParsedEvent(BaseEvent):
    """Airspace flight parsed event schema."""
    details: AirspaceFlightParsedDetails = Field(..., description="Flight parsing specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example flight parsed event."""
        flight_id = f"FLT-{str(uuid4())[:8].upper()}"
        plan_id = f"PLAN-{datetime.utcnow().strftime('%Y%m%d')}-001"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-flight-parser",
            "severity": Severity.INFO,
            "sector_id": "airspace-sector-1",
            "summary": f"Flight {flight_id} parsed successfully from plan {plan_id}",
            "correlation_id": str(uuid4()),
            "details": {
                "flight_id": flight_id,
                "plan_id": plan_id,
                "callsign": "UAL123",
                "aircraft_type": "Boeing 737-800",
                "origin": "KJFK",
                "destination": "KLAX",
                "departure_time": (datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)).isoformat() + "Z",
                "arrival_time": (datetime.utcnow().replace(hour=11, minute=30, second=0, microsecond=0)).isoformat() + "Z",
                "route": ["KJFK", "WAYPOINT1", "WAYPOINT2", "WAYPOINT3", "KLAX"],
                "altitude": 35000.0,
                "speed": 450.0,
                "parse_status": "success",
                "parse_errors": []
            }
        }


class AirspaceTrajectorySampledDetails(BaseModel):
    """Details for airspace.trajectory.sampled events."""
    flight_id: str = Field(..., description="Flight identifier")
    sample_count: Optional[int] = Field(None, description="Number of trajectory samples")
    sample_interval: Optional[float] = Field(None, description="Sampling interval in seconds")
    trajectory_points: Optional[List[Dict[str, Any]]] = Field(None, description="List of trajectory points with lat, lon, alt, time")
    start_time: Optional[str] = Field(None, description="Trajectory start time (ISO 8601)")
    end_time: Optional[str] = Field(None, description="Trajectory end time (ISO 8601)")
    total_duration: Optional[float] = Field(None, description="Total trajectory duration in seconds")
    sampling_method: Optional[str] = Field(None, description="Sampling method used")


class AirspaceTrajectorySampledEvent(BaseEvent):
    """Airspace trajectory sampled event schema."""
    details: AirspaceTrajectorySampledDetails = Field(..., description="Trajectory sampling specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example trajectory sampled event."""
        flight_id = f"FLT-{str(uuid4())[:8].upper()}"
        start_time = datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-trajectory-sampler",
            "severity": Severity.INFO,
            "sector_id": "airspace-sector-1",
            "summary": f"Trajectory sampled for flight {flight_id}",
            "correlation_id": str(uuid4()),
            "details": {
                "flight_id": flight_id,
                "sample_count": 360,
                "sample_interval": 60.0,
                "trajectory_points": [
                    {
                        "latitude": 40.6413,
                        "longitude": -73.7781,
                        "altitude": 0.0,
                        "timestamp": start_time.isoformat() + "Z"
                    },
                    {
                        "latitude": 40.7500,
                        "longitude": -74.0000,
                        "altitude": 10000.0,
                        "timestamp": (start_time.replace(minute=10)).isoformat() + "Z"
                    }
                ],
                "start_time": start_time.isoformat() + "Z",
                "end_time": (start_time.replace(hour=11, minute=30)).isoformat() + "Z",
                "total_duration": 12600.0,
                "sampling_method": "time-based"
            }
        }


class AirspaceConflictDetectedDetails(BaseModel):
    """Details for airspace.conflict.detected events."""
    conflict_id: str = Field(..., description="Unique conflict identifier")
    conflict_type: Optional[str] = Field(None, description="Type of conflict (separation|altitude|time)")
    severity_level: Optional[str] = Field(None, description="Conflict severity (low|medium|high|critical)")
    flight_ids: Optional[List[str]] = Field(None, description="List of flight IDs involved in conflict")
    conflict_location: Optional[Dict[str, Any]] = Field(None, description="Location of conflict (lat, lon, alt)")
    conflict_time: Optional[str] = Field(None, description="Predicted conflict time (ISO 8601)")
    minimum_separation: Optional[float] = Field(None, description="Minimum separation distance in nautical miles")
    required_separation: Optional[float] = Field(None, description="Required separation distance in nautical miles")
    conflict_duration: Optional[float] = Field(None, description="Conflict duration in seconds")
    detection_method: Optional[str] = Field(None, description="Method used to detect conflict")


class AirspaceConflictDetectedEvent(BaseEvent):
    """Airspace conflict detected event schema."""
    details: AirspaceConflictDetectedDetails = Field(..., description="Conflict detection specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example conflict detected event."""
        conflict_id = f"CONF-{str(uuid4())[:8].upper()}"
        flight_id_1 = f"FLT-{str(uuid4())[:8].upper()}"
        flight_id_2 = f"FLT-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-conflict-detector",
            "severity": Severity.WARNING,
            "sector_id": "airspace-sector-2",
            "summary": f"Conflict {conflict_id} detected between flights {flight_id_1} and {flight_id_2}",
            "correlation_id": str(uuid4()),
            "details": {
                "conflict_id": conflict_id,
                "conflict_type": "separation",
                "severity_level": "high",
                "flight_ids": [flight_id_1, flight_id_2],
                "conflict_location": {
                    "latitude": 39.8283,
                    "longitude": -98.5795,
                    "altitude": 35000.0
                },
                "conflict_time": (datetime.utcnow().replace(hour=9, minute=15, second=0, microsecond=0)).isoformat() + "Z",
                "minimum_separation": 2.5,
                "required_separation": 5.0,
                "conflict_duration": 120.0,
                "detection_method": "trajectory-intersection"
            }
        }


class AirspaceHotspotDetectedDetails(BaseModel):
    """Details for airspace.hotspot.detected events."""
    hotspot_id: str = Field(..., description="Unique hotspot identifier")
    hotspot_type: Optional[str] = Field(None, description="Type of hotspot (congestion|weather|restriction)")
    location: Optional[Dict[str, Any]] = Field(None, description="Hotspot location (lat, lon, alt, radius)")
    affected_flights: Optional[List[str]] = Field(None, description="List of flight IDs affected by hotspot")
    severity: Optional[str] = Field(None, description="Hotspot severity (low|medium|high|critical)")
    start_time: Optional[str] = Field(None, description="Hotspot start time (ISO 8601)")
    end_time: Optional[str] = Field(None, description="Hotspot end time (ISO 8601)")
    density: Optional[float] = Field(None, description="Aircraft density in the hotspot area")
    capacity_limit: Optional[int] = Field(None, description="Maximum capacity for the area")
    current_count: Optional[int] = Field(None, description="Current aircraft count in the area")
    description: Optional[str] = Field(None, description="Description of the hotspot")


class AirspaceHotspotDetectedEvent(BaseEvent):
    """Airspace hotspot detected event schema."""
    details: AirspaceHotspotDetectedDetails = Field(..., description="Hotspot detection specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example hotspot detected event."""
        hotspot_id = f"HOTSPOT-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-hotspot-detector",
            "severity": Severity.WARNING,
            "sector_id": "airspace-sector-3",
            "summary": f"Congestion hotspot {hotspot_id} detected in sector 3",
            "correlation_id": str(uuid4()),
            "details": {
                "hotspot_id": hotspot_id,
                "hotspot_type": "congestion",
                "location": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "altitude": 30000.0,
                    "radius_nm": 25.0
                },
                "affected_flights": [f"FLT-{str(uuid4())[:8].upper()}" for _ in range(5)],
                "severity": "high",
                "start_time": (datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)).isoformat() + "Z",
                "end_time": (datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)).isoformat() + "Z",
                "density": 0.85,
                "capacity_limit": 50,
                "current_count": 43,
                "description": "High traffic congestion in approach corridor"
            }
        }


class AirspaceSolutionProposedDetails(BaseModel):
    """Details for airspace.solution.proposed events."""
    solution_id: str = Field(..., description="Unique solution identifier")
    solution_type: Optional[str] = Field(None, description="Type of solution (reroute|delay|altitude_change|speed_adjustment)")
    problem_id: Optional[str] = Field(None, description="Problem identifier this solution addresses")
    affected_flights: Optional[List[str]] = Field(None, description="List of flight IDs affected by solution")
    proposed_actions: Optional[List[Dict[str, Any]]] = Field(None, description="List of proposed actions")
    estimated_impact: Optional[Dict[str, Any]] = Field(None, description="Estimated impact metrics")
    confidence_score: Optional[float] = Field(None, description="Confidence score (0.0-1.0)")
    generated_by: Optional[str] = Field(None, description="System or agent that generated the solution")
    requires_approval: Optional[bool] = Field(None, description="Whether solution requires manual approval")


class AirspaceSolutionProposedEvent(BaseEvent):
    """Airspace solution proposed event schema."""
    details: AirspaceSolutionProposedDetails = Field(..., description="Solution proposal specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example solution proposed event."""
        solution_id = f"SOL-{str(uuid4())[:8].upper()}"
        conflict_id = f"CONF-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-solution-generator",
            "severity": Severity.INFO,
            "sector_id": "airspace-sector-2",
            "summary": f"Solution {solution_id} proposed for conflict resolution",
            "correlation_id": str(uuid4()),
            "details": {
                "solution_id": solution_id,
                "solution_type": "reroute",
                "problem_id": conflict_id,
                "affected_flights": [f"FLT-{str(uuid4())[:8].upper()}" for _ in range(2)],
                "proposed_actions": [
                    {
                        "flight_id": "FLT-ABC123",
                        "action": "reroute",
                        "new_waypoints": ["WAYPOINT1", "WAYPOINT2", "WAYPOINT3"],
                        "delay_minutes": 5
                    },
                    {
                        "flight_id": "FLT-XYZ789",
                        "action": "altitude_change",
                        "new_altitude": 37000,
                        "delay_minutes": 0
                    }
                ],
                "estimated_impact": {
                    "total_delay_minutes": 5,
                    "fuel_impact_percent": 2.5,
                    "affected_passengers": 350
                },
                "confidence_score": 0.87,
                "generated_by": "airspace-ai-coordinator",
                "requires_approval": True
            }
        }


class AirspaceReportReadyDetails(BaseModel):
    """Details for airspace.report.ready events."""
    report_id: str = Field(..., description="Unique report identifier")
    report_type: Optional[str] = Field(None, description="Type of report (traffic|conflict|hotspot|summary)")
    report_period_start: Optional[str] = Field(None, description="Report period start time (ISO 8601)")
    report_period_end: Optional[str] = Field(None, description="Report period end time (ISO 8601)")
    report_url: Optional[str] = Field(None, description="URL or path to the report")
    report_format: Optional[str] = Field(None, description="Report format (PDF|JSON|HTML|CSV)")
    total_flights: Optional[int] = Field(None, description="Total flights in report period")
    conflicts_detected: Optional[int] = Field(None, description="Number of conflicts detected")
    hotspots_detected: Optional[int] = Field(None, description="Number of hotspots detected")
    solutions_proposed: Optional[int] = Field(None, description="Number of solutions proposed")
    generated_by: Optional[str] = Field(None, description="System that generated the report")
    report_size: Optional[int] = Field(None, description="Report size in bytes")


class AirspaceReportReadyEvent(BaseEvent):
    """Airspace report ready event schema."""
    details: AirspaceReportReadyDetails = Field(..., description="Report ready specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example report ready event."""
        report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "airspace-report-generator",
            "severity": Severity.INFO,
            "sector_id": "airspace-all-sectors",
            "summary": f"Airspace report {report_id} ready for review",
            "correlation_id": str(uuid4()),
            "details": {
                "report_id": report_id,
                "report_type": "summary",
                "report_period_start": period_start.isoformat() + "Z",
                "report_period_end": period_end.isoformat() + "Z",
                "report_url": f"/reports/{report_id}.pdf",
                "report_format": "PDF",
                "total_flights": 1247,
                "conflicts_detected": 23,
                "hotspots_detected": 8,
                "solutions_proposed": 31,
                "generated_by": "airspace-analytics-engine",
                "report_size": 2048576
            }
        }


# Geospatial Geometry Models
class PointGeometry(BaseModel):
    """Point geometry for geospatial events."""
    type: str = Field("Point", description="Geometry type")
    coordinates: List[float] = Field(..., description="Point coordinates [longitude, latitude]", min_items=2, max_items=2)

    @validator("coordinates")
    def validate_point_coordinates(cls, v):
        """Validate point coordinates."""
        if len(v) != 2:
            raise ValueError("Point coordinates must have exactly 2 elements [lon, lat]")
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v


class CircleGeometry(BaseModel):
    """Circle geometry for geospatial events."""
    type: str = Field("Circle", description="Geometry type")
    coordinates: List[float] = Field(..., description="Circle center [longitude, latitude]", min_items=2, max_items=2)
    radius_meters: float = Field(..., description="Circle radius in meters", gt=0)

    @validator("coordinates")
    def validate_circle_coordinates(cls, v):
        """Validate circle center coordinates."""
        if len(v) != 2:
            raise ValueError("Circle center must have exactly 2 elements [lon, lat]")
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v


class PolygonGeometry(BaseModel):
    """Polygon geometry for geospatial events."""
    type: str = Field("Polygon", description="Geometry type")
    coordinates: List[List[float]] = Field(..., description="Polygon coordinates as array of [lon, lat] points", min_items=3)

    @validator("coordinates")
    def validate_polygon_coordinates(cls, v):
        """Validate polygon coordinates."""
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 points")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each polygon point must have exactly 2 elements [lon, lat]")
            lon, lat = point
            if not (-180 <= lon <= 180):
                raise ValueError("Longitude must be between -180 and 180")
            if not (-90 <= lat <= 90):
                raise ValueError("Latitude must be between -90 and 90")
        # Check if polygon is closed (first point == last point)
        if v[0] != v[-1]:
            raise ValueError("Polygon must be closed (first point must equal last point)")
        return v


class GeospatialStyle(BaseModel):
    """Style configuration for geospatial overlays."""
    color: str = Field("red", description="Color in hex format (e.g., '#FF0000') or named color")
    opacity: float = Field(0.5, description="Opacity value between 0.35 and 0.7", ge=0.35, le=0.7)
    outline: bool = Field(True, description="Whether to show outline")


class GeoIncidentDetails(BaseModel):
    """Details for geo.incident events."""
    id: str = Field(..., description="Unique identifier for the incident")
    geometry: Dict[str, Any] = Field(..., description="Geometry object (Point, Circle, or Polygon)")
    style: GeospatialStyle = Field(default_factory=lambda: GeospatialStyle(), description="Style configuration")
    incident_type: Optional[str] = Field(None, description="Type of incident")
    description: Optional[str] = Field(None, description="Detailed description of the incident")
    status: Optional[str] = Field(None, description="Incident status (e.g., 'active', 'resolved')")


class GeoIncidentEvent(BaseEvent):
    """Geospatial incident event schema."""
    details: GeoIncidentDetails = Field(..., description="Geospatial incident specific details")

    @classmethod
    def example_point(cls) -> Dict[str, Any]:
        """Example point incident event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "geo-monitoring-system",
            "severity": Severity.CRITICAL,
            "sector_id": "ottawa-region",
            "summary": "Critical incident detected at coordinates",
            "correlation_id": str(uuid4()),
            "details": {
                "id": f"INCIDENT-{str(uuid4())[:8].upper()}",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-75.6972, 45.4215]  # Ottawa coordinates
                },
                "style": {
                    "color": "red",
                    "opacity": 0.7,
                    "outline": True
                },
                "incident_type": "power_outage",
                "description": "Major power outage affecting downtown area",
                "status": "active"
            }
        }

    @classmethod
    def example_circle(cls) -> Dict[str, Any]:
        """Example circle incident event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "geo-monitoring-system",
            "severity": Severity.WARNING,
            "sector_id": "ottawa-region",
            "summary": "Incident zone detected",
            "correlation_id": str(uuid4()),
            "details": {
                "id": f"INCIDENT-{str(uuid4())[:8].upper()}",
                "geometry": {
                    "type": "Circle",
                    "coordinates": [-75.6972, 45.4215],
                    "radius_meters": 5000
                },
                "style": {
                    "color": "orange",
                    "opacity": 0.5,
                    "outline": True
                },
                "incident_type": "traffic_disruption",
                "description": "Major traffic disruption in downtown core",
                "status": "active"
            }
        }


class GeoRiskAreaDetails(BaseModel):
    """Details for geo.risk_area events."""
    id: str = Field(..., description="Unique identifier for the risk area")
    geometry: Dict[str, Any] = Field(..., description="Geometry object (Point, Circle, or Polygon)")
    style: GeospatialStyle = Field(default_factory=lambda: GeospatialStyle(), description="Style configuration")
    risk_level: Optional[str] = Field(None, description="Risk level (e.g., 'low', 'medium', 'high', 'critical')")
    risk_type: Optional[str] = Field(None, description="Type of risk")
    description: Optional[str] = Field(None, description="Detailed description of the risk area")


class GeoRiskAreaEvent(BaseEvent):
    """Geospatial risk area event schema."""
    details: GeoRiskAreaDetails = Field(..., description="Geospatial risk area specific details")

    @classmethod
    def example_polygon(cls) -> Dict[str, Any]:
        """Example polygon risk area event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "risk-assessment-system",
            "severity": Severity.WARNING,
            "sector_id": "ottawa-region",
            "summary": "High-risk area identified",
            "correlation_id": str(uuid4()),
            "details": {
                "id": f"RISK-{str(uuid4())[:8].upper()}",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [-75.7072, 45.4115],
                        [-75.6872, 45.4115],
                        [-75.6872, 45.4315],
                        [-75.7072, 45.4315],
                        [-75.7072, 45.4115]  # Closed polygon
                    ]
                },
                "style": {
                    "color": "#FF0000",
                    "opacity": 0.6,
                    "outline": True
                },
                "risk_level": "high",
                "risk_type": "flood_zone",
                "description": "High-risk flood zone requiring monitoring"
            }
        }

    @classmethod
    def example_circle(cls) -> Dict[str, Any]:
        """Example circle risk area event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "risk-assessment-system",
            "severity": Severity.INFO,
            "sector_id": "ottawa-region",
            "summary": "Medium-risk area identified",
            "correlation_id": str(uuid4()),
            "details": {
                "id": f"RISK-{str(uuid4())[:8].upper()}",
                "geometry": {
                    "type": "Circle",
                    "coordinates": [-75.6972, 45.4215],
                    "radius_meters": 10000
                },
                "style": {
                    "color": "yellow",
                    "opacity": 0.4,
                    "outline": True
                },
                "risk_level": "medium",
                "risk_type": "weather_alert",
                "description": "Weather alert zone - moderate risk"
            }
        }


# Transit Domain Models (OC Transpo)
class TransitGTFSRTFetchStartedDetails(BaseModel):
    """Details for transit.gtfsrt.fetch.started events."""
    feed_url: str = Field(..., description="GTFS-RT feed URL")
    feed_type: Optional[str] = Field(None, description="Feed type (vehicle_positions|trip_updates|alerts)")
    fetch_id: Optional[str] = Field(None, description="Unique fetch identifier")
    expected_entities: Optional[int] = Field(None, description="Expected number of entities in feed")


class TransitGTFSRTFetchStartedEvent(BaseEvent):
    """Transit GTFS-RT fetch started event schema."""
    details: TransitGTFSRTFetchStartedDetails = Field(..., description="GTFS-RT fetch specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example GTFS-RT fetch started event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "transit-gtfsrt-fetcher",
            "severity": Severity.INFO,
            "sector_id": "ottawa-transit",
            "summary": "GTFS-RT feed fetch started",
            "correlation_id": str(uuid4()),
            "details": {
                "feed_url": "https://api.octranspo.com/gtfsrt/vehicle_positions",
                "feed_type": "vehicle_positions",
                "fetch_id": f"FETCH-{str(uuid4())[:8].upper()}",
                "expected_entities": 450
            }
        }


class TransitVehiclePositionDetails(BaseModel):
    """Details for transit.vehicle.position events."""
    vehicle_id: str = Field(..., description="Vehicle identifier")
    trip_id: Optional[str] = Field(None, description="Trip identifier")
    route_id: Optional[str] = Field(None, description="Route identifier")
    latitude: Optional[float] = Field(None, description="Vehicle latitude")
    longitude: Optional[float] = Field(None, description="Vehicle longitude")
    bearing: Optional[float] = Field(None, description="Vehicle bearing in degrees")
    speed: Optional[float] = Field(None, description="Vehicle speed in m/s")
    occupancy_status: Optional[str] = Field(None, description="Occupancy status")
    current_stop_sequence: Optional[int] = Field(None, description="Current stop sequence")
    current_status: Optional[str] = Field(None, description="Current status (INCOMING_AT|STOPPED_AT|IN_TRANSIT_TO)")
    timestamp: Optional[str] = Field(None, description="Position timestamp (ISO 8601)")


class TransitVehiclePositionEvent(BaseEvent):
    """Transit vehicle position event schema."""
    details: TransitVehiclePositionDetails = Field(..., description="Vehicle position specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example vehicle position event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "transit-vehicle-tracker",
            "severity": Severity.INFO,
            "sector_id": "ottawa-transit",
            "summary": f"Vehicle {str(uuid4())[:8].upper()} position update",
            "correlation_id": str(uuid4()),
            "details": {
                "vehicle_id": f"VEH-{str(uuid4())[:8].upper()}",
                "trip_id": "TRIP-12345",
                "route_id": "ROUTE-95",
                "latitude": 45.4215,
                "longitude": -75.6972,
                "bearing": 180.0,
                "speed": 12.5,
                "occupancy_status": "MANY_SEATS_AVAILABLE",
                "current_stop_sequence": 15,
                "current_status": "IN_TRANSIT_TO",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }


class TransitTripUpdateDetails(BaseModel):
    """Details for transit.trip.update events."""
    trip_id: str = Field(..., description="Trip identifier")
    route_id: Optional[str] = Field(None, description="Route identifier")
    vehicle_id: Optional[str] = Field(None, description="Vehicle identifier")
    stop_time_updates: Optional[List[Dict[str, Any]]] = Field(None, description="List of stop time updates")
    delay: Optional[int] = Field(None, description="Trip delay in seconds")
    timestamp: Optional[str] = Field(None, description="Update timestamp (ISO 8601)")


class TransitTripUpdateEvent(BaseEvent):
    """Transit trip update event schema."""
    details: TransitTripUpdateDetails = Field(..., description="Trip update specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example trip update event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "transit-trip-monitor",
            "severity": Severity.INFO,
            "sector_id": "ottawa-transit",
            "summary": f"Trip {str(uuid4())[:8].upper()} update received",
            "correlation_id": str(uuid4()),
            "details": {
                "trip_id": f"TRIP-{str(uuid4())[:8].upper()}",
                "route_id": "ROUTE-95",
                "vehicle_id": f"VEH-{str(uuid4())[:8].upper()}",
                "stop_time_updates": [
                    {
                        "stop_sequence": 15,
                        "stop_id": "STOP-12345",
                        "arrival_time": (datetime.utcnow().replace(minute=30)).isoformat() + "Z",
                        "departure_time": (datetime.utcnow().replace(minute=32)).isoformat() + "Z"
                    }
                ],
                "delay": 120,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }


class TransitDisruptionRiskDetails(BaseModel):
    """Details for transit.disruption.risk events."""
    risk_id: str = Field(..., description="Unique risk identifier")
    risk_type: Optional[str] = Field(None, description="Risk type (delay|congestion|service_interruption|weather)")
    severity_level: Optional[str] = Field(None, description="Risk severity (low|medium|high|critical)")
    affected_routes: Optional[List[str]] = Field(None, description="List of affected route IDs")
    affected_stops: Optional[List[str]] = Field(None, description="List of affected stop IDs")
    location: Optional[Dict[str, Any]] = Field(None, description="Risk location (lat, lon, radius_meters)")
    predicted_start_time: Optional[str] = Field(None, description="Predicted start time (ISO 8601)")
    predicted_end_time: Optional[str] = Field(None, description="Predicted end time (ISO 8601)")
    confidence_score: Optional[float] = Field(None, description="Confidence score (0.0-1.0)")
    risk_score: Optional[float] = Field(None, description="Risk score (0.0-1.0)")
    cause: Optional[str] = Field(None, description="Risk cause (delay_cluster|headway_gap|stalled_vehicle)")
    description: Optional[str] = Field(None, description="Risk description")


class TransitDisruptionRiskEvent(BaseEvent):
    """Transit disruption risk event schema."""
    details: TransitDisruptionRiskDetails = Field(..., description="Disruption risk specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example disruption risk event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "transit-risk-analyzer",
            "severity": Severity.WARNING,
            "sector_id": "ottawa-transit",
            "summary": f"Disruption risk {str(uuid4())[:8].upper()} detected",
            "correlation_id": str(uuid4()),
            "details": {
                "risk_id": f"RISK-{str(uuid4())[:8].upper()}",
                "risk_type": "delay",
                "severity_level": "high",
                "affected_routes": ["ROUTE-95", "ROUTE-97"],
                "affected_stops": ["STOP-12345", "STOP-12346"],
                "location": {
                    "latitude": 45.4215,
                    "longitude": -75.6972
                },
                "predicted_start_time": (datetime.utcnow().replace(hour=14, minute=0)).isoformat() + "Z",
                "predicted_end_time": (datetime.utcnow().replace(hour=16, minute=0)).isoformat() + "Z",
                "confidence_score": 0.75,
                "description": "High probability of delays due to traffic congestion"
            }
        }


class TransitHotspotDetails(BaseModel):
    """Details for transit.hotspot events."""
    hotspot_id: str = Field(..., description="Unique hotspot identifier")
    hotspot_type: Optional[str] = Field(None, description="Hotspot type (congestion|delay|service_issue)")
    location: Optional[Dict[str, Any]] = Field(None, description="Hotspot location (lat, lon, radius)")
    affected_routes: Optional[List[str]] = Field(None, description="List of affected route IDs")
    affected_vehicles: Optional[List[str]] = Field(None, description="List of affected vehicle IDs")
    severity: Optional[str] = Field(None, description="Hotspot severity (low|medium|high|critical)")
    start_time: Optional[str] = Field(None, description="Hotspot start time (ISO 8601)")
    end_time: Optional[str] = Field(None, description="Hotspot end time (ISO 8601)")
    vehicle_count: Optional[int] = Field(None, description="Number of vehicles in hotspot")
    average_delay: Optional[float] = Field(None, description="Average delay in minutes")
    description: Optional[str] = Field(None, description="Hotspot description")


class TransitHotspotEvent(BaseEvent):
    """Transit hotspot event schema."""
    details: TransitHotspotDetails = Field(..., description="Hotspot specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example hotspot event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "transit-hotspot-detector",
            "severity": Severity.WARNING,
            "sector_id": "ottawa-transit",
            "summary": f"Transit hotspot {str(uuid4())[:8].upper()} detected",
            "correlation_id": str(uuid4()),
            "details": {
                "hotspot_id": f"HOTSPOT-{str(uuid4())[:8].upper()}",
                "hotspot_type": "congestion",
                "location": {
                    "latitude": 45.4215,
                    "longitude": -75.6972,
                    "radius_meters": 500
                },
                "affected_routes": ["ROUTE-95", "ROUTE-97"],
                "affected_vehicles": [f"VEH-{str(uuid4())[:8].upper()}" for _ in range(3)],
                "severity": "high",
                "start_time": (datetime.utcnow().replace(hour=14, minute=0)).isoformat() + "Z",
                "end_time": (datetime.utcnow().replace(hour=15, minute=30)).isoformat() + "Z",
                "vehicle_count": 12,
                "average_delay": 8.5,
                "description": "High congestion hotspot in downtown core"
            }
        }


class TransitReportReadyDetails(BaseModel):
    """Details for transit.report.ready events."""
    report_id: str = Field(..., description="Unique report identifier")
    report_type: Optional[str] = Field(None, description="Report type (summary|disruption|performance|hotspot)")
    report_period_start: Optional[str] = Field(None, description="Report period start time (ISO 8601)")
    report_period_end: Optional[str] = Field(None, description="Report period end time (ISO 8601)")
    report_url: Optional[str] = Field(None, description="URL or path to the report")
    report_format: Optional[str] = Field(None, description="Report format (PDF|JSON|HTML|CSV)")
    total_vehicles: Optional[int] = Field(None, description="Total vehicles tracked")
    disruptions_detected: Optional[int] = Field(None, description="Number of disruptions detected")
    hotspots_detected: Optional[int] = Field(None, description="Number of hotspots detected")
    average_delay_minutes: Optional[float] = Field(None, description="Average delay in minutes")
    generated_by: Optional[str] = Field(None, description="System that generated the report")
    report_size: Optional[int] = Field(None, description="Report size in bytes")


class TransitReportReadyEvent(BaseEvent):
    """Transit report ready event schema."""
    details: TransitReportReadyDetails = Field(..., description="Report ready specific details")


class TransitMitigationAppliedDetails(BaseModel):
    """Details for transit.mitigation.applied events."""
    fix_id: str = Field(..., description="Fix identifier that triggered this mitigation")
    action_type: str = Field(..., description="Type of action (e.g., TRANSIT_REROUTE_SIM)")
    route_id: Optional[str] = Field(None, description="Route identifier affected")
    target: Optional[Dict[str, Any]] = Field(None, description="Action target specification")
    params: Optional[Dict[str, Any]] = Field(None, description="Action parameters")
    simulation_mode: bool = Field(True, description="Whether this is a simulation (safe sandbox)")
    what_if_active: Optional[bool] = Field(None, description="Whether this is stored as 'what-if active' scenario")


class TransitMitigationAppliedEvent(BaseEvent):
    """Transit mitigation applied event schema."""
    details: TransitMitigationAppliedDetails = Field(..., description="Mitigation applied specific details")


# Fix (Audit + Actuation) Domain Models
class ActionType(str, Enum):
    """Action type values for fix events."""
    TRANSIT_REROUTE_SIM = "TRANSIT_REROUTE_SIM"
    TRAFFIC_ADVISORY_SIM = "TRAFFIC_ADVISORY_SIM"
    AIRSPACE_MITIGATION_SIM = "AIRSPACE_MITIGATION_SIM"
    POWER_RECOVERY_SIM = "POWER_RECOVERY_SIM"


class RiskLevel(str, Enum):
    """Risk level values for fix events."""
    LOW = "low"
    MED = "med"
    HIGH = "high"


class FixSource(str, Enum):
    """Source of fix generation."""
    GEMINI = "gemini"
    RULES = "rules"
    CEREBRAS = "cerebras"


class ActionVerification(BaseModel):
    """Verification criteria for an action."""
    metric_name: str = Field(..., description="Metric name to verify (e.g., 'delay_reduction', 'risk_score')")
    threshold: float = Field(..., description="Threshold value for verification")
    window_seconds: int = Field(..., description="Time window in seconds for verification")


class ActionTarget(BaseModel):
    """Target specification for an action."""
    route_id: Optional[str] = Field(None, description="Route identifier (for transit actions)")
    sector_id: Optional[str] = Field(None, description="Sector identifier (for power/airspace actions)")
    area_bbox: Optional[Dict[str, Any]] = Field(None, description="Bounding box for area-based actions")
    stop_id: Optional[str] = Field(None, description="Stop identifier (for transit actions)")
    flight_id: Optional[str] = Field(None, description="Flight identifier (for airspace actions)")


class FixAction(BaseModel):
    """Action object for fix events."""
    type: ActionType = Field(..., description="Type of action to perform")
    target: ActionTarget = Field(..., description="Target specification for the action")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")
    verification: Optional[ActionVerification] = Field(None, description="Verification criteria for the action")


class ExpectedImpact(BaseModel):
    """Expected impact metrics for a fix."""
    delay_reduction: Optional[float] = Field(None, description="Expected delay reduction in minutes")
    risk_score_delta: Optional[float] = Field(None, description="Expected change in risk score")
    area_affected: Optional[Dict[str, Any]] = Field(None, description="Geographic area affected (bbox or geometry)")


class FixDetails(BaseModel):
    """Details for fix.* events."""
    fix_id: str = Field(..., description="Unique fix identifier (stable)")
    correlation_id: str = Field(..., description="Correlation ID linking to incident_id/hotspot_id/plan_id")
    source: FixSource = Field(..., description="Source of fix generation (gemini|rules|cerebras)")
    title: str = Field(..., description="Fix title")
    summary: str = Field(..., description="Fix summary description")
    actions: List[FixAction] = Field(..., description="List of actions to perform")
    risk_level: RiskLevel = Field(..., description="Risk level of the fix (low|med|high)")
    expected_impact: ExpectedImpact = Field(..., description="Expected impact metrics")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    proposed_by: str = Field(..., description="Agent ID or operator ID who proposed the fix")
    requires_human_approval: bool = Field(default=True, description="Whether human approval is required")
    review_notes: Optional[str] = Field(None, description="Review notes from human reviewer")
    approved_by: Optional[str] = Field(None, description="Agent ID or operator ID who approved/rejected")
    deployed_at: Optional[str] = Field(None, description="Deployment timestamp (ISO 8601)")
    verified_at: Optional[str] = Field(None, description="Verification timestamp (ISO 8601)")
    rollback_reason: Optional[str] = Field(None, description="Reason for rollback if applicable")


class FixEvent(BaseEvent):
    """Fix event schema for audit + actuation workflow."""
    details: FixDetails = Field(..., description="Fix-specific details")

    @classmethod
    def example_proposed(cls) -> Dict[str, Any]:
        """Example fix.proposed event."""
        fix_id = f"FIX-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fix-coordinator",
            "severity": Severity.WARNING,
            "sector_id": "ottawa-transit",
            "summary": f"Fix {fix_id} proposed for transit disruption",
            "correlation_id": "HOTSPOT-ABC123",
            "details": {
                "fix_id": fix_id,
                "correlation_id": "HOTSPOT-ABC123",
                "source": FixSource.GEMINI,
                "title": "Reroute Route 95 to bypass congestion",
                "summary": "Proposed reroute to reduce delays by 15 minutes",
                "actions": [
                    {
                        "type": ActionType.TRANSIT_REROUTE_SIM,
                        "target": {
                            "route_id": "ROUTE-95",
                            "area_bbox": {
                                "min_lat": 45.4115,
                                "max_lat": 45.4315,
                                "min_lon": -75.7072,
                                "max_lon": -75.6872
                            }
                        },
                        "params": {
                            "alternative_route": ["STOP-12345", "STOP-12350", "STOP-12355"],
                            "expected_delay_reduction": 15.0
                        },
                        "verification": {
                            "metric_name": "delay_reduction",
                            "threshold": 10.0,
                            "window_seconds": 300
                        }
                    }
                ],
                "risk_level": RiskLevel.MED,
                "expected_impact": {
                    "delay_reduction": 15.0,
                    "risk_score_delta": -0.2,
                    "area_affected": {
                        "type": "bbox",
                        "coordinates": {
                            "min_lat": 45.4115,
                            "max_lat": 45.4315,
                            "min_lon": -75.7072,
                            "max_lon": -75.6872
                        }
                    }
                },
                "created_at": datetime.utcnow().isoformat() + "Z",
                "proposed_by": "agent-fix-generator",
                "requires_human_approval": True
            }
        }

    @classmethod
    def example_approved(cls) -> Dict[str, Any]:
        """Example fix.approved event."""
        fix_id = f"FIX-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fix-reviewer",
            "severity": Severity.INFO,
            "sector_id": "ottawa-transit",
            "summary": f"Fix {fix_id} approved for deployment",
            "correlation_id": "HOTSPOT-ABC123",
            "details": {
                "fix_id": fix_id,
                "correlation_id": "HOTSPOT-ABC123",
                "source": FixSource.GEMINI,
                "title": "Reroute Route 95 to bypass congestion",
                "summary": "Proposed reroute to reduce delays by 15 minutes",
                "actions": [
                    {
                        "type": ActionType.TRANSIT_REROUTE_SIM,
                        "target": {
                            "route_id": "ROUTE-95"
                        },
                        "params": {
                            "alternative_route": ["STOP-12345", "STOP-12350", "STOP-12355"]
                        },
                        "verification": {
                            "metric_name": "delay_reduction",
                            "threshold": 10.0,
                            "window_seconds": 300
                        }
                    }
                ],
                "risk_level": RiskLevel.MED,
                "expected_impact": {
                    "delay_reduction": 15.0,
                    "risk_score_delta": -0.2
                },
                "created_at": (datetime.utcnow().replace(minute=0, second=0, microsecond=0)).isoformat() + "Z",
                "proposed_by": "agent-fix-generator",
                "requires_human_approval": True,
                "review_notes": "Approved after safety review",
                "approved_by": "OP-001"
            }
        }

    @classmethod
    def example_deploy_succeeded(cls) -> Dict[str, Any]:
        """Example fix.deploy_succeeded event."""
        fix_id = f"FIX-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fix-deployer",
            "severity": Severity.INFO,
            "sector_id": "ottawa-transit",
            "summary": f"Fix {fix_id} deployed successfully",
            "correlation_id": "HOTSPOT-ABC123",
            "details": {
                "fix_id": fix_id,
                "correlation_id": "HOTSPOT-ABC123",
                "source": FixSource.GEMINI,
                "title": "Reroute Route 95 to bypass congestion",
                "summary": "Proposed reroute to reduce delays by 15 minutes",
                "actions": [
                    {
                        "type": ActionType.TRANSIT_REROUTE_SIM,
                        "target": {
                            "route_id": "ROUTE-95"
                        },
                        "params": {
                            "alternative_route": ["STOP-12345", "STOP-12350", "STOP-12355"]
                        },
                        "verification": {
                            "metric_name": "delay_reduction",
                            "threshold": 10.0,
                            "window_seconds": 300
                        }
                    }
                ],
                "risk_level": RiskLevel.MED,
                "expected_impact": {
                    "delay_reduction": 15.0,
                    "risk_score_delta": -0.2
                },
                "created_at": (datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)).isoformat() + "Z",
                "proposed_by": "agent-fix-generator",
                "requires_human_approval": True,
                "approved_by": "OP-001",
                "deployed_at": datetime.utcnow().isoformat() + "Z"
            }
        }

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example report ready event."""
        report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "transit-report-generator",
            "severity": Severity.INFO,
            "sector_id": "ottawa-transit",
            "summary": f"Transit report {report_id} ready for review",
            "correlation_id": str(uuid4()),
            "details": {
                "report_id": report_id,
                "report_type": "summary",
                "report_period_start": period_start.isoformat() + "Z",
                "report_period_end": period_end.isoformat() + "Z",
                "report_url": f"/reports/transit/{report_id}.pdf",
                "report_format": "PDF",
                "total_vehicles": 450,
                "disruptions_detected": 12,
                "hotspots_detected": 5,
                "average_delay_minutes": 3.2,
                "generated_by": "transit-analytics-engine",
                "report_size": 1536000
            }
        }


# Defense Domain Events

class ThreatType(str, Enum):
    """Threat type values."""
    AIRSPACE = "airspace"
    CYBER_PHYSICAL = "cyber_physical"
    ENVIRONMENTAL = "environmental"
    CIVIL = "civil"


class ThreatSeverity(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MED = "med"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatDetails(BaseModel):
    """Details for threat events."""
    threat_id: str = Field(..., description="Unique threat identifier")
    threat_type: ThreatType = Field(..., description="Type of threat")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    severity: ThreatSeverity = Field(..., description="Threat severity level")
    affected_area: Optional[Dict[str, Any]] = Field(None, description="Geometry of affected area (GeoJSON format)")
    sources: List[str] = Field(default_factory=list, description="List of data sources (transit, satellite, airspace, traffic, infra)")
    summary: str = Field(..., description="Summary of the threat")
    detected_at: str = Field(..., description="Detection timestamp (ISO 8601)")
    disclaimer: str = Field(default="Defense features are non-kinetic and informational only.", description="Defense disclaimer")


class DefenseThreatDetectedEvent(BaseEvent):
    """Defense threat detected event schema."""
    details: ThreatDetails = Field(..., description="Threat detection specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example threat detected event."""
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-threat-detector",
            "severity": Severity.HIGH,
            "sector_id": "ottawa-airspace",
            "summary": f"Threat {threat_id} detected: Unusual airspace activity",
            "correlation_id": threat_id,
            "details": {
                "threat_id": threat_id,
                "threat_type": ThreatType.AIRSPACE,
                "confidence_score": 0.75,
                "severity": ThreatSeverity.HIGH,
                "affected_area": {
                    "type": "Polygon",
                    "coordinates": [[[-75.7, 45.4], [-75.6, 45.4], [-75.6, 45.5], [-75.7, 45.5], [-75.7, 45.4]]]
                },
                "sources": ["airspace", "satellite"],
                "summary": "Unusual airspace activity detected in Ottawa region",
                "detected_at": datetime.utcnow().isoformat() + "Z",
                "disclaimer": "Defense features are non-kinetic and informational only."
            }
        }


class DefenseThreatAssessedDetails(BaseModel):
    """Details for defense.threat.assessed events."""
    threat_id: str = Field(..., description="Threat identifier")
    assessment_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Assessment score (0.0 to 1.0)")
    risk_level: Optional[str] = Field(None, description="Assessed risk level")
    assessment_notes: Optional[str] = Field(None, description="Assessment notes")
    assessed_by: Optional[str] = Field(None, description="Agent or operator who assessed the threat")
    assessed_at: str = Field(..., description="Assessment timestamp (ISO 8601)")


class DefenseThreatAssessedEvent(BaseEvent):
    """Defense threat assessed event schema."""
    details: DefenseThreatAssessedDetails = Field(..., description="Threat assessment specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example threat assessed event."""
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-threat-assessor",
            "severity": Severity.MODERATE,
            "sector_id": "ottawa-airspace",
            "summary": f"Threat {threat_id} assessed as high risk",
            "correlation_id": threat_id,
            "details": {
                "threat_id": threat_id,
                "assessment_score": 0.85,
                "risk_level": "high",
                "assessment_notes": "Threat confirmed with high confidence, requires immediate attention",
                "assessed_by": "defense-analyst-001",
                "assessed_at": datetime.utcnow().isoformat() + "Z"
            }
        }


class DefenseThreatEscalatedDetails(BaseModel):
    """Details for defense.threat.escalated events."""
    threat_id: str = Field(..., description="Threat identifier")
    previous_severity: str = Field(..., description="Previous severity level")
    new_severity: str = Field(..., description="New severity level")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")
    escalated_by: Optional[str] = Field(None, description="Agent or operator who escalated")
    escalated_at: str = Field(..., description="Escalation timestamp (ISO 8601)")


class DefenseThreatEscalatedEvent(BaseEvent):
    """Defense threat escalated event schema."""
    details: DefenseThreatEscalatedDetails = Field(..., description="Threat escalation specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example threat escalated event."""
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-threat-monitor",
            "severity": Severity.CRITICAL,
            "sector_id": "ottawa-airspace",
            "summary": f"Threat {threat_id} escalated from high to critical",
            "correlation_id": threat_id,
            "details": {
                "threat_id": threat_id,
                "previous_severity": "high",
                "new_severity": "critical",
                "escalation_reason": "Threat activity increased significantly",
                "escalated_by": "defense-monitor-001",
                "escalated_at": datetime.utcnow().isoformat() + "Z"
            }
        }


class DefensePostureChangedDetails(BaseModel):
    """Details for defense.posture.changed events."""
    posture_id: Optional[str] = Field(None, description="Posture identifier")
    previous_posture: Optional[str] = Field(None, description="Previous defense posture")
    new_posture: str = Field(..., description="New defense posture")
    change_reason: Optional[str] = Field(None, description="Reason for posture change")
    changed_by: Optional[str] = Field(None, description="Agent or operator who changed posture")
    changed_at: str = Field(..., description="Posture change timestamp (ISO 8601)")


class DefensePostureChangedEvent(BaseEvent):
    """Defense posture changed event schema."""
    details: DefensePostureChangedDetails = Field(..., description="Posture change specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example posture changed event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-posture-manager",
            "severity": Severity.WARNING,
            "sector_id": "ottawa-region",
            "summary": "Defense posture changed to heightened alert",
            "correlation_id": str(uuid4()),
            "details": {
                "posture_id": "POSTURE-001",
                "previous_posture": "normal",
                "new_posture": "heightened_alert",
                "change_reason": "Multiple threats detected in region",
                "changed_by": "defense-coordinator-001",
                "changed_at": datetime.utcnow().isoformat() + "Z"
            }
        }


class DefenseActionProposedDetails(BaseModel):
    """Details for defense.action.proposed events."""
    action_id: str = Field(..., description="Action identifier")
    threat_id: Optional[str] = Field(None, description="Related threat identifier")
    action_type: str = Field(..., description="Type of defense action")
    action_description: str = Field(..., description="Description of the proposed action")
    proposed_by: Optional[str] = Field(None, description="Agent or operator who proposed the action")
    proposed_at: str = Field(..., description="Proposal timestamp (ISO 8601)")
    requires_approval: bool = Field(default=True, description="Whether action requires approval")


class DefenseActionProposedEvent(BaseEvent):
    """Defense action proposed event schema."""
    details: DefenseActionProposedDetails = Field(..., description="Action proposal specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example action proposed event."""
        action_id = f"ACTION-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-action-planner",
            "severity": Severity.MODERATE,
            "sector_id": "ottawa-airspace",
            "summary": f"Defense action {action_id} proposed for threat {threat_id}",
            "correlation_id": threat_id,
            "details": {
                "action_id": action_id,
                "threat_id": threat_id,
                "action_type": "informational_alert",
                "action_description": "Issue public safety advisory regarding airspace activity",
                "proposed_by": "defense-planner-001",
                "proposed_at": datetime.utcnow().isoformat() + "Z",
                "requires_approval": True
            }
        }


class DefenseActionApprovedDetails(BaseModel):
    """Details for defense.action.approved events."""
    action_id: str = Field(..., description="Action identifier")
    threat_id: Optional[str] = Field(None, description="Related threat identifier")
    approved_by: Optional[str] = Field(None, description="Agent or operator who approved the action")
    approved_at: str = Field(..., description="Approval timestamp (ISO 8601)")
    approval_notes: Optional[str] = Field(None, description="Approval notes")


class DefenseActionApprovedEvent(BaseEvent):
    """Defense action approved event schema."""
    details: DefenseActionApprovedDetails = Field(..., description="Action approval specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example action approved event."""
        action_id = f"ACTION-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-action-approver",
            "severity": Severity.INFO,
            "sector_id": "ottawa-airspace",
            "summary": f"Defense action {action_id} approved",
            "correlation_id": threat_id,
            "details": {
                "action_id": action_id,
                "threat_id": threat_id,
                "approved_by": "OP-001",
                "approved_at": datetime.utcnow().isoformat() + "Z",
                "approval_notes": "Action approved for deployment"
            }
        }


class DefenseActionDeployedDetails(BaseModel):
    """Details for defense.action.deployed events."""
    action_id: str = Field(..., description="Action identifier")
    threat_id: Optional[str] = Field(None, description="Related threat identifier")
    deployment_status: str = Field(..., description="Deployment status (success|failed|partial)")
    deployed_by: Optional[str] = Field(None, description="Agent or operator who deployed the action")
    deployed_at: str = Field(..., description="Deployment timestamp (ISO 8601)")
    deployment_notes: Optional[str] = Field(None, description="Deployment notes")


class DefenseActionDeployedEvent(BaseEvent):
    """Defense action deployed event schema."""
    details: DefenseActionDeployedDetails = Field(..., description="Action deployment specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example action deployed event."""
        action_id = f"ACTION-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-action-deployer",
            "severity": Severity.INFO,
            "sector_id": "ottawa-airspace",
            "summary": f"Defense action {action_id} deployed successfully",
            "correlation_id": threat_id,
            "details": {
                "action_id": action_id,
                "threat_id": threat_id,
                "deployment_status": "success",
                "deployed_by": "defense-deployer-001",
                "deployed_at": datetime.utcnow().isoformat() + "Z",
                "deployment_notes": "Public safety advisory issued"
            }
        }


class DefenseThreatResolvedDetails(BaseModel):
    """Details for defense.threat.resolved events."""
    threat_id: str = Field(..., description="Threat identifier")
    resolution_status: str = Field(..., description="Resolution status (resolved|mitigated|false_positive)")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    resolved_by: Optional[str] = Field(None, description="Agent or operator who resolved the threat")
    resolved_at: str = Field(..., description="Resolution timestamp (ISO 8601)")


class DefenseThreatResolvedEvent(BaseEvent):
    """Defense threat resolved event schema."""
    details: DefenseThreatResolvedDetails = Field(..., description="Threat resolution specific details")

    @classmethod
    def example(cls) -> Dict[str, Any]:
        """Example threat resolved event."""
        threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "defense-threat-resolver",
            "severity": Severity.INFO,
            "sector_id": "ottawa-airspace",
            "summary": f"Threat {threat_id} resolved",
            "correlation_id": threat_id,
            "details": {
                "threat_id": threat_id,
                "resolution_status": "resolved",
                "resolution_notes": "Threat activity ceased, no further action required",
                "resolved_by": "defense-monitor-001",
                "resolved_at": datetime.utcnow().isoformat() + "Z"
            }
        }


# Event type mapping
EVENT_SCHEMAS = {
    "power.failure": PowerFailureEvent,
    "recovery.plan": RecoveryPlanEvent,
    "operator.status": OperatorStatusEvent,
    "audit.decision": AuditDecisionEvent,
    "airspace.plan.uploaded": AirspacePlanUploadedEvent,
    "airspace.aircraft.position": AircraftPositionEvent,
    "airspace.flight.parsed": AirspaceFlightParsedEvent,
    "airspace.trajectory.sampled": AirspaceTrajectorySampledEvent,
    "airspace.conflict.detected": AirspaceConflictDetectedEvent,
    "airspace.hotspot.detected": AirspaceHotspotDetectedEvent,
    "airspace.solution.proposed": AirspaceSolutionProposedEvent,
    "airspace.report.ready": AirspaceReportReadyEvent,
    "geo.incident": GeoIncidentEvent,
    "geo.risk_area": GeoRiskAreaEvent,
    "transit.gtfsrt.fetch.started": TransitGTFSRTFetchStartedEvent,
    "transit.vehicle.position": TransitVehiclePositionEvent,
    "transit.trip.update": TransitTripUpdateEvent,
    "transit.disruption.risk": TransitDisruptionRiskEvent,
    "transit.hotspot": TransitHotspotEvent,
    "transit.report.ready": TransitReportReadyEvent,
    "transit.mitigation.applied": TransitMitigationAppliedEvent,
    "fix.proposed": FixEvent,
    "fix.review_required": FixEvent,
    "fix.approved": FixEvent,
    "fix.rejected": FixEvent,
    "fix.deploy_requested": FixEvent,
    "fix.deploy_started": FixEvent,
    "fix.deploy_succeeded": FixEvent,
    "fix.deploy_failed": FixEvent,
    "fix.verified": FixEvent,
    "fix.rollback_requested": FixEvent,
    "fix.rollback_succeeded": FixEvent,
    "defense.threat.detected": DefenseThreatDetectedEvent,
    "defense.threat.assessed": DefenseThreatAssessedEvent,
    "defense.threat.escalated": DefenseThreatEscalatedEvent,
    "defense.posture.changed": DefensePostureChangedEvent,
    "defense.action.proposed": DefenseActionProposedEvent,
    "defense.action.approved": DefenseActionApprovedEvent,
    "defense.action.deployed": DefenseActionDeployedEvent,
    "defense.threat.resolved": DefenseThreatResolvedEvent,
}


def validate_event(event_type: str, event_data: Dict[str, Any]) -> BaseEvent:
    """
    Validate an event against its schema.
    
    Args:
        event_type: Event type (e.g., "power.failure")
        event_data: Event data dictionary
        
    Returns:
        Validated event model instance
        
    Raises:
        ValueError: If event type is unknown or validation fails
    """
    if event_type not in EVENT_SCHEMAS:
        raise ValueError(f"Unknown event type: {event_type}")
    
    schema_class = EVENT_SCHEMAS[event_type]
    return schema_class(**event_data)


def serialize_event(event: BaseEvent) -> Dict[str, Any]:
    """
    Serialize an event to a dictionary.
    
    Args:
        event: Event model instance
        
    Returns:
        Dictionary representation of the event
    """
    return event.dict()


def deserialize_event(event_type: str, event_data: Dict[str, Any]) -> BaseEvent:
    """
    Deserialize and validate an event from a dictionary.
    
    Args:
        event_type: Event type (e.g., "power.failure")
        event_data: Event data dictionary
        
    Returns:
        Validated event model instance
    """
    return validate_event(event_type, event_data)

