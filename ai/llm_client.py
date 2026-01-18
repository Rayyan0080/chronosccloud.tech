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
from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Import prompt template
from ai.prompts import RECOVERY_PLAN_PROMPT


class PlannerProvider(str, Enum):
    """Enum for planner provider types."""
    RULES = "rules"
    GEMINI = "gemini"
    CEREBRAS = "cerebras"


# JSON Schema for recovery plan validation
RECOVERY_PLAN_SCHEMA = {
    "type": "object",
    "required": ["plan_id", "plan_name", "status", "steps"],
    "properties": {
        "plan_id": {"type": "string"},
        "plan_name": {"type": "string"},
        "status": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "estimated_completion": {"type": "string"},
        "assigned_agents": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
}


def _validate_recovery_plan(plan_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate recovery plan against schema.
    
    Args:
        plan_data: Recovery plan dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    required_fields = ["plan_id", "plan_name", "status", "steps"]
    missing_fields = [field for field in required_fields if field not in plan_data]
    
    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"
    
    # Validate types
    if not isinstance(plan_data.get("plan_id"), str):
        return False, "plan_id must be a string"
    
    if not isinstance(plan_data.get("plan_name"), str):
        return False, "plan_name must be a string"
    
    if not isinstance(plan_data.get("status"), str):
        return False, "status must be a string"
    
    if not isinstance(plan_data.get("steps"), list):
        return False, "steps must be a list"
    
    if plan_data.get("steps") and not all(isinstance(step, str) for step in plan_data["steps"]):
        return False, "All steps must be strings"
    
    return True, None


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
    
    SAFETY: This function NEVER crashes. Always falls back to rules-based planner
    if LLM APIs fail, timeout, or return invalid JSON.

    Tries providers in order:
    1. Cerebras (if LLM_SERVICE_API_KEY is set)
    2. Gemini (if GEMINI_API_KEY is set)
    3. Rules-based fallback plan (always available)

    Args:
        event: Power failure event dictionary

    Returns:
        Recovery plan dictionary (always valid, never None)
    """
    provider_used = PlannerProvider.RULES.value
    
    # Check for Cerebras first
    cerebras_api_key = os.getenv("LLM_SERVICE_API_KEY")
    cerebras_endpoint = os.getenv("LLM_SERVICE_ENDPOINT", "https://api.cerebras.ai/v1")
    cerebras_model = os.getenv("LLM_SERVICE_PLANNING_MODEL_NAME", "openai/zai-glm-4.7")

    if cerebras_api_key:
        try:
            plan = _get_recovery_plan_cerebras(event, cerebras_endpoint, cerebras_api_key, cerebras_model)
            provider_used = PlannerProvider.CEREBRAS.value
            logger.info(f"Recovery plan generated using {provider_used.upper()} provider")
            return plan
        except Exception as e:
            logger.warning(f"Cerebras API failed: {e}, trying Gemini...")

    # Fall back to Gemini
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            plan = _get_recovery_plan_gemini(event, gemini_api_key)
            provider_used = PlannerProvider.GEMINI.value
            logger.info(f"Recovery plan generated using {provider_used.upper()} provider")
            return plan
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}, using rules-based fallback...")

    # Use rules-based fallback plan (always available, never fails)
    logger.info(f"Using {provider_used.upper()} provider (fallback)")
    fallback_plan = _generate_fallback_plan(event)
    fallback_plan["_llm_provider"] = "rules"
    fallback_plan["_llm_model"] = "fallback"
    fallback_plan["provider"] = "rules"
    fallback_plan["model"] = "fallback"
    fallback_plan["_fallback"] = True
    return fallback_plan


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

    # Add timeout to prevent hanging (30 seconds max)
    response = requests.post(url, json=data, headers=headers, timeout=30)

    if response.status_code != 200:
        error_text = response.text[:200] if len(response.text) > 200 else response.text
        raise Exception(f"Cerebras API error: {response.status_code} - {error_text}")

    response_data = response.json()
    response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

    logger.debug(f"Cerebras response: {response_text[:500]}...")

    # Parse JSON from response (STRICT parsing)
    plan_data = _extract_json_from_text(response_text)

    if not plan_data:
        logger.warning("Failed to parse JSON from Cerebras response, using rules-based fallback")
        raise ValueError("Invalid JSON response from Cerebras API")

    # Validate against schema (STRICT validation)
    is_valid, error_msg = _validate_recovery_plan(plan_data)
    if not is_valid:
        logger.warning(f"Cerebras response validation failed: {error_msg}, using rules-based fallback")
        raise ValueError(f"Invalid recovery plan schema: {error_msg}")

    logger.info("Recovery plan generated successfully using Cerebras (validated)")
    # Add provider info to plan
    plan_data["_llm_provider"] = "cerebras"
    plan_data["_llm_model"] = model
    plan_data["provider"] = "cerebras"
    plan_data["model"] = model
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

    # Parse JSON from response (STRICT parsing)
    plan_data = _extract_json_from_text(response_text)

    if not plan_data:
        logger.warning("Failed to parse JSON from Gemini response, using rules-based fallback")
        raise ValueError("Invalid JSON response from Gemini API")

    # Validate against schema (STRICT validation)
    is_valid, error_msg = _validate_recovery_plan(plan_data)
    if not is_valid:
        logger.warning(f"Gemini response validation failed: {error_msg}, using rules-based fallback")
        raise ValueError(f"Invalid recovery plan schema: {error_msg}")

    logger.info("Recovery plan generated successfully using Gemini (validated)")
    # Add provider info to plan
    plan_data["_llm_provider"] = "gemini"
    plan_data["_llm_model"] = "gemini-pro"
    plan_data["provider"] = "gemini"
    plan_data["model"] = "gemini-pro"
    return plan_data

