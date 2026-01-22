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
- `moderate`: Moderate severity condition (renamed from `error` for clarity)
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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
  "severity": "info|warning|moderate|critical",
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

### transit.gtfsrt.fetch.started

GTFS-RT feed fetch started events indicating the beginning of a real-time transit data fetch.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "feed_url": "string",
    "feed_type": "string (optional)",
    "fetch_id": "string (optional)",
    "expected_entities": "number (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Vehicle Positions Feed**
```json
{
  "event_id": "cc0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:00:00Z",
  "source": "transit-gtfsrt-fetcher",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "GTFS-RT feed fetch started",
  "correlation_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "feed_url": "https://api.octranspo.com/gtfsrt/vehicle_positions",
    "feed_type": "vehicle_positions",
    "fetch_id": "FETCH-ABC12345",
    "expected_entities": 450
  }
}
```

**Example 2: Trip Updates Feed**
```json
{
  "event_id": "cc0e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:05:00Z",
  "source": "transit-gtfsrt-fetcher",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "GTFS-RT trip updates feed fetch started",
  "correlation_id": "dd0e8400-e29b-41d4-a716-446655440001",
  "details": {
    "feed_url": "https://api.octranspo.com/gtfsrt/trip_updates",
    "feed_type": "trip_updates",
    "fetch_id": "FETCH-DEF67890",
    "expected_entities": 320
  }
}
```

### transit.vehicle.position

Vehicle position events indicating real-time location updates for transit vehicles.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "vehicle_id": "string",
    "trip_id": "string (optional)",
    "route_id": "string (optional)",
    "latitude": "number (optional)",
    "longitude": "number (optional)",
    "bearing": "number (optional)",
    "speed": "number (optional)",
    "occupancy_status": "string (optional)",
    "current_stop_sequence": "number (optional)",
    "current_status": "string (optional)",
    "timestamp": "string (ISO 8601, optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: In Transit Vehicle**
```json
{
  "event_id": "ee0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:15:00Z",
  "source": "transit-vehicle-tracker",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Vehicle VEH-ABC123 position update",
  "correlation_id": "ff0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "vehicle_id": "VEH-ABC123",
    "trip_id": "TRIP-12345",
    "route_id": "ROUTE-95",
    "latitude": 45.4215,
    "longitude": -75.6972,
    "bearing": 180.0,
    "speed": 12.5,
    "occupancy_status": "MANY_SEATS_AVAILABLE",
    "current_stop_sequence": 15,
    "current_status": "IN_TRANSIT_TO",
    "timestamp": "2024-01-15T14:15:00Z"
  }
}
```

**Example 2: Stopped Vehicle**
```json
{
  "event_id": "ee0e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:20:00Z",
  "source": "transit-vehicle-tracker",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Vehicle VEH-DEF456 position update",
  "correlation_id": "ff0e8400-e29b-41d4-a716-446655440001",
  "details": {
    "vehicle_id": "VEH-DEF456",
    "trip_id": "TRIP-67890",
    "route_id": "ROUTE-97",
    "latitude": 45.4115,
    "longitude": -75.7072,
    "bearing": 0.0,
    "speed": 0.0,
    "occupancy_status": "FULL",
    "current_stop_sequence": 8,
    "current_status": "STOPPED_AT",
    "timestamp": "2024-01-15T14:20:00Z"
  }
}
```

### transit.trip.update

Trip update events indicating schedule changes and delays for transit trips.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "trip_id": "string",
    "route_id": "string (optional)",
    "vehicle_id": "string (optional)",
    "stop_time_updates": "array (optional)",
    "delay": "number (optional)",
    "timestamp": "string (ISO 8601, optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Delayed Trip**
```json
{
  "event_id": "110e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:25:00Z",
  "source": "transit-trip-monitor",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Trip TRIP-12345 update received - 2 minute delay",
  "correlation_id": "220e8400-e29b-41d4-a716-446655440000",
  "details": {
    "trip_id": "TRIP-12345",
    "route_id": "ROUTE-95",
    "vehicle_id": "VEH-ABC123",
    "stop_time_updates": [
      {
        "stop_sequence": 15,
        "stop_id": "STOP-12345",
        "arrival_time": "2024-01-15T14:30:00Z",
        "departure_time": "2024-01-15T14:32:00Z"
      }
    ],
    "delay": 120,
    "timestamp": "2024-01-15T14:25:00Z"
  }
}
```

**Example 2: On-Time Trip**
```json
{
  "event_id": "110e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:30:00Z",
  "source": "transit-trip-monitor",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Trip TRIP-67890 update received - on time",
  "correlation_id": "220e8400-e29b-41d4-a716-446655440001",
  "details": {
    "trip_id": "TRIP-67890",
    "route_id": "ROUTE-97",
    "vehicle_id": "VEH-DEF456",
    "stop_time_updates": [
      {
        "stop_sequence": 8,
        "stop_id": "STOP-12346",
        "arrival_time": "2024-01-15T14:35:00Z",
        "departure_time": "2024-01-15T14:36:00Z"
      }
    ],
    "delay": 0,
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

### transit.disruption.risk

Disruption risk events indicating predicted or detected service disruptions.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "risk_id": "string",
    "risk_type": "string (optional)",
    "severity_level": "string (optional)",
    "affected_routes": "array (optional)",
    "affected_stops": "array (optional)",
    "location": "object (optional)",
    "predicted_start_time": "string (ISO 8601, optional)",
    "predicted_end_time": "string (ISO 8601, optional)",
    "confidence_score": "number (optional)",
    "description": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: High Risk Delay**
```json
{
  "event_id": "330e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:40:00Z",
  "source": "transit-risk-analyzer",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Disruption risk RISK-ABC123 detected - high probability of delays",
  "correlation_id": "440e8400-e29b-41d4-a716-446655440000",
  "details": {
    "risk_id": "RISK-ABC123",
    "risk_type": "delay",
    "severity_level": "high",
    "affected_routes": ["ROUTE-95", "ROUTE-97"],
    "affected_stops": ["STOP-12345", "STOP-12346"],
    "location": {
      "latitude": 45.4215,
      "longitude": -75.6972
    },
    "predicted_start_time": "2024-01-15T14:00:00Z",
    "predicted_end_time": "2024-01-15T16:00:00Z",
    "confidence_score": 0.75,
    "description": "High probability of delays due to traffic congestion"
  }
}
```

**Example 2: Service Interruption Risk**
```json
{
  "event_id": "330e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:45:00Z",
  "source": "transit-risk-analyzer",
  "severity": "critical",
  "sector_id": "ottawa-transit",
  "summary": "Disruption risk RISK-DEF456 detected - potential service interruption",
  "correlation_id": "440e8400-e29b-41d4-a716-446655440001",
  "details": {
    "risk_id": "RISK-DEF456",
    "risk_type": "service_interruption",
    "severity_level": "critical",
    "affected_routes": ["ROUTE-95"],
    "affected_stops": ["STOP-12345"],
    "location": {
      "latitude": 45.4115,
      "longitude": -75.7072
    },
    "predicted_start_time": "2024-01-15T15:00:00Z",
    "predicted_end_time": "2024-01-15T17:00:00Z",
    "confidence_score": 0.85,
    "description": "Potential service interruption due to infrastructure issue"
  }
}
```

### transit.hotspot

Transit hotspot events indicating congestion or high-density areas in the transit network.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "hotspot_id": "string",
    "hotspot_type": "string (optional)",
    "location": "object (optional)",
    "affected_routes": "array (optional)",
    "affected_vehicles": "array (optional)",
    "severity": "string (optional)",
    "start_time": "string (ISO 8601, optional)",
    "end_time": "string (ISO 8601, optional)",
    "vehicle_count": "number (optional)",
    "average_delay": "number (optional)",
    "description": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Congestion Hotspot**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:00:00Z",
  "source": "transit-hotspot-detector",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Transit hotspot HOTSPOT-ABC123 detected in downtown core",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440000",
  "details": {
    "hotspot_id": "HOTSPOT-ABC123",
    "hotspot_type": "congestion",
    "location": {
      "latitude": 45.4215,
      "longitude": -75.6972,
      "radius_meters": 500
    },
    "affected_routes": ["ROUTE-95", "ROUTE-97"],
    "affected_vehicles": ["VEH-ABC123", "VEH-DEF456", "VEH-GHI789"],
    "severity": "high",
    "start_time": "2024-01-15T14:00:00Z",
    "end_time": "2024-01-15T15:30:00Z",
    "vehicle_count": 12,
    "average_delay": 8.5,
    "description": "High congestion hotspot in downtown core"
  }
}
```

**Example 2: Delay Hotspot**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T15:10:00Z",
  "source": "transit-hotspot-detector",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Transit hotspot HOTSPOT-DEF456 detected - significant delays",
  "correlation_id": "660e8400-e29b-41d4-a716-446655440001",
  "details": {
    "hotspot_id": "HOTSPOT-DEF456",
    "hotspot_type": "delay",
    "location": {
      "latitude": 45.4115,
      "longitude": -75.7072,
      "radius_meters": 300
    },
    "affected_routes": ["ROUTE-95"],
    "affected_vehicles": ["VEH-ABC123", "VEH-DEF456"],
    "severity": "medium",
    "start_time": "2024-01-15T15:00:00Z",
    "end_time": "2024-01-15T16:00:00Z",
    "vehicle_count": 5,
    "average_delay": 5.2,
    "description": "Delay hotspot affecting route 95"
  }
}
```

### transit.report.ready

Transit report ready events indicating analysis reports have been generated.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "report_id": "string",
    "report_type": "string (optional)",
    "report_period_start": "string (ISO 8601, optional)",
    "report_period_end": "string (ISO 8601, optional)",
    "report_url": "string (optional)",
    "report_format": "string (optional)",
    "total_vehicles": "number (optional)",
    "disruptions_detected": "number (optional)",
    "hotspots_detected": "number (optional)",
    "average_delay_minutes": "number (optional)",
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
  "source": "transit-report-generator",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Transit report RPT-20240115-ABC123 ready for review",
  "correlation_id": "880e8400-e29b-41d4-a716-446655440000",
  "details": {
    "report_id": "RPT-20240115-ABC123",
    "report_type": "summary",
    "report_period_start": "2024-01-15T00:00:00Z",
    "report_period_end": "2024-01-15T23:59:59Z",
    "report_url": "/reports/transit/RPT-20240115-ABC123.pdf",
    "report_format": "PDF",
    "total_vehicles": 450,
    "disruptions_detected": 12,
    "hotspots_detected": 5,
    "average_delay_minutes": 3.2,
    "generated_by": "transit-analytics-engine",
    "report_size": 1536000
  }
}
```

**Example 2: Disruption Analysis Report**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T12:00:00Z",
  "source": "transit-report-generator",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Transit disruption report RPT-DISRUPT-20240115 ready",
  "correlation_id": "880e8400-e29b-41d4-a716-446655440001",
  "details": {
    "report_id": "RPT-DISRUPT-20240115",
    "report_type": "disruption",
    "report_period_start": "2024-01-15T08:00:00Z",
    "report_period_end": "2024-01-15T12:00:00Z",
    "report_url": "/reports/transit/RPT-DISRUPT-20240115.json",
    "report_format": "JSON",
    "total_vehicles": 342,
    "disruptions_detected": 8,
    "hotspots_detected": 3,
    "average_delay_minutes": 5.8,
    "generated_by": "transit-analytics-engine",
    "report_size": 524288
  }
}
```

### fix.proposed

Fix proposed events indicating a new fix has been proposed to address an incident, hotspot, or plan issue.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "fix_id": "string (stable identifier)",
    "correlation_id": "string (incident_id|hotspot_id|plan_id)",
    "source": "string (gemini|rules|cerebras)",
    "title": "string",
    "summary": "string",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM|TRAFFIC_ADVISORY_SIM|AIRSPACE_MITIGATION_SIM|POWER_RECOVERY_SIM",
        "target": {
          "route_id": "string (optional)",
          "sector_id": "string (optional)",
          "area_bbox": "object (optional)",
          "stop_id": "string (optional)",
          "flight_id": "string (optional)"
        },
        "params": "object (action-specific parameters)",
        "verification": {
          "metric_name": "string",
          "threshold": "number",
          "window_seconds": "number"
        }
      }
    ],
    "risk_level": "string (low|med|high)",
    "expected_impact": {
      "delay_reduction": "number (optional, minutes)",
      "risk_score_delta": "number (optional)",
      "area_affected": "object (optional)"
    },
    "created_at": "string (ISO 8601)",
    "proposed_by": "string (agent_id or operator_id)",
    "requires_human_approval": "boolean (default: true)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example 1: Transit Reroute Fix**
```json
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:00:00Z",
  "source": "fix-coordinator",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 proposed for transit disruption",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
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
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true
  }
}
```

**Example 2: Airspace Mitigation Fix**
```json
{
  "event_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:05:00Z",
  "source": "fix-coordinator",
  "severity": "warning",
  "sector_id": "airspace-sector-2",
  "summary": "Fix FIX-20240115-DEF456 proposed for conflict resolution",
  "correlation_id": "CONF-ABC123",
  "details": {
    "fix_id": "FIX-20240115-DEF456",
    "correlation_id": "CONF-ABC123",
    "source": "rules",
    "title": "Altitude adjustment for conflict mitigation",
    "summary": "Increase altitude for FLT-ABC123 by 2000 feet",
    "actions": [
      {
        "type": "AIRSPACE_MITIGATION_SIM",
        "target": {
          "flight_id": "FLT-ABC123",
          "sector_id": "airspace-sector-2"
        },
        "params": {
          "altitude_change": 2000,
          "altitude_unit": "feet"
        },
        "verification": {
          "metric_name": "risk_score_delta",
          "threshold": -0.1,
          "window_seconds": 60
        }
      }
    ],
    "risk_level": "low",
    "expected_impact": {
      "delay_reduction": 0.0,
      "risk_score_delta": -0.3,
      "area_affected": {
        "type": "point",
        "coordinates": {
          "latitude": 39.8283,
          "longitude": -98.5795,
          "altitude": 35000
        }
      }
    },
    "created_at": "2024-01-15T14:05:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": false
  }
}
```

### fix.review_required

Fix review required events indicating a fix needs human review before approval.

**Payload Structure:** Same as `fix.proposed` with additional `review_notes` field.

**Example:**
```json
{
  "event_id": "cc0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:10:00Z",
  "source": "fix-reviewer",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 requires human review",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "review_notes": "High-risk change requiring safety review"
  }
}
```

### fix.approved

Fix approved events indicating a fix has been approved for deployment.

**Payload Structure:** Same as `fix.proposed` with additional `approved_by` and `review_notes` fields.

**Example:**
```json
{
  "event_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:15:00Z",
  "source": "fix-reviewer",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 approved for deployment",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "review_notes": "Approved after safety review",
    "approved_by": "OP-001"
  }
}
```

### fix.rejected

Fix rejected events indicating a fix has been rejected and will not be deployed.

**Payload Structure:** Same as `fix.approved` with rejection information.

**Example:**
```json
{
  "event_id": "ee0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:20:00Z",
  "source": "fix-reviewer",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-XYZ789 rejected",
  "correlation_id": "HOTSPOT-DEF456",
  "details": {
    "fix_id": "FIX-20240115-XYZ789",
    "correlation_id": "HOTSPOT-DEF456",
    "source": "gemini",
    "title": "Alternative reroute proposal",
    "summary": "Proposed reroute rejected due to safety concerns",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
        "target": {
          "route_id": "ROUTE-97"
        },
        "params": {
          "alternative_route": ["STOP-12360", "STOP-12365"]
        },
        "verification": {
          "metric_name": "delay_reduction",
          "threshold": 10.0,
          "window_seconds": 300
        }
      }
    ],
    "risk_level": "high",
    "expected_impact": {
      "delay_reduction": 20.0,
      "risk_score_delta": 0.1
    },
    "created_at": "2024-01-15T14:10:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "review_notes": "Rejected: Alternative route passes through construction zone",
    "approved_by": "OP-001"
  }
}
```

### fix.deploy_requested

Fix deploy requested events indicating deployment has been requested for an approved fix.

**Payload Structure:** Same as `fix.approved`.

**Example:**
```json
{
  "event_id": "ff0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:25:00Z",
  "source": "fix-deployer",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 deployment requested",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "approved_by": "OP-001"
  }
}
```

### fix.deploy_started

Fix deploy started events indicating deployment has begun.

**Payload Structure:** Same as `fix.deploy_requested` with `deployed_at` timestamp.

**Example:**
```json
{
  "event_id": "110e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:26:00Z",
  "source": "fix-deployer",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 deployment started",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "approved_by": "OP-001",
    "deployed_at": "2024-01-15T14:26:00Z"
  }
}
```

### fix.deploy_succeeded

Fix deploy succeeded events indicating successful deployment.

**Payload Structure:** Same as `fix.deploy_started`.

**Example:**
```json
{
  "event_id": "220e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:27:00Z",
  "source": "fix-deployer",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 deployed successfully",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "approved_by": "OP-001",
    "deployed_at": "2024-01-15T14:27:00Z"
  }
}
```

### fix.deploy_failed

Fix deploy failed events indicating deployment failure.

**Payload Structure:** Same as `fix.deploy_started` with failure information.

**Example:**
```json
{
  "event_id": "330e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:28:00Z",
  "source": "fix-deployer",
  "severity": "moderate",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-GHI789 deployment failed",
  "correlation_id": "HOTSPOT-GHI789",
  "details": {
    "fix_id": "FIX-20240115-GHI789",
    "correlation_id": "HOTSPOT-GHI789",
    "source": "rules",
    "title": "Traffic advisory for Route 97",
    "summary": "Deployment failed due to system error",
    "actions": [
      {
        "type": "TRAFFIC_ADVISORY_SIM",
        "target": {
          "route_id": "ROUTE-97"
        },
        "params": {
          "advisory_message": "Expect delays"
        },
        "verification": {
          "metric_name": "risk_score_delta",
          "threshold": -0.1,
          "window_seconds": 180
        }
      }
    ],
    "risk_level": "low",
    "expected_impact": {
      "delay_reduction": 5.0,
      "risk_score_delta": -0.1
    },
    "created_at": "2024-01-15T14:20:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": false,
    "review_notes": "Deployment failed: System timeout"
  }
}
```

### fix.verified

Fix verified events indicating a deployed fix has been verified as successful.

**Payload Structure:** Same as `fix.deploy_succeeded` with `verified_at` timestamp.

**Example:**
```json
{
  "event_id": "440e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:35:00Z",
  "source": "fix-verifier",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 verified as successful",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "approved_by": "OP-001",
    "deployed_at": "2024-01-15T14:27:00Z",
    "verified_at": "2024-01-15T14:35:00Z"
  }
}
```

### fix.rollback_requested

Fix rollback requested events indicating a rollback has been requested for a deployed fix.

**Payload Structure:** Same as `fix.verified` with `rollback_reason`.

**Example:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:40:00Z",
  "source": "fix-coordinator",
  "severity": "warning",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 rollback requested",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "approved_by": "OP-001",
    "deployed_at": "2024-01-15T14:27:00Z",
    "verified_at": "2024-01-15T14:35:00Z",
    "rollback_reason": "Fix causing unexpected delays on alternative route"
  }
}
```

### fix.rollback_succeeded

Fix rollback succeeded events indicating successful rollback of a fix.

**Payload Structure:** Same as `fix.rollback_requested`.

**Example:**
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:45:00Z",
  "source": "fix-deployer",
  "severity": "info",
  "sector_id": "ottawa-transit",
  "summary": "Fix FIX-20240115-ABC123 rolled back successfully",
  "correlation_id": "HOTSPOT-ABC123",
  "details": {
    "fix_id": "FIX-20240115-ABC123",
    "correlation_id": "HOTSPOT-ABC123",
    "source": "gemini",
    "title": "Reroute Route 95 to bypass congestion",
    "summary": "Proposed reroute to reduce delays by 15 minutes",
    "actions": [
      {
        "type": "TRANSIT_REROUTE_SIM",
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
    "risk_level": "med",
    "expected_impact": {
      "delay_reduction": 15.0,
      "risk_score_delta": -0.2
    },
    "created_at": "2024-01-15T14:00:00Z",
    "proposed_by": "agent-fix-generator",
    "requires_human_approval": true,
    "approved_by": "OP-001",
    "deployed_at": "2024-01-15T14:27:00Z",
    "verified_at": "2024-01-15T14:35:00Z",
    "rollback_reason": "Fix causing unexpected delays on alternative route"
  }
}
```

## Defense Domain Events

**⚠️ IMPORTANT DISCLAIMER:** Defense features are non-kinetic and informational only.

### defense.threat.detected

Threat detected events indicating potential security or safety threats.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "threat_id": "string",
    "threat_type": "airspace|cyber_physical|environmental|civil",
    "confidence_score": "number (0.0-1.0)",
    "severity": "low|med|high|critical",
    "affected_area": "object (GeoJSON geometry, optional)",
    "sources": ["array of strings"],
    "summary": "string",
    "detected_at": "string (ISO 8601)",
    "disclaimer": "Defense features are non-kinetic and informational only."
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:00:00Z",
  "source": "defense-threat-detector",
  "severity": "high",
  "sector_id": "ottawa-airspace",
  "summary": "Threat THREAT-20240115-ABC123 detected: Unusual airspace activity",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "threat_id": "THREAT-20240115-ABC123",
    "threat_type": "airspace",
    "confidence_score": 0.75,
    "severity": "high",
    "affected_area": {
      "type": "Polygon",
      "coordinates": [[[-75.7, 45.4], [-75.6, 45.4], [-75.6, 45.5], [-75.7, 45.5], [-75.7, 45.4]]]
    },
    "sources": ["airspace", "satellite"],
    "summary": "Unusual airspace activity detected in Ottawa region",
    "detected_at": "2024-01-15T15:00:00Z",
    "disclaimer": "Defense features are non-kinetic and informational only."
  }
}
```

### defense.threat.assessed

Threat assessed events indicating that a threat has been evaluated.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "threat_id": "string",
    "assessment_score": "number (0.0-1.0, optional)",
    "risk_level": "string (optional)",
    "assessment_notes": "string (optional)",
    "assessed_by": "string (optional)",
    "assessed_at": "string (ISO 8601)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:05:00Z",
  "source": "defense-threat-assessor",
  "severity": "moderate",
  "sector_id": "ottawa-airspace",
  "summary": "Threat THREAT-20240115-ABC123 assessed as high risk",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "threat_id": "THREAT-20240115-ABC123",
    "assessment_score": 0.85,
    "risk_level": "high",
    "assessment_notes": "Threat confirmed with high confidence, requires immediate attention",
    "assessed_by": "defense-analyst-001",
    "assessed_at": "2024-01-15T15:05:00Z"
  }
}
```

### defense.threat.escalated

Threat escalated events indicating that a threat's severity has been increased.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "threat_id": "string",
    "previous_severity": "string",
    "new_severity": "string",
    "escalation_reason": "string (optional)",
    "escalated_by": "string (optional)",
    "escalated_at": "string (ISO 8601)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "990e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:10:00Z",
  "source": "defense-threat-monitor",
  "severity": "critical",
  "sector_id": "ottawa-airspace",
  "summary": "Threat THREAT-20240115-ABC123 escalated from high to critical",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "threat_id": "THREAT-20240115-ABC123",
    "previous_severity": "high",
    "new_severity": "critical",
    "escalation_reason": "Threat activity increased significantly",
    "escalated_by": "defense-monitor-001",
    "escalated_at": "2024-01-15T15:10:00Z"
  }
}
```

### defense.posture.changed

Defense posture changed events indicating changes to the overall defense posture.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "posture_id": "string (optional)",
    "previous_posture": "string (optional)",
    "new_posture": "string",
    "change_reason": "string (optional)",
    "changed_by": "string (optional)",
    "changed_at": "string (ISO 8601)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "aa0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:15:00Z",
  "source": "defense-posture-manager",
  "severity": "warning",
  "sector_id": "ottawa-region",
  "summary": "Defense posture changed to heightened alert",
  "correlation_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "details": {
    "posture_id": "POSTURE-001",
    "previous_posture": "normal",
    "new_posture": "heightened_alert",
    "change_reason": "Multiple threats detected in region",
    "changed_by": "defense-coordinator-001",
    "changed_at": "2024-01-15T15:15:00Z"
  }
}
```

### defense.action.proposed

Defense action proposed events indicating that a defense action has been proposed.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "action_id": "string",
    "threat_id": "string (optional)",
    "action_type": "string",
    "action_description": "string",
    "proposed_by": "string (optional)",
    "proposed_at": "string (ISO 8601)",
    "requires_approval": "boolean"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:20:00Z",
  "source": "defense-action-planner",
  "severity": "moderate",
  "sector_id": "ottawa-airspace",
  "summary": "Defense action ACTION-20240115-XYZ789 proposed for threat THREAT-20240115-ABC123",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "action_id": "ACTION-20240115-XYZ789",
    "threat_id": "THREAT-20240115-ABC123",
    "action_type": "informational_alert",
    "action_description": "Issue public safety advisory regarding airspace activity",
    "proposed_by": "defense-planner-001",
    "proposed_at": "2024-01-15T15:20:00Z",
    "requires_approval": true
  }
}
```

### defense.action.approved

Defense action approved events indicating that a defense action has been approved.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "action_id": "string",
    "threat_id": "string (optional)",
    "approved_by": "string (optional)",
    "approved_at": "string (ISO 8601)",
    "approval_notes": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "cc0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:25:00Z",
  "source": "defense-action-approver",
  "severity": "info",
  "sector_id": "ottawa-airspace",
  "summary": "Defense action ACTION-20240115-XYZ789 approved",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "action_id": "ACTION-20240115-XYZ789",
    "threat_id": "THREAT-20240115-ABC123",
    "approved_by": "OP-001",
    "approved_at": "2024-01-15T15:25:00Z",
    "approval_notes": "Action approved for deployment"
  }
}
```

### defense.action.deployed

Defense action deployed events indicating that a defense action has been deployed.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "action_id": "string",
    "threat_id": "string (optional)",
    "deployment_status": "success|failed|partial",
    "deployed_by": "string (optional)",
    "deployed_at": "string (ISO 8601)",
    "deployment_notes": "string (optional)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T15:30:00Z",
  "source": "defense-action-deployer",
  "severity": "info",
  "sector_id": "ottawa-airspace",
  "summary": "Defense action ACTION-20240115-XYZ789 deployed successfully",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "action_id": "ACTION-20240115-XYZ789",
    "threat_id": "THREAT-20240115-ABC123",
    "deployment_status": "success",
    "deployed_by": "defense-deployer-001",
    "deployed_at": "2024-01-15T15:30:00Z",
    "deployment_notes": "Public safety advisory issued"
  }
}
```

### defense.threat.resolved

Threat resolved events indicating that a threat has been resolved.

**Payload Structure:**
```json
{
  "event_id": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "source": "string",
  "severity": "info|warning|moderate|critical",
  "sector_id": "string",
  "summary": "string",
  "details": {
    "threat_id": "string",
    "resolution_status": "resolved|mitigated|false_positive",
    "resolution_notes": "string (optional)",
    "resolved_by": "string (optional)",
    "resolved_at": "string (ISO 8601)"
  },
  "correlation_id": "string (UUID, optional)"
}
```

**Example:**
```json
{
  "event_id": "ee0e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T16:00:00Z",
  "source": "defense-threat-resolver",
  "severity": "info",
  "sector_id": "ottawa-airspace",
  "summary": "Threat THREAT-20240115-ABC123 resolved",
  "correlation_id": "THREAT-20240115-ABC123",
  "details": {
    "threat_id": "THREAT-20240115-ABC123",
    "resolution_status": "resolved",
    "resolution_notes": "Threat activity ceased, no further action required",
    "resolved_by": "defense-monitor-001",
    "resolved_at": "2024-01-15T16:00:00Z"
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
- `transit.gtfsrt.fetch.started` → `chronos.events.transit.gtfsrt.fetch.started`
- `transit.vehicle.position` → `chronos.events.transit.vehicle.position`
- `transit.trip.update` → `chronos.events.transit.trip.update`
- `transit.disruption.risk` → `chronos.events.transit.disruption.risk`
- `transit.hotspot` → `chronos.events.transit.hotspot`
- `transit.report.ready` → `chronos.events.transit.report.ready`
- `fix.proposed` → `chronos.events.fix.proposed`
- `fix.review_required` → `chronos.events.fix.review_required`
- `fix.approved` → `chronos.events.fix.approved`
- `fix.rejected` → `chronos.events.fix.rejected`
- `fix.deploy_requested` → `chronos.events.fix.deploy_requested`
- `fix.deploy_started` → `chronos.events.fix.deploy_started`
- `fix.deploy_succeeded` → `chronos.events.fix.deploy_succeeded`
- `fix.deploy_failed` → `chronos.events.fix.deploy_failed`
- `fix.verified` → `chronos.events.fix.verified`
- `fix.rollback_requested` → `chronos.events.fix.rollback_requested`
- `fix.rollback_succeeded` → `chronos.events.fix.rollback_succeeded`
- `defense.threat.detected` → `chronos.events.defense.threat.detected`
- `defense.threat.assessed` → `chronos.events.defense.threat.assessed`
- `defense.threat.escalated` → `chronos.events.defense.threat.escalated`
- `defense.posture.changed` → `chronos.events.defense.posture.changed`
- `defense.action.proposed` → `chronos.events.defense.action.proposed`
- `defense.action.approved` → `chronos.events.defense.action.approved`
- `defense.action.deployed` → `chronos.events.defense.action.deployed`
- `defense.threat.resolved` → `chronos.events.defense.threat.resolved`

## Best Practices

1. Always generate a unique UUID for `event_id`
2. Use ISO 8601 format for all timestamps (UTC recommended)
3. Set appropriate severity levels based on impact
4. Include relevant context in `details` object
5. Link related events using `related_events` array when applicable
6. Validate events before publishing to ensure schema compliance

