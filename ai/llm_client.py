"""
Unified LLM Client

Supports multiple LLM providers:
- Google Gemini (default)
- Cerebras (alternative, free tier available)
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
    Generate a fallback recovery plan when LLM API is unavailable.

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
            "Immediate safety shutdown of affected sector",
            "Activate emergency backup power systems",
            "Notify emergency response team",
            "Isolate sector from main grid",
            "Begin damage assessment",
            "Coordinate restoration with maintenance team",
        ]
        hours = 4.0
    elif severity == "error":
        steps = [
            "Assess circuit integrity",
            "Isolate affected circuits",
            "Activate backup power systems",
            "Verify backup system operation",
            "Restore primary power gradually",
            "Monitor system stability",
        ]
        hours = 2.5
    else:
        steps = [
            "Monitor power levels continuously",
            "Investigate voltage fluctuation cause",
            "Apply voltage regulation",
            "Verify system returns to normal",
        ]
        hours = 1.0

    return {
        "plan_id": plan_id,
        "plan_name": plan_name,
        "status": "draft",
        "steps": steps,
        "estimated_completion": (datetime.utcnow() + timedelta(hours=hours)).isoformat() + "Z",
        "assigned_agents": ["agent-001", "agent-002"] if severity in ["critical", "error"] else ["agent-001"],
        "reasoning": f"Fallback plan generated for {severity} severity event in {sector_id}",
    }


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response text.

    Args:
        text: Response text that may contain JSON

    Returns:
        Parsed JSON dictionary or None
    """
    # Try to find JSON in the text
    # Look for JSON object pattern
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_pattern, text, re.DOTALL)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # If no JSON found, try parsing entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def get_recovery_plan(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate recovery plan using configured LLM provider.

    Tries providers in order:
    1. Cerebras (if LLM_SERVICE_API_KEY is set)
    2. Gemini (if GEMINI_API_KEY is set)
    3. Fallback plan (if no API keys)

    Args:
        event: Power failure event dictionary

    Returns:
        Recovery plan dictionary
    """
    # Check for Cerebras first
    cerebras_api_key = os.getenv("LLM_SERVICE_API_KEY")
    cerebras_endpoint = os.getenv("LLM_SERVICE_ENDPOINT", "https://api.cerebras.ai/v1")
    cerebras_model = os.getenv("LLM_SERVICE_PLANNING_MODEL_NAME", "openai/zai-glm-4.7")

    if cerebras_api_key:
        try:
            return _get_recovery_plan_cerebras(event, cerebras_endpoint, cerebras_api_key, cerebras_model)
        except Exception as e:
            logger.warning(f"Cerebras API failed: {e}, trying Gemini...")

    # Fall back to Gemini
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            return _get_recovery_plan_gemini(event, gemini_api_key)
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}, using fallback...")

    # Use fallback plan
    logger.info("No LLM API keys configured, using fallback recovery plan")
    return _generate_fallback_plan(event)


def _get_recovery_plan_cerebras(
    event: Dict[str, Any], endpoint: str, api_key: str, model: str
) -> Dict[str, Any]:
    """
    Generate recovery plan using Cerebras API.

    Args:
        event: Power failure event dictionary
        endpoint: Cerebras API endpoint
        api_key: Cerebras API key
        model: Model name (e.g., "openai/zai-glm-4.7")

    Returns:
        Recovery plan dictionary
    """
    try:
        import requests
    except ImportError:
        raise ImportError("requests library required for Cerebras API. Install with: pip install requests")

    # Prepare prompt
    event_json = json.dumps(event, indent=2)
    prompt = RECOVERY_PLAN_PROMPT.format(event_json=event_json)

    logger.info(f"Calling Cerebras API ({model}) to generate recovery plan...")

    # Call Cerebras API (OpenAI-compatible format)
    url = f"{endpoint}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a crisis management AI that generates structured recovery plans in JSON format.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    response = requests.post(url, json=data, headers=headers, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Cerebras API error: {response.status_code} - {response.text}")

    response_data = response.json()
    response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

    logger.debug(f"Cerebras response: {response_text[:500]}...")

    # Parse JSON from response
    plan_data = _extract_json_from_text(response_text)

    if not plan_data:
        logger.warning("Failed to parse JSON from Cerebras response, using fallback")
        return _generate_fallback_plan(event)

    # Validate required fields
    required_fields = ["plan_id", "plan_name", "status", "steps"]
    missing_fields = [field for field in required_fields if field not in plan_data]

    if missing_fields:
        logger.warning(f"Missing required fields in Cerebras response: {missing_fields}, using fallback")
        return _generate_fallback_plan(event)

    logger.info("Recovery plan generated successfully using Cerebras")
    return plan_data


def _get_recovery_plan_gemini(event: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Generate recovery plan using Google Gemini API.

    Args:
        event: Power failure event dictionary
        api_key: Gemini API key

    Returns:
        Recovery plan dictionary
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai library required for Gemini API. Install with: pip install google-generativeai"
        )

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
        logger.warning(f"Missing required fields in Gemini response: {missing_fields}, using fallback")
        return _generate_fallback_plan(event)

    logger.info("Recovery plan generated successfully using Gemini")
    return plan_data

