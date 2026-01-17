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
    severity: Severity = Field(..., description="Event severity level")
    sector_id: str = Field(..., description="Identifier for the affected sector/location")
    summary: str = Field(..., description="Brief description of the event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event-specific information")

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
            "severity": Severity.CRITICAL,
            "sector_id": "building-a-main",
            "summary": "Complete power failure detected in main building",
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
            "severity": Severity.WARNING,
            "sector_id": "building-b-floor-3",
            "summary": "Phase 2 power failure detected",
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
            "severity": Severity.CRITICAL,
            "sector_id": "building-a-main",
            "summary": "Recovery plan RP-2024-001 activated for power restoration",
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
            "severity": Severity.INFO,
            "sector_id": "building-b-floor-3",
            "summary": "Recovery plan RP-2024-002 completed successfully",
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
            "severity": Severity.INFO,
            "sector_id": "control-room-1",
            "summary": "Operator John Doe is now available",
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
            "severity": Severity.WARNING,
            "sector_id": "control-room-2",
            "summary": "Operator Jane Smith is offline",
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
            "severity": Severity.INFO,
            "sector_id": "building-a-main",
            "summary": "Automated decision to activate backup power system",
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
            "severity": Severity.WARNING,
            "sector_id": "building-b-floor-3",
            "summary": "Manual decision to delay recovery plan execution",
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


# Event type mapping
EVENT_SCHEMAS = {
    "power.failure": PowerFailureEvent,
    "recovery.plan": RecoveryPlanEvent,
    "operator.status": OperatorStatusEvent,
    "audit.decision": AuditDecisionEvent,
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

