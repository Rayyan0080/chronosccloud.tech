# Event Schema Documentation

This document defines the event schema for Project Chronos. All events follow a consistent JSON structure and are published to RabbitMQ topics.

## Common Event Structure

All events must include the following base fields:

- `event_id` (string, UUID): Unique identifier for the event
- `timestamp` (string, ISO 8601): Event creation timestamp
- `source` (string): Source system or component that generated the event
- `severity` (string, enum): Event severity level
- `sector_id` (string): Identifier for the affected sector/location
- `summary` (string): Brief description of the event
- `details` (object): Additional event-specific information
- `correlation_id` (string, UUID, optional): Correlation ID for linking related events

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
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "voltage": "number (optional)",
    "current": "number (optional)",
    "phase": "string (optional)",
    "backup_status": "string (optional)",
    "estimated_restore_time": "string (ISO 8601, optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Critical Power Failure**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:30:00Z",
  "source": "power-monitoring-system",
  "severity": "critical",
  "sector_id": "building-a-main",
  "summary": "Complete power failure detected in main building",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440000",
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
  "source": "power-monitoring-system",
  "severity": "warning",
  "sector_id": "building-b-floor-3",
  "summary": "Phase 2 power failure detected",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440001",
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
  "source": "string",
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
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Recovery Plan Activated**
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:40:00Z",
  "source": "recovery-plan-coordinator",
  "severity": "critical",
  "sector_id": "building-a-main",
  "summary": "Recovery plan RP-2024-001 activated for power restoration",
  "correlation_id": "770e8400-e29b-41d4-a716-446655440000",
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
  "source": "recovery-plan-coordinator",
  "severity": "info",
  "sector_id": "building-b-floor-3",
  "summary": "Recovery plan RP-2024-002 completed successfully",
  "correlation_id": "770e8400-e29b-41d4-a716-446655440001",
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
  "source": "string",
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
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Operator Available**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:45:00Z",
  "source": "operator-status-monitor",
  "severity": "info",
  "sector_id": "control-room-1",
  "summary": "Operator John Doe is now available",
  "correlation_id": "880e8400-e29b-41d4-a716-446655440000",
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
  "source": "operator-status-monitor",
  "severity": "warning",
  "sector_id": "control-room-2",
  "summary": "Operator Jane Smith is offline",
  "correlation_id": "880e8400-e29b-41d4-a716-446655440001",
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
  "source": "string",
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
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Automated Decision**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:50:00Z",
  "source": "autonomy-router",
  "severity": "info",
  "sector_id": "building-a-main",
  "summary": "Automated decision to activate backup power system",
  "correlation_id": "990e8400-e29b-41d4-a716-446655440000",
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
  "source": "operator-dashboard",
  "severity": "warning",
  "sector_id": "building-b-floor-3",
  "summary": "Manual decision to delay recovery plan execution",
  "correlation_id": "990e8400-e29b-41d4-a716-446655440001",
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

### airspace.plan.uploaded

Flight plan uploaded events indicating new flight plans have been received.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "plan_id": "string",
    "plan_name": "string (optional)",
    "file_path": "string (optional)",
    "file_size": "number (optional)",
    "file_format": "string (optional)",
    "upload_timestamp": "string (ISO 8601, optional)",
    "uploaded_by": "string (optional)",
    "flight_count": "number (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Flight Plan Uploaded**
```json
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T08:00:00Z",
  "source": "airspace-plan-manager",
  "severity": "info",
  "sector_id": "airspace-sector-1",
  "summary": "Flight plan PLAN-20240115-ABC123 uploaded successfully",
  "correlation_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "plan_id": "PLAN-20240115-ABC123",
    "plan_name": "Morning Rush Hour Plan",
    "file_path": "/uploads/flight_plans/2024-01-15_morning.json",
    "file_size": 245760,
    "file_format": "JSON",
    "upload_timestamp": "2024-01-15T08:00:00Z",
    "uploaded_by": "operator-001",
    "flight_count": 127
  }
}
```

**Example 2: Large Flight Plan Uploaded**
```json
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T12:00:00Z",
  "source": "airspace-plan-manager",
  "severity": "info",
  "sector_id": "airspace-sector-2",
  "summary": "Large flight plan PLAN-20240115-XYZ789 uploaded",
  "correlation_id": "bb0e8400-e29b-41d4-a716-446655440001",
  "details": {
    "plan_id": "PLAN-20240115-XYZ789",
    "plan_name": "Afternoon Traffic Plan",
    "file_path": "/uploads/flight_plans/2024-01-15_afternoon.json",
    "file_size": 1048576,
    "file_format": "JSON",
    "upload_timestamp": "2024-01-15T12:00:00Z",
    "uploaded_by": "system-auto",
    "flight_count": 342
  }
}
```

### airspace.flight.parsed

Flight parsed events indicating individual flights have been extracted from flight plans.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "flight_id": "string",
    "plan_id": "string",
    "callsign": "string (optional)",
    "aircraft_type": "string (optional)",
    "origin": "string (optional)",
    "destination": "string (optional)",
    "departure_time": "string (ISO 8601, optional)",
    "arrival_time": "string (ISO 8601, optional)",
    "route": "array (optional)",
    "altitude": "number (optional)",
    "speed": "number (optional)",
    "parse_status": "string (optional)",
    "parse_errors": "array (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Flight Parsed Successfully**
```json
{
  "event_id": "cc0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T08:05:00Z",
  "source": "airspace-flight-parser",
  "severity": "info",
  "sector_id": "airspace-sector-1",
  "summary": "Flight FLT-ABC123 parsed successfully from plan PLAN-20240115-ABC123",
  "correlation_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "flight_id": "FLT-ABC123",
    "plan_id": "PLAN-20240115-ABC123",
    "callsign": "UAL123",
    "aircraft_type": "Boeing 737-800",
    "origin": "KJFK",
    "destination": "KLAX",
    "departure_time": "2024-01-15T08:00:00Z",
    "arrival_time": "2024-01-15T11:30:00Z",
    "route": ["KJFK", "WAYPOINT1", "WAYPOINT2", "WAYPOINT3", "KLAX"],
    "altitude": 35000.0,
    "speed": 450.0,
    "parse_status": "success",
    "parse_errors": []
  }
}
```

**Example 2: Flight Parsed with Warnings**
```json
{
  "event_id": "cc0e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T08:10:00Z",
  "source": "airspace-flight-parser",
  "severity": "warning",
  "sector_id": "airspace-sector-1",
  "summary": "Flight FLT-DEF456 parsed with warnings",
  "correlation_id": "dd0e8400-e29b-41d4-a716-446655440001",
  "details": {
    "flight_id": "FLT-DEF456",
    "plan_id": "PLAN-20240115-ABC123",
    "callsign": "AAL456",
    "aircraft_type": "Airbus A320",
    "origin": "KORD",
    "destination": "KDFW",
    "departure_time": "2024-01-15T09:00:00Z",
    "arrival_time": "2024-01-15T11:15:00Z",
    "route": ["KORD", "WAYPOINT1", "KDFW"],
    "altitude": 33000.0,
    "speed": null,
    "parse_status": "partial",
    "parse_errors": ["Missing speed information, using default"]
  }
}
```

### airspace.trajectory.sampled

Trajectory sampled events indicating flight trajectories have been sampled for analysis.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "flight_id": "string",
    "sample_count": "number (optional)",
    "sample_interval": "number (optional)",
    "trajectory_points": "array (optional)",
    "start_time": "string (ISO 8601, optional)",
    "end_time": "string (ISO 8601, optional)",
    "total_duration": "number (optional)",
    "sampling_method": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Trajectory Sampled**
```json
{
  "event_id": "ee0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T08:15:00Z",
  "source": "airspace-trajectory-sampler",
  "severity": "info",
  "sector_id": "airspace-sector-1",
  "summary": "Trajectory sampled for flight FLT-ABC123",
  "correlation_id": "ff0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "flight_id": "FLT-ABC123",
    "sample_count": 360,
    "sample_interval": 60.0,
    "trajectory_points": [
      {
        "latitude": 40.6413,
        "longitude": -73.7781,
        "altitude": 0.0,
        "timestamp": "2024-01-15T08:00:00Z"
      },
      {
        "latitude": 40.7500,
        "longitude": -74.0000,
        "altitude": 10000.0,
        "timestamp": "2024-01-15T08:10:00Z"
      }
    ],
    "start_time": "2024-01-15T08:00:00Z",
    "end_time": "2024-01-15T11:30:00Z",
    "total_duration": 12600.0,
    "sampling_method": "time-based"
  }
}
```

**Example 2: High-Resolution Trajectory Sampled**
```json
{
  "event_id": "ee0e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T08:20:00Z",
  "source": "airspace-trajectory-sampler",
  "severity": "info",
  "sector_id": "airspace-sector-2",
  "summary": "High-resolution trajectory sampled for flight FLT-GHI789",
  "correlation_id": "ff0e8400-e29b-41d4-a716-446655440001",
  "details": {
    "flight_id": "FLT-GHI789",
    "sample_count": 2160,
    "sample_interval": 10.0,
    "trajectory_points": [
      {
        "latitude": 41.8781,
        "longitude": -87.6298,
        "altitude": 0.0,
        "timestamp": "2024-01-15T09:00:00Z"
      }
    ],
    "start_time": "2024-01-15T09:00:00Z",
    "end_time": "2024-01-15T11:15:00Z",
    "total_duration": 8100.0,
    "sampling_method": "high-resolution"
  }
}
```

### airspace.conflict.detected

Conflict detected events indicating potential conflicts between flights have been identified.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "conflict_id": "string",
    "conflict_type": "string (optional)",
    "severity_level": "string (optional)",
    "flight_ids": "array (optional)",
    "conflict_location": "object (optional)",
    "conflict_time": "string (ISO 8601, optional)",
    "minimum_separation": "number (optional)",
    "required_separation": "number (optional)",
    "conflict_duration": "number (optional)",
    "detection_method": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: High Severity Conflict**
```json
{
  "event_id": "110e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T09:00:00Z",
  "source": "airspace-conflict-detector",
  "severity": "warning",
  "sector_id": "airspace-sector-2",
  "summary": "Conflict CONF-ABC123 detected between flights FLT-ABC123 and FLT-XYZ789",
  "correlation_id": "220e8400-e29b-41d4-a716-446655440000",
  "details": {
    "conflict_id": "CONF-ABC123",
    "conflict_type": "separation",
    "severity_level": "high",
    "flight_ids": ["FLT-ABC123", "FLT-XYZ789"],
    "conflict_location": {
      "latitude": 39.8283,
      "longitude": -98.5795,
      "altitude": 35000.0
    },
    "conflict_time": "2024-01-15T09:15:00Z",
    "minimum_separation": 2.5,
    "required_separation": 5.0,
    "conflict_duration": 120.0,
    "detection_method": "trajectory-intersection"
  }
}
```

**Example 2: Critical Conflict**
```json
{
  "event_id": "110e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T09:30:00Z",
  "source": "airspace-conflict-detector",
  "severity": "critical",
  "sector_id": "airspace-sector-3",
  "summary": "Critical conflict CONF-DEF456 detected - immediate action required",
  "correlation_id": "220e8400-e29b-41d4-a716-446655440001",
  "details": {
    "conflict_id": "CONF-DEF456",
    "conflict_type": "separation",
    "severity_level": "critical",
    "flight_ids": ["FLT-DEF456", "FLT-GHI789"],
    "conflict_location": {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 32000.0
    },
    "conflict_time": "2024-01-15T09:45:00Z",
    "minimum_separation": 0.8,
    "required_separation": 5.0,
    "conflict_duration": 180.0,
    "detection_method": "real-time-monitoring"
  }
}
```

### airspace.hotspot.detected

Hotspot detected events indicating congestion or high-density areas in airspace.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "hotspot_id": "string",
    "hotspot_type": "string (optional)",
    "location": "object (optional)",
    "affected_flights": "array (optional)",
    "severity": "string (optional)",
    "start_time": "string (ISO 8601, optional)",
    "end_time": "string (ISO 8601, optional)",
    "density": "number (optional)",
    "capacity_limit": "number (optional)",
    "current_count": "number (optional)",
    "description": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Congestion Hotspot**
```json
{
  "event_id": "330e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:00:00Z",
  "source": "airspace-hotspot-detector",
  "severity": "warning",
  "sector_id": "airspace-sector-3",
  "summary": "Congestion hotspot HOTSPOT-ABC123 detected in sector 3",
  "correlation_id": "440e8400-e29b-41d4-a716-446655440000",
  "details": {
    "hotspot_id": "HOTSPOT-ABC123",
    "hotspot_type": "congestion",
    "location": {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 30000.0,
      "radius_nm": 25.0
    },
    "affected_flights": ["FLT-ABC123", "FLT-DEF456", "FLT-GHI789", "FLT-JKL012", "FLT-MNO345"],
    "severity": "high",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T12:00:00Z",
    "density": 0.85,
    "capacity_limit": 50,
    "current_count": 43,
    "description": "High traffic congestion in approach corridor"
  }
}
```

**Example 2: Weather Hotspot**
```json
{
  "event_id": "330e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T10:30:00Z",
  "source": "airspace-hotspot-detector",
  "severity": "warning",
  "sector_id": "airspace-sector-1",
  "summary": "Weather hotspot HOTSPOT-DEF456 detected",
  "correlation_id": "440e8400-e29b-41d4-a716-446655440001",
  "details": {
    "hotspot_id": "HOTSPOT-DEF456",
    "hotspot_type": "weather",
    "location": {
      "latitude": 39.9526,
      "longitude": -75.1652,
      "altitude": 25000.0,
      "radius_nm": 30.0
    },
    "affected_flights": ["FLT-PQR678", "FLT-STU901"],
    "severity": "medium",
    "start_time": "2024-01-15T10:30:00Z",
    "end_time": "2024-01-15T14:00:00Z",
    "density": 0.45,
    "capacity_limit": 20,
    "current_count": 9,
    "description": "Thunderstorm activity affecting approach routes"
  }
}
```

### airspace.solution.proposed

Solution proposed events indicating resolution strategies for conflicts or hotspots.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "solution_id": "string",
    "solution_type": "string (optional)",
    "problem_id": "string (optional)",
    "affected_flights": "array (optional)",
    "proposed_actions": "array (optional)",
    "estimated_impact": "object (optional)",
    "confidence_score": "number (optional)",
    "generated_by": "string (optional)",
    "requires_approval": "boolean (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Reroute Solution**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T09:20:00Z",
  "source": "airspace-solution-generator",
  "severity": "info",
  "sector_id": "airspace-sector-2",
  "summary": "Solution SOL-ABC123 proposed for conflict resolution",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440000",
  "details": {
    "solution_id": "SOL-ABC123",
    "solution_type": "reroute",
    "problem_id": "CONF-ABC123",
    "affected_flights": ["FLT-ABC123", "FLT-XYZ789"],
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
    "requires_approval": true
  }
}
```

**Example 2: Speed Adjustment Solution**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T10:15:00Z",
  "source": "airspace-solution-generator",
  "severity": "info",
  "sector_id": "airspace-sector-3",
  "summary": "Solution SOL-DEF456 proposed for hotspot mitigation",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440001",
  "details": {
    "solution_id": "SOL-DEF456",
    "solution_type": "speed_adjustment",
    "problem_id": "HOTSPOT-ABC123",
    "affected_flights": ["FLT-DEF456", "FLT-GHI789", "FLT-JKL012"],
    "proposed_actions": [
      {
        "flight_id": "FLT-DEF456",
        "action": "speed_reduction",
        "speed_change_knots": -20,
        "delay_minutes": 3
      },
      {
        "flight_id": "FLT-GHI789",
        "action": "speed_increase",
        "speed_change_knots": 15,
        "delay_minutes": -2
      }
    ],
    "estimated_impact": {
      "total_delay_minutes": 1,
      "fuel_impact_percent": 1.2,
      "affected_passengers": 420
    },
    "confidence_score": 0.92,
    "generated_by": "airspace-ai-coordinator",
    "requires_approval": false
  }
}
```

### airspace.report.ready

Report ready events indicating airspace analysis reports have been generated.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "report_id": "string",
    "report_type": "string (optional)",
    "report_period_start": "string (ISO 8601, optional)",
    "report_period_end": "string (ISO 8601, optional)",
    "report_url": "string (optional)",
    "report_format": "string (optional)",
    "total_flights": "number (optional)",
    "conflicts_detected": "number (optional)",
    "hotspots_detected": "number (optional)",
    "solutions_proposed": "number (optional)",
    "generated_by": "string (optional)",
    "report_size": "number (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Daily Summary Report**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T23:59:00Z",
  "source": "airspace-report-generator",
  "severity": "info",
  "sector_id": "airspace-all-sectors",
  "summary": "Airspace report RPT-20240115-ABC123 ready for review",
  "correlation_id": "880e8400-e29b-41d4-a716-446655440000",
  "details": {
    "report_id": "RPT-20240115-ABC123",
    "report_type": "summary",
    "report_period_start": "2024-01-15T00:00:00Z",
    "report_period_end": "2024-01-15T23:59:59Z",
    "report_url": "/reports/RPT-20240115-ABC123.pdf",
    "report_format": "PDF",
    "total_flights": 1247,
    "conflicts_detected": 23,
    "hotspots_detected": 8,
    "solutions_proposed": 31,
    "generated_by": "airspace-analytics-engine",
    "report_size": 2048576
  }
}
```

**Example 2: Conflict Analysis Report**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T12:00:00Z",
  "source": "airspace-report-generator",
  "severity": "info",
  "sector_id": "airspace-sector-2",
  "summary": "Conflict analysis report RPT-CONF-20240115 ready",
  "correlation_id": "880e8400-e29b-41d4-a716-446655440001",
  "details": {
    "report_id": "RPT-CONF-20240115",
    "report_type": "conflict",
    "report_period_start": "2024-01-15T08:00:00Z",
    "report_period_end": "2024-01-15T12:00:00Z",
    "report_url": "/reports/RPT-CONF-20240115.json",
    "report_format": "JSON",
    "total_flights": 342,
    "conflicts_detected": 12,
    "hotspots_detected": 3,
    "solutions_proposed": 15,
    "generated_by": "airspace-analytics-engine",
    "report_size": 524288
  }
}
```

### geo.incident

Geospatial incident events for marking incidents on maps with geographic coordinates.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "id": "string",
    "geometry": {
      "type": "Point|Circle|Polygon",
      "coordinates": "varies by type",
      "radius_meters": "number (for Circle only)"
    },
    "style": {
      "color": "string (default: 'red')",
      "opacity": "number (0.35-0.7, default: 0.5)",
      "outline": "boolean (default: true)"
    },
    "incident_type": "string (optional)",
    "description": "string (optional)",
    "status": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Geometry Types:**

- **Point**: `{"type": "Point", "coordinates": [longitude, latitude]}`
- **Circle**: `{"type": "Circle", "coordinates": [longitude, latitude], "radius_meters": number}`
- **Polygon**: `{"type": "Polygon", "coordinates": [[lon, lat], [lon, lat], ...]}` (must be closed)

**Example 1: Point Incident**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:30:00Z",
  "source": "geo-monitoring-system",
  "severity": "critical",
  "sector_id": "ottawa-region",
  "summary": "Critical incident detected at coordinates",
  "correlation_id": "990e8400-e29b-41d4-a716-446655440000",
  "details": {
    "id": "INCIDENT-ABC12345",
    "geometry": {
      "type": "Point",
      "coordinates": [-75.6972, 45.4215]
    },
    "style": {
      "color": "red",
      "opacity": 0.7,
      "outline": true
    },
    "incident_type": "power_outage",
    "description": "Major power outage affecting downtown area",
    "status": "active"
  }
}
```

**Example 2: Circle Incident**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:35:00Z",
  "source": "geo-monitoring-system",
  "severity": "warning",
  "sector_id": "ottawa-region",
  "summary": "Incident zone detected",
  "correlation_id": "990e8400-e29b-41d4-a716-446655440001",
  "details": {
    "id": "INCIDENT-DEF67890",
    "geometry": {
      "type": "Circle",
      "coordinates": [-75.6972, 45.4215],
      "radius_meters": 5000
    },
    "style": {
      "color": "orange",
      "opacity": 0.5,
      "outline": true
    },
    "incident_type": "traffic_disruption",
    "description": "Major traffic disruption in downtown core",
    "status": "active"
  }
}
```

### geo.risk_area

Geospatial risk area events for marking risk zones on maps with geographic boundaries.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|error|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "id": "string",
    "geometry": {
      "type": "Point|Circle|Polygon",
      "coordinates": "varies by type",
      "radius_meters": "number (for Circle only)"
    },
    "style": {
      "color": "string (default: 'red')",
      "opacity": "number (0.35-0.7, default: 0.5)",
      "outline": "boolean (default: true)"
    },
    "risk_level": "string (optional)",
    "risk_type": "string (optional)",
    "description": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Polygon Risk Area**
```json
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:00:00Z",
  "source": "risk-assessment-system",
  "severity": "warning",
  "sector_id": "ottawa-region",
  "summary": "High-risk area identified",
  "correlation_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "id": "RISK-XYZ12345",
    "geometry": {
      "type": "Polygon",
      "coordinates": [
        [-75.7072, 45.4115],
        [-75.6872, 45.4115],
        [-75.6872, 45.4315],
        [-75.7072, 45.4315],
        [-75.7072, 45.4115]
      ]
    },
    "style": {
      "color": "#FF0000",
      "opacity": 0.6,
      "outline": true
    },
    "risk_level": "high",
    "risk_type": "flood_zone",
    "description": "High-risk flood zone requiring monitoring"
  }
}
```

**Example 2: Circle Risk Area**
```json
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T15:05:00Z",
  "source": "risk-assessment-system",
  "severity": "info",
  "sector_id": "ottawa-region",
  "summary": "Medium-risk area identified",
  "correlation_id": "bb0e8400-e29b-41d4-a716-446655440001",
  "details": {
    "id": "RISK-UVW67890",
    "geometry": {
      "type": "Circle",
      "coordinates": [-75.6972, 45.4215],
      "radius_meters": 10000
    },
    "style": {
      "color": "yellow",
      "opacity": 0.4,
      "outline": true
    },
    "risk_level": "medium",
    "risk_type": "weather_alert",
    "description": "Weather alert zone - moderate risk"
  }
}
```

## Event Validation

All events should be validated against this schema before publishing. The Python schema implementation in `agents/shared/schema.py` provides validation utilities.

## Event Routing

Events are published to topics matching the event type:
- `power.failure` → `chronos.events.power.failure`
- `recovery.plan` → `chronos.events.recovery.plan`
- `operator.status` → `chronos.events.operator.status`
- `audit.decision` → `chronos.events.audit.decision`
- `airspace.plan.uploaded` → `chronos.events.airspace.plan.uploaded`
- `airspace.flight.parsed` → `chronos.events.airspace.flight.parsed`
- `airspace.trajectory.sampled` → `chronos.events.airspace.trajectory.sampled`
- `airspace.conflict.detected` → `chronos.events.airspace.conflict.detected`
- `airspace.hotspot.detected` → `chronos.events.airspace.hotspot.detected`
- `airspace.solution.proposed` → `chronos.events.airspace.solution.proposed`
- `airspace.report.ready` → `chronos.events.airspace.report.ready`
- `geo.incident` → `chronos.events.geo.incident`
- `geo.risk_area` → `chronos.events.geo.risk_area`

## Best Practices

1. Always generate a unique UUID for `event_id`
2. Use ISO 8601 format for all timestamps (UTC recommended)
3. Set appropriate severity levels based on impact
4. Include relevant context in `details` object
5. Link related events using `related_events` array when applicable
6. Validate events before publishing to ensure schema compliance

