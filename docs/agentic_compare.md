# Agentic Compare: Airspace Solution Generation Modes

This document explains the differences between RULES, LLM, and AGENTIC modes for generating airspace conflict and hotspot solutions in Project Chronos.

## Overview

The system supports three autonomy modes for airspace solution generation:

1. **RULES**: Deterministic heuristics-based solutions
2. **LLM**: AI-generated solutions using Gemini
3. **AGENTIC**: Multi-agent task-based solutions

## Configuration

Set the mode using the `AUTONOMY_MODE` environment variable:

```bash
# PowerShell
$env:AUTONOMY_MODE="RULES"
$env:AUTONOMY_MODE="LLM"
$env:AUTONOMY_MODE="AGENTIC"

# Bash
export AUTONOMY_MODE=RULES
export AUTONOMY_MODE=LLM
export AUTONOMY_MODE=AGENTIC
```

Or add to `.env` file:
```
AUTONOMY_MODE=RULES
```

## Mode Comparison

### RULES Mode

**Approach**: Deterministic heuristics using predefined rules.

**Solution Types**:
- **Altitude change**: Increase altitude by 2000 feet (max FL410)
- **Speed change**: Reduce speed by 15 knots (min 300 knots)
- **Departure shift**: Delay departure by 5 minutes for time-based conflicts

**Characteristics**:
- ✅ Fast (no API calls)
- ✅ Deterministic (same input = same output)
- ✅ No external dependencies
- ✅ Always available (fallback mode)
- ⚠️ Limited flexibility
- ⚠️ May not optimize for complex scenarios

**Example Output**:

```json
{
  "solution_id": "SOL-RULES-ABC12345",
  "solution_type": "multi_action",
  "problem_id": "CONF-XYZ789",
  "affected_flights": ["FLT-ABC123", "FLT-DEF456"],
  "proposed_actions": [
    {
      "flight_id": "FLT-ABC123",
      "action": "altitude_change",
      "new_altitude": 37000,
      "delay_minutes": 0,
      "reasoning": "Increase altitude to create vertical separation"
    },
    {
      "flight_id": "FLT-DEF456",
      "action": "speed_change",
      "speed_change_knots": -15,
      "new_speed": 435,
      "delay_minutes": 0,
      "reasoning": "Reduce speed to create temporal separation"
    },
    {
      "flight_id": "FLT-ABC123",
      "action": "departure_shift",
      "delay_minutes": 5,
      "reasoning": "Shift departure time to avoid conflict window"
    }
  ],
  "estimated_impact": {
    "total_delay_minutes": 5,
    "fuel_impact_percent": 1.5,
    "affected_passengers": 300
  },
  "confidence_score": 0.85,
  "generated_by": "rules-engine",
  "requires_approval": true
}
```

**When to Use**:
- Production systems requiring guaranteed availability
- Simple conflict scenarios
- When API keys are unavailable
- Fallback mode for reliability

---

### LLM Mode

**Approach**: AI-generated solutions using Google Gemini API.

**Process**:
1. Build summary of conflicts/hotspots and trajectories
2. Send to Gemini with strict JSON format request
3. Parse JSON response
4. Fallback to RULES if parsing fails or API unavailable

**Characteristics**:
- ✅ More flexible and adaptive
- ✅ Can handle complex scenarios
- ✅ Learns from patterns
- ⚠️ Requires API key (`GEMINI_API_KEY`)
- ⚠️ Slower (API call latency)
- ⚠️ May produce unexpected outputs
- ⚠️ Falls back to RULES on failure

**Example Output**:

```json
{
  "solution_id": "SOL-LLM-DEF67890",
  "solution_type": "reroute",
  "problem_id": "CONF-XYZ789",
  "affected_flights": ["FLT-ABC123", "FLT-DEF456"],
  "proposed_actions": [
    {
      "flight_id": "FLT-ABC123",
      "action": "reroute",
      "new_waypoints": ["WAYPOINT1", "WAYPOINT2", "WAYPOINT3"],
      "delay_minutes": 3,
      "reasoning": "Reroute to avoid conflict zone while minimizing delay"
    },
    {
      "flight_id": "FLT-DEF456",
      "action": "altitude_change",
      "new_altitude": 38000,
      "delay_minutes": 0,
      "reasoning": "Increase altitude to maintain separation during reroute"
    }
  ],
  "estimated_impact": {
    "total_delay_minutes": 3,
    "fuel_impact_percent": 2.1,
    "affected_passengers": 300
  },
  "confidence_score": 0.78,
  "generated_by": "llm-gemini",
  "requires_approval": true
}
```

**When to Use**:
- Complex multi-flight scenarios
- When optimization is important
- Research and development
- When API access is available

---

### AGENTIC Mode

**Approach**: Multi-agent task decomposition and coordination.

**Process**:
1. Coordinator splits problem into tasks:
   - `task.airspace.deconflict` (for conflicts)
   - `task.airspace.hotspot_mitigation` (for hotspots)
   - `task.airspace.validation_fix` (for violations)
2. Specialized agents subscribe to tasks:
   - `airspace_deconflict_agent` → proposes altitude changes
   - `airspace_hotspot_agent` → proposes speed adjustments
3. Agents publish partial solutions
4. Coordinator merges partial solutions into complete solution
5. Coordinator publishes final `airspace.solution.proposed` event

**Characteristics**:
- ✅ Distributed problem solving
- ✅ Specialized agents for different problem types
- ✅ Can scale horizontally (multiple agents)
- ✅ Modular and extensible
- ⚠️ More complex architecture
- ⚠️ Requires multiple agents running
- ⚠️ Slightly slower (task coordination overhead)

**Example Flow**:

1. **Conflict Detected**:
   ```
   airspace.conflict.detected → coordinator_agent
   ```

2. **Task Published**:
   ```json
   {
     "topic": "chronos.tasks.airspace.deconflict",
     "details": {
       "task_id": "TASK-DECONF-ABC123",
       "task_type": "deconflict",
       "conflict": { ... }
     }
   }
   ```

3. **Partial Solution from Deconflict Agent**:
   ```json
   {
     "topic": "chronos.tasks.airspace.partial_solution",
     "details": {
       "task_id": "TASK-DECONF-ABC123",
       "solution_type": "altitude_change",
       "affected_flights": ["FLT-ABC123"],
       "proposed_actions": [
         {
           "flight_id": "FLT-ABC123",
           "action": "altitude_change",
           "new_altitude": 37000,
           "reasoning": "Increase altitude to create vertical separation"
         }
       ],
       "agent_name": "airspace-deconflict-agent"
     }
   }
   ```

4. **Merged Solution from Coordinator**:
   ```json
   {
     "topic": "chronos.events.airspace.solution.proposed",
     "details": {
       "solution_id": "SOL-MERGED-XYZ789",
       "solution_type": "multi_action",
       "problem_id": "CONF-XYZ789",
       "affected_flights": ["FLT-ABC123", "FLT-DEF456"],
       "proposed_actions": [
         {
           "flight_id": "FLT-ABC123",
           "action": "altitude_change",
           "new_altitude": 37000
         },
         {
           "flight_id": "FLT-DEF456",
           "action": "speed_change",
           "speed_change_knots": -15
         }
       ],
       "generated_by": "coordinator-agent-merged",
       "partial_solutions": ["airspace-deconflict-agent", "airspace-hotspot-agent"]
     }
   }
   ```

**When to Use**:
- Complex multi-problem scenarios
- When you need specialized expertise per problem type
- Research into multi-agent systems
- When horizontal scaling is needed

---

## Key Differences Summary

| Feature | RULES | LLM | AGENTIC |
|---------|-------|-----|---------|
| **Speed** | Fastest | Medium | Slowest |
| **Deterministic** | Yes | No | Partially |
| **External Dependencies** | None | Gemini API | Multiple agents |
| **Complexity** | Low | Medium | High |
| **Flexibility** | Low | High | Very High |
| **Reliability** | Highest | Medium | Medium |
| **Scalability** | Single process | Single process | Multi-process |
| **Fallback** | N/A | RULES | RULES |

## Example Scenarios

### Scenario 1: Simple Conflict (2 flights)

**RULES Output**:
- Altitude change for flight 1 (+2000 ft)
- Speed change for flight 2 (-15 knots)
- **Total delay**: 0 minutes
- **Confidence**: 0.85

**LLM Output**:
- Reroute for flight 1
- Altitude change for flight 2
- **Total delay**: 3 minutes
- **Confidence**: 0.78

**AGENTIC Output**:
- Altitude change from deconflict agent
- Speed adjustment from hotspot agent (if applicable)
- **Total delay**: 0-2 minutes
- **Confidence**: 0.80-0.90 (averaged)

### Scenario 2: Complex Hotspot (5+ flights)

**RULES Output**:
- Speed reduction for first 3 flights (-20 knots each)
- **Total delay**: 2 minutes per flight
- **Confidence**: 0.80

**LLM Output**:
- Mixed strategy: some reroutes, some speed changes, some delays
- Optimized for minimal total impact
- **Total delay**: Variable (1-5 minutes)
- **Confidence**: 0.75

**AGENTIC Output**:
- Multiple partial solutions from different agents
- Merged into comprehensive solution
- **Total delay**: Optimized across agents
- **Confidence**: 0.82 (averaged from agents)

## Running the System

### RULES Mode (Default)
```bash
# No additional setup needed
python agents/trajectory_insight_agent.py
python agents/coordinator_agent.py
```

### LLM Mode
```bash
# Set API key
$env:GEMINI_API_KEY="your_key_here"
$env:AUTONOMY_MODE="LLM"

python agents/trajectory_insight_agent.py
python agents/coordinator_agent.py
```

### AGENTIC Mode
```bash
# Set mode
$env:AUTONOMY_MODE="AGENTIC"

# Terminal 1: Coordinator
python agents/coordinator_agent.py

# Terminal 2: Deconflict Agent
python agents/airspace_deconflict_agent.py

# Terminal 3: Hotspot Agent
python agents/airspace_hotspot_agent.py

# Terminal 4: Trajectory Insight Agent
python agents/trajectory_insight_agent.py
```

## Best Practices

1. **Start with RULES**: Always test with RULES mode first to ensure basic functionality
2. **Use LLM for complex scenarios**: When RULES heuristics are insufficient
3. **Use AGENTIC for research**: When exploring multi-agent coordination
4. **Always have fallback**: System automatically falls back to RULES on failure
5. **Monitor confidence scores**: Lower confidence may indicate edge cases

## Troubleshooting

### LLM Mode Issues

**Problem**: Solutions not generated, falling back to RULES
- **Check**: `GEMINI_API_KEY` is set correctly
- **Check**: API key has proper permissions
- **Check**: Network connectivity to Gemini API
- **Solution**: Verify API key, check logs for error messages

### AGENTIC Mode Issues

**Problem**: No solutions generated
- **Check**: All agents are running (coordinator, deconflict, hotspot)
- **Check**: Agents are subscribed to correct topics
- **Check**: Message broker is running
- **Solution**: Ensure all agents are started and connected

**Problem**: Partial solutions not merging
- **Check**: Coordinator is subscribed to `chronos.tasks.airspace.partial_solution`
- **Check**: Partial solutions have matching `task_id`
- **Solution**: Verify topic subscriptions and correlation IDs

## Conclusion

Each mode has its strengths:

- **RULES**: Production-ready, reliable, fast
- **LLM**: Flexible, adaptive, handles complexity
- **AGENTIC**: Research-oriented, scalable, modular

Choose based on your requirements: reliability (RULES), flexibility (LLM), or research (AGENTIC).
