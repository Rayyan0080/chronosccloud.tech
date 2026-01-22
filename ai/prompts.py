"""
Prompt templates for AI services in Project Chronos.
"""

RECOVERY_PLAN_PROMPT = """You are a crisis management AI assistant for Project Chronos, a digital twin crisis system.

Analyze the following power failure event and generate a recovery plan. Return ONLY valid JSON, no other text.

Power Failure Event:
{event_json}

Generate a recovery plan with the following structure:
{{
  "plan_id": "RP-YYYY-NNN" (format: RP-year-sequential number),
  "plan_name": "Descriptive name for the recovery plan",
  "status": "draft",
  "steps": [
    "Step 1 description",
    "Step 2 description",
    "Step 3 description",
    ...
  ],
  "estimated_completion": "ISO 8601 timestamp (estimate completion time based on severity and sector)",
  "assigned_agents": ["agent-001", "agent-002", ...] (suggest 1-3 agent IDs)
}}

Guidelines:
- Create 3-6 recovery steps based on the event severity and details
- Steps should be actionable and sequential
- Estimated completion should be realistic (1-4 hours for most cases, longer for critical failures)
- Use agent IDs in format "agent-XXX" where XXX is a 3-digit number
- Plan name should be descriptive (e.g., "Sector 1 Power Restoration Plan")
- Consider voltage, load, phase, and backup status when creating steps

Return ONLY the JSON object, no markdown, no code blocks, no explanations."""


FIX_PROPOSAL_PROMPT = """You are a crisis management AI assistant for Project Chronos. Generate a fix proposal to address an incident, hotspot, or plan issue.

Analyze the following event and generate a fix proposal. Return ONLY valid JSON, no other text, no prose, no explanations.

Event:
{event_json}

Generate a fix proposal with the following EXACT structure:
{{
  "title": "string (descriptive title for the fix)",
  "summary": "string (brief summary of what the fix does)",
  "actions": [
    {{
      "type": "TRANSIT_REROUTE_SIM|TRAFFIC_ADVISORY_SIM|AIRSPACE_MITIGATION_SIM|POWER_RECOVERY_SIM",
      "target": {{
        "route_id": "string (optional, for transit actions)",
        "sector_id": "string (optional, for power/airspace actions)",
        "area_bbox": {{"min_lat": number, "max_lat": number, "min_lon": number, "max_lon": number}} (optional),
        "stop_id": "string (optional, for transit actions)",
        "flight_id": "string (optional, for airspace actions)"
      }},
      "params": {{"key": "value"}} (action-specific parameters),
      "verification": {{
        "metric_name": "string (e.g., 'delay_reduction', 'risk_score_delta')",
        "threshold": number,
        "window_seconds": number
      }}
    }}
  ],
  "risk_level": "low|med|high",
  "expected_impact": {{
    "delay_reduction": number (optional, in minutes),
    "risk_score_delta": number (optional, expected change in risk score),
    "area_affected": {{"type": "bbox|point", "coordinates": {{}}}} (optional)
  }},
  "verification": {{
    "metric_name": "string",
    "threshold": number,
    "window_seconds": number
  }}
}}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON, no markdown, no code blocks, no explanations
- Must include ALL required fields: title, summary, actions[], risk_level, expected_impact
- actions[] must contain at least one action
- Each action must have: type, target, params, verification
- Each action.verification must have: metric_name, threshold, window_seconds
- risk_level must be one of: "low", "med", "high"
- expected_impact must include at least one metric (delay_reduction or risk_score_delta)
- verification at top level is optional (each action must have its own verification)

Return ONLY the JSON object, nothing else."""


DEFENSE_ASSESSMENT_PROMPT = """You are a defense assessment AI assistant for Project Chronos. Analyze a detected threat and provide a comprehensive assessment.

Analyze the following threat information and generate an assessment. Return ONLY valid JSON, no other text, no prose, no explanations.

Threat Information:
{threat_summary}

Sources Involved: {sources}
Confidence Score: {confidence_score}
Current City Posture: {current_posture}

Generate a defense assessment with the following EXACT structure:
{{
  "threat_type": "airspace|cyber_physical|environmental|civil",
  "likely_cause": "string (brief description of likely cause)",
  "recommended_posture": "string (e.g., 'normal', 'heightened_alert', 'elevated', 'critical')",
  "protective_actions": [
    "string (action 1 description)",
    "string (action 2 description)",
    ...
  ],
  "escalation_needed": true|false
}}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON, no markdown, no code blocks, no explanations
- threat_type must be one of: "airspace", "cyber_physical", "environmental", "civil"
- recommended_posture must be a valid posture level
- protective_actions must be a non-empty array of strings
- escalation_needed must be a boolean (true or false)
- likely_cause must be a descriptive string

Return ONLY the JSON object, nothing else."""