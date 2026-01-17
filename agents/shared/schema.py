"""
Event schema definitions and validation for Project Chronos.

This module provides Pydantic models for event validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class Severity(str, Enum):
    """Event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
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


# Event type mapping
EVENT_SCHEMAS = {
    "power.failure": PowerFailureEvent,
    "recovery.plan": RecoveryPlanEvent,
    "operator.status": OperatorStatusEvent,
    "audit.decision": AuditDecisionEvent,
    "airspace.plan.uploaded": AirspacePlanUploadedEvent,
    "airspace.flight.parsed": AirspaceFlightParsedEvent,
    "airspace.trajectory.sampled": AirspaceTrajectorySampledEvent,
    "airspace.conflict.detected": AirspaceConflictDetectedEvent,
    "airspace.hotspot.detected": AirspaceHotspotDetectedEvent,
    "airspace.solution.proposed": AirspaceSolutionProposedEvent,
    "airspace.report.ready": AirspaceReportReadyEvent,
    "geo.incident": GeoIncidentEvent,
    "geo.risk_area": GeoRiskAreaEvent,
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

