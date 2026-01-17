# Event Schema Documentation

This document defines the event schema for Project Chronos. All events follow a consistent JSON structure and are published to RabbitMQ topics.

## Common Event Structure

All events must include the following base fields:

- `event_id` (string, UUID): Unique identifier for the event
- `timestamp` (string, ISO 8601): Event creation timestamp
- `severity` (string, enum): Event severity level
- `sector_id` (string): Identifier for the affected sector/location
- `summary` (string): Brief description of the event
- `details` (object): Additional event-specific information

### Severity Levels

- `info`: Informational event
- `warning`: Warning condition
- `error`: Error condition
- `critical`: Critical condition requiring immediate attention

## Event Topics

### power.failure

Power failure events indicating electrical system issues.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "voltage": "number (optional)",
    "current": "number (optional)",
    "phase": "string (optional)",
    "backup_status": "string (optional)",
    "estimated_restore_time": "string (ISO 8601, optional)"
  }
}
```

**Example 1: Critical Power Failure**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:30:00Z",
  "severity": "critical",
  "sector_id": "building-a-main",
  "summary": "Complete power failure detected in main building",
  "details": {
    "voltage": 0,
    "current": 0,
    "phase": "all",
    "backup_status": "failed",
    "estimated_restore_time": "2024-01-15T16:00:00Z"
  }
}
```

**Example 2: Partial Power Failure**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:35:00Z",
  "severity": "warning",
  "sector_id": "building-b-floor-3",
  "summary": "Phase 2 power failure detected",
  "details": {
    "voltage": 0,
    "current": 0,
    "phase": "phase-2",
    "backup_status": "active",
    "estimated_restore_time": "2024-01-15T15:00:00Z"
  }
}
```

### recovery.plan

Recovery plan events for crisis response and restoration procedures.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "plan_id": "string",
    "plan_name": "string",
    "status": "string (draft|active|completed|failed)",
    "steps": "array (optional)",
    "estimated_completion": "string (ISO 8601, optional)",
    "assigned_agents": "array (optional)"
  }
}
```

**Example 1: Recovery Plan Activated**
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:40:00Z",
  "severity": "critical",
  "sector_id": "building-a-main",
  "summary": "Recovery plan RP-2024-001 activated for power restoration",
  "details": {
    "plan_id": "RP-2024-001",
    "plan_name": "Main Building Power Restoration",
    "status": "active",
    "steps": [
      "Assess damage",
      "Isolate affected circuits",
      "Restore backup power",
      "Verify system integrity"
    ],
    "estimated_completion": "2024-01-15T16:30:00Z",
    "assigned_agents": ["agent-001", "agent-002", "agent-005"]
  }
}
```

**Example 2: Recovery Plan Completed**
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T16:25:00Z",
  "severity": "info",
  "sector_id": "building-b-floor-3",
  "summary": "Recovery plan RP-2024-002 completed successfully",
  "details": {
    "plan_id": "RP-2024-002",
    "plan_name": "Phase 2 Power Restoration",
    "status": "completed",
    "steps": [
      "Assess damage",
      "Isolate affected circuits",
      "Restore backup power",
      "Verify system integrity"
    ],
    "estimated_completion": "2024-01-15T15:00:00Z",
    "assigned_agents": ["agent-003"]
  }
}
```

### operator.status

Operator status events tracking human operator availability and actions.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "operator_id": "string",
    "operator_name": "string",
    "status": "string (available|busy|away|offline)",
    "current_task": "string (optional)",
    "location": "string (optional)",
    "last_action": "string (optional)",
    "last_action_time": "string (ISO 8601, optional)"
  }
}
```

**Example 1: Operator Available**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:45:00Z",
  "severity": "info",
  "sector_id": "control-room-1",
  "summary": "Operator John Doe is now available",
  "details": {
    "operator_id": "OP-001",
    "operator_name": "John Doe",
    "status": "available",
    "current_task": null,
    "location": "control-room-1",
    "last_action": "completed_power_restoration",
    "last_action_time": "2024-01-15T14:30:00Z"
  }
}
```

**Example 2: Operator Offline**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T15:00:00Z",
  "severity": "warning",
  "sector_id": "control-room-2",
  "summary": "Operator Jane Smith is offline",
  "details": {
    "operator_id": "OP-002",
    "operator_name": "Jane Smith",
    "status": "offline",
    "current_task": null,
    "location": null,
    "last_action": "acknowledged_alert",
    "last_action_time": "2024-01-15T14:55:00Z"
  }
}
```

### audit.decision

Audit decision events for tracking automated and manual decisions in the system.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "decision_id": "string",
    "decision_type": "string (automated|manual|hybrid)",
    "decision_maker": "string (agent_id or operator_id)",
    "action": "string",
    "reasoning": "string (optional)",
    "outcome": "string (success|failure|pending, optional)",
    "related_events": "array (optional)"
  }
}
```

**Example 1: Automated Decision**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:50:00Z",
  "severity": "info",
  "sector_id": "building-a-main",
  "summary": "Automated decision to activate backup power system",
  "details": {
    "decision_id": "DEC-2024-001",
    "decision_type": "automated",
    "decision_maker": "agent-001",
    "action": "activate_backup_power",
    "reasoning": "Power failure detected and backup system is operational",
    "outcome": "success",
    "related_events": [
      "550e8400-e29b-41d4-a716-446655440000"
    ]
  }
}
```

**Example 2: Manual Decision**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T15:10:00Z",
  "severity": "warning",
  "sector_id": "building-b-floor-3",
  "summary": "Manual decision to delay recovery plan execution",
  "details": {
    "decision_id": "DEC-2024-002",
    "decision_type": "manual",
    "decision_maker": "OP-001",
    "action": "delay_recovery_plan",
    "reasoning": "Waiting for additional safety verification before proceeding",
    "outcome": "pending",
    "related_events": [
      "660e8400-e29b-41d4-a716-446655440000"
    ]
  }
}
```

## Event Validation

All events should be validated against this schema before publishing. The Python schema implementation in `agents/shared/schema.py` provides validation utilities.

## Event Routing

Events are published to RabbitMQ topics matching the event type:
- `power.failure` → `chronos.events.power.failure`
- `recovery.plan` → `chronos.events.recovery.plan`
- `operator.status` → `chronos.events.operator.status`
- `audit.decision` → `chronos.events.audit.decision`

## Best Practices

1. Always generate a unique UUID for `event_id`
2. Use ISO 8601 format for all timestamps (UTC recommended)
3. Set appropriate severity levels based on impact
4. Include relevant context in `details` object
5. Link related events using `related_events` array when applicable
6. Validate events before publishing to ensure schema compliance

