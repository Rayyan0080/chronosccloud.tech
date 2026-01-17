"""
Gemini AI client for generating recovery plans.

Handles API calls to Google Gemini and provides fallback plans when API is unavailable.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Import prompt template
from ai.prompts import RECOVERY_PLAN_PROMPT


def _generate_fallback_plan(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a fallback recovery plan when Gemini API is unavailable.

    Args:
        event: Power failure event dictionary

    Returns:
        Recovery plan dictionary
    """
    sector_id = event.get("sector_id", "unknown")
    severity = event.get("severity", "error")
    details = event.get("details", {})
    voltage = details.get("voltage", 0)
    phase = details.get("phase", "unknown")

    # Generate plan ID
    year = datetime.utcnow().year
    plan_num = str(uuid4())[:3].upper()
    plan_id = f"RP-{year}-{plan_num}"

    # Determine plan name
    plan_name = f"{sector_id.replace('-', ' ').title()} Power Restoration Plan"

    # Generate steps based on severity
    if severity == "critical":
        steps = [
            "Immediate safety assessment and personnel evacuation if needed",
            "Isolate affected power circuits to prevent cascading failures",
            "Activate backup power systems and verify functionality",
            "Assess damage to electrical infrastructure",
            "Coordinate with maintenance team for repairs",
            "Restore primary power and verify system integrity",
        ]
        hours = 3.0
    elif severity == "error":
        steps = [
            "Assess affected circuits and isolate if necessary",
            "Check backup power system status",
            "Identify root cause of power failure",
            "Execute repair procedures",
            "Verify power restoration and system stability",
        ]
        hours = 2.0
    else:  # warning
        steps = [
            "Monitor power levels and system status",
            "Investigate cause of power fluctuation",
            "Apply corrective measures",
            "Verify system returns to normal operation",
        ]
        hours = 1.5

    # Adjust based on voltage (lower voltage = more severe)
    if voltage < 10:
        hours += 1.0
        steps.insert(1, "Emergency power routing to critical systems")

    # Calculate estimated completion
    estimated_completion = (datetime.utcnow() + timedelta(hours=hours)).isoformat() + "Z"

    # Assign agents (1-3 based on severity)
    num_agents = 3 if severity == "critical" else 2 if severity == "error" else 1
    assigned_agents = [f"agent-{i:03d}" for i in range(1, num_agents + 1)]

    return {
        "plan_id": plan_id,
        "plan_name": plan_name,
        "status": "draft",
        "steps": steps,
        "estimated_completion": estimated_completion,
        "assigned_agents": assigned_agents,
    }


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from text that may contain markdown, code blocks, or extra text.

    Args:
        text: Text that may contain JSON

    Returns:
        Parsed JSON dictionary or None if extraction fails
    """
    if not text:
        return None

    # Remove markdown code blocks
    text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # Try to find JSON object boundaries
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_pattern, text, re.DOTALL)

    if matches:
        # Use the longest match (likely the full JSON)
        text = max(matches, key=len)

    # Try parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to fix common issues
        # Remove trailing commas
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        # Try again
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
            return None


def get_recovery_plan(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a recovery plan for a power failure event using Gemini AI.

    If GEMINI_API_KEY is not set or API call fails, returns a fallback plan.

    Args:
        event: Power failure event dictionary with structure:
            {
                "event_id": str,
                "timestamp": str,
                "severity": str,
                "sector_id": str,
                "summary": str,
                "details": {
                    "voltage": float,
                    "load": float,
                    "phase": str,
                    "backup_status": str,
                    ...
                }
            }

    Returns:
        Recovery plan dictionary with structure:
            {
                "plan_id": str,
                "plan_name": str,
                "status": str,
                "steps": List[str],
                "estimated_completion": str,
                "assigned_agents": List[str]
            }
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # If no API key, return fallback
    if not api_key:
        logger.info("GEMINI_API_KEY not set, using fallback recovery plan")
        return _generate_fallback_plan(event)

    try:
        # Import Google Generative AI
        try:
            import google.generativeai as genai
        except ImportError:
            logger.warning(
                "google-generativeai library not installed. Install with: pip install google-generativeai"
            )
            logger.info("Using fallback recovery plan")
            return _generate_fallback_plan(event)

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Prepare prompt
        event_json = json.dumps(event, indent=2)
        prompt = RECOVERY_PLAN_PROMPT.format(event_json=event_json)

        logger.info("Calling Gemini API to generate recovery plan...")

        # Call Gemini API
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1000,
            },
        )

        # Extract text from response
        response_text = response.text if hasattr(response, "text") else str(response)

        logger.debug(f"Gemini response: {response_text[:500]}...")

        # Parse JSON from response
        plan_data = _extract_json_from_text(response_text)

        if not plan_data:
            logger.warning("Failed to parse JSON from Gemini response, using fallback")
            return _generate_fallback_plan(event)

        # Validate required fields
        required_fields = ["plan_id", "plan_name", "status", "steps"]
        missing_fields = [field for field in required_fields if field not in plan_data]

        if missing_fields:
            logger.warning(
                f"Gemini response missing required fields: {missing_fields}, using fallback"
            )
            return _generate_fallback_plan(event)

        # Ensure steps is a list
        if not isinstance(plan_data.get("steps"), list):
            logger.warning("Gemini response 'steps' is not a list, using fallback")
            return _generate_fallback_plan(event)

        # Add defaults for optional fields
        if "estimated_completion" not in plan_data:
            hours = 2.0
            plan_data["estimated_completion"] = (
                (datetime.utcnow() + timedelta(hours=hours)).isoformat() + "Z"
            )

        if "assigned_agents" not in plan_data:
            plan_data["assigned_agents"] = ["agent-001", "agent-002"]

        logger.info(f"Successfully generated recovery plan: {plan_data.get('plan_id')}")
        return plan_data

    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}", exc_info=True)
        logger.info("Using fallback recovery plan")
        return _generate_fallback_plan(event)

