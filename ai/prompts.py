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

