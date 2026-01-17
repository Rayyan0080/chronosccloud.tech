# Observability with Sentry

Project Chronos uses [Sentry](https://sentry.io) for error tracking, performance monitoring, and observability across all agent services.

## Overview

Sentry provides:
- **Error Tracking**: Automatic exception capture with full stack traces
- **Performance Monitoring**: Track execution times and identify bottlenecks
- **Event Logging**: Capture important events (startup, received events, published events)
- **Contextual Information**: Service tags, autonomy mode, and custom metadata

## Configuration

### Setup

1. **Get Sentry DSN**:
   - Sign up at https://sentry.io
   - Create a project
   - Copy your DSN (Data Source Name)

2. **Set Environment Variable**:
   ```bash
   export SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"
   ```

   Or in PowerShell:
   ```powershell
   $env:SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"
   ```

3. **Optional Configuration**:
   ```bash
   # Set environment (development, staging, production)
   export SENTRY_ENVIRONMENT="development"
   
   # Set release version
   export SENTRY_RELEASE="1.0.0"
   
   # Set trace sample rate (0.0 to 1.0)
   export SENTRY_TRACES_SAMPLE_RATE="0.1"
   ```

## What Gets Captured

### 1. Service Startup

Every agent captures startup events:
- Service name
- Configuration details
- Initialization status

**Example:**
```python
init_sentry("crisis_generator")
capture_startup("crisis_generator", {"service_type": "event_generator"})
```

### 2. Received Events

When agents receive events from the message broker:
- Event topic
- Event ID
- Event metadata (sector_id, severity, etc.)

**Example:**
```python
capture_received_event(
    topic,
    event_id,
    {"sector_id": sector_id, "severity": severity}
)
```

### 3. Published Events

When agents publish events:
- Event topic
- Event ID
- Event payload summary

**Example:**
```python
capture_published_event(
    POWER_FAILURE_TOPIC,
    event_id,
    {"sector_id": sector_id, "voltage": voltage}
)
```

### 4. Exceptions

All exceptions are automatically captured with:
- Full stack trace
- Exception type and message
- Service context
- Custom metadata

**Example:**
```python
try:
    # ... code ...
except Exception as e:
    capture_exception(e, {"service": "crisis_generator", "error_type": "fatal"})
```

## Tags

All Sentry events include tags for filtering and grouping:

### service_name
- `crisis_generator`
- `coordinator_agent`
- `stress_monitor`
- `autonomy_router`
- `state_logger`
- `solana_audit_logger`
- `qnx_event_source`
- `flight_plan_ingestor`
- `trajectory_insight_agent`
- `airspace_deconflict_agent`
- `airspace_hotspot_agent`

### autonomy_mode
- `NORMAL`: Standard operation mode
- `HIGH`: High autonomy mode
- Framework name (e.g., `AGENTIC_MESH`, `RULES_ENGINE`)
- Airspace solution mode: `RULES`, `LLM`, `AGENTIC`

### event_type
- `startup`: Service startup
- `received_event`: Event received from broker
- `published_event`: Event published to broker
- `exception`: Exception occurred

### plan_id
- Flight plan identifier (for airspace domain agents)
- Set dynamically when processing plans

## Integration

### Shared Module

All agents use the shared Sentry module (`agents/shared/sentry.py`):

```python
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_published_event,
    capture_exception,
)
```

### Initialization

Each agent initializes Sentry in its `main()` function:

```python
async def main():
    # Initialize Sentry
    init_sentry("service_name", autonomy_mode="NORMAL")
    capture_startup("service_name", {"service_type": "..."})
    
    # ... rest of service code ...
```

### Event Capture

Agents capture events at key points:

```python
# When receiving events
capture_received_event(topic, event_id, {"sector_id": sector_id})

# When publishing events
capture_published_event(topic, event_id, {"voltage": voltage})

# When exceptions occur
try:
    # ... code ...
except Exception as e:
    capture_exception(e, {"context": "..."})
```

## Agent Coverage

All agents have Sentry integration:

| Agent | Startup | Received | Published | Exceptions |
|-------|---------|----------|-----------|------------|
| `crisis_generator` | ✅ | N/A | ✅ | ✅ |
| `coordinator_agent` | ✅ | ✅ | ✅ | ✅ |
| `stress_monitor` | ✅ | N/A | ✅ | ✅ |
| `autonomy_router` | ✅ | ✅ | ✅ | ✅ |
| `state_logger` | ✅ | ✅ | N/A | ✅ |
| `solana_audit_logger` | ✅ | ✅ | N/A | ✅ |
| `qnx_event_source` | ✅ | N/A | ✅ | ✅ |
| `flight_plan_ingestor` | ✅ | N/A | ✅ | ✅ |
| `trajectory_insight_agent` | ✅ | ✅ | ✅ | ✅ |
| `airspace_deconflict_agent` | ✅ | ✅ | ✅ | ✅ |
| `airspace_hotspot_agent` | ✅ | ✅ | ✅ | ✅ |

## Viewing Data in Sentry

### Issues

View all errors and exceptions:
- Filter by service: `service_name:crisis_generator`
- Filter by autonomy mode: `autonomy_mode:HIGH`
- Filter by event type: `event_type:exception`

### Performance

Track service performance:
- Average execution time per service
- Slowest operations
- Performance trends

### Events

View all captured events:
- Startup events
- Received/published events
- Custom events

### Dashboards

Create custom dashboards:
- Service health overview
- Error rates by service
- Event volume trends
- Autonomy mode distribution

## Best Practices

1. **Always Initialize**: Every agent should call `init_sentry()` at startup
2. **Capture Context**: Include relevant metadata in event captures
3. **Handle Failures Gracefully**: Sentry failures should not break agent functionality
4. **Use Tags**: Leverage tags for filtering and grouping
5. **Monitor Performance**: Use performance monitoring to identify bottlenecks

## Troubleshooting

### Sentry Not Capturing Events

1. **Check DSN**:
   ```bash
   echo $SENTRY_DSN
   ```

2. **Check Installation**:
   ```bash
   pip install sentry-sdk
   ```

3. **Check Logs**:
   - Look for "SENTRY INITIALIZED" in agent logs
   - Check for "Sentry library not available" warnings

### Too Many Events

Adjust sample rates:
```bash
export SENTRY_TRACES_SAMPLE_RATE="0.1"  # 10% of events
```

### Missing Context

Ensure agents include relevant metadata:
```python
capture_exception(e, {
    "service": "service_name",
    "event_id": event_id,
    "sector_id": sector_id,
})
```

## Privacy and Security

- **No Sensitive Data**: Do not include passwords, API keys, or PII in Sentry events
- **Data Retention**: Configure retention policies in Sentry dashboard
- **Access Control**: Use Sentry's team and project permissions

## Example Queries

### Find All Errors in Crisis Generator
```
service_name:crisis_generator event_type:exception
```

### Find All Events in High Autonomy Mode
```
autonomy_mode:HIGH
```

### Find Slow Operations
```
Performance > 1000ms
```

### Find Recent Startup Events
```
event_type:startup
```

## Airspace Domain Observability

The airspace domain agents have enhanced Sentry instrumentation:

### Flight Plan Ingestor

**Tags:**
- `service_name`: `flight_plan_ingestor`
- `plan_id`: Flight plan identifier (set dynamically)

**Breadcrumbs:**
- `topic.publish`: When publishing `airspace.plan.uploaded` events
- `topic.publish`: When publishing `airspace.flight.parsed` events

**Exception Handling:**
- Flight lists are automatically redacted to avoid logging entire flight data
- Only summary information (flight count, plan_id) is included in exception context

**Example:**
```python
# Set plan_id tag
set_tag("plan_id", plan_id)

# Add breadcrumb when publishing
add_breadcrumb(
    message=f"Publishing airspace.plan.uploaded for plan {plan_id}",
    category="topic.publish",
    data={"topic": AIRSPACE_PLAN_UPLOADED_TOPIC, "plan_id": plan_id}
)

# Exception with redacted data
capture_exception(e, {
    "plan_id": plan_id,
    "flight_count": len(flights),
    # Full flight list is NOT included
})
```

### Trajectory Insight Agent

**Tags:**
- `service_name`: `trajectory_insight_agent`
- `autonomy_mode`: `RULES`, `LLM`, or `AGENTIC`
- `plan_id`: Flight plan identifier (set dynamically when processing)

**Breadcrumbs:**
- `topic.receive`: When receiving `airspace.flight.parsed` events
- `topic.publish`: When publishing conflict, hotspot, solution, and report events
- `plan.processing`: When starting to process a plan

**Exception Handling:**
- Flight lists and full payloads are automatically redacted
- Only metadata (plan_id, flight_count, event_id) is included

**Example:**
```python
# Set tags
set_tag("plan_id", plan_id)
set_tag("autonomy_mode", AUTONOMY_MODE)

# Add breadcrumb when receiving
add_breadcrumb(
    message=f"Received airspace.flight.parsed: {flight_id}",
    category="topic.receive",
    data={"topic": topic, "flight_id": flight_id, "plan_id": plan_id}
)

# Add breadcrumb when publishing
add_breadcrumb(
    message=f"Publishing airspace.conflict.detected: {conflict_id}",
    category="topic.publish",
    data={"topic": AIRSPACE_CONFLICT_DETECTED_TOPIC, "conflict_id": conflict_id}
)

# Exception with redacted data
capture_exception(e, {
    "plan_id": plan_id,
    "flight_count": len(flights),
    # Full flight list is NOT included
})
```

### Airspace Task Agents

**Tags:**
- `service_name`: `airspace_deconflict_agent` or `airspace_hotspot_agent`
- `autonomy_mode`: `AGENTIC` (when running)

**Breadcrumbs:**
- `topic.receive`: When receiving task events
- `topic.publish`: When publishing partial solutions

## Payload Redaction

To protect sensitive data and avoid logging large payloads, the Sentry integration automatically redacts:

- **Large Lists**: Lists with more than 10 items are replaced with `[REDACTED: N items]`
- **Flight Lists**: Full flight data is never included in exception context
- **Event Payloads**: Only metadata (event_id, plan_id, flight_id) is included

This ensures:
- ✅ Sensitive flight data is not logged
- ✅ Exception context remains useful for debugging
- ✅ Sentry events stay within size limits
- ✅ Performance is not impacted by large payloads

## Integration with Other Tools

Sentry can integrate with:
- **Slack**: Get notifications for errors
- **PagerDuty**: Alert on critical issues
- **GitHub**: Link errors to code
- **Jira**: Create tickets for errors

Configure integrations in the Sentry dashboard under Settings → Integrations.

