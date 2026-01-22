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
from typing import Dict, Any, Optional, List
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Import prompt template
from ai.prompts import RECOVERY_PLAN_PROMPT, FIX_PROPOSAL_PROMPT, DEFENSE_ASSESSMENT_PROMPT

# Import schema for fix validation
from agents.shared.schema import (
    FixDetails, FixAction, ActionType, RiskLevel, FixSource, 
    ExpectedImpact, ActionVerification, ActionTarget, Severity
)
from agents.shared.constants import (
    FIX_PROPOSED_TOPIC, 
    FIX_REVIEW_REQUIRED_TOPIC,
    DEFENSE_THREAT_ASSESSED_TOPIC,
)
from agents.shared.messaging import publish


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


def _generate_fallback_fix(event: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """
    Generate a fallback fix proposal when LLM API is unavailable.

    Args:
        event: Event dictionary (incident, hotspot, or plan)
        correlation_id: Correlation ID linking to the original event

    Returns:
        Fix proposal dictionary
    """
    from datetime import timezone
    
    # Generate fix ID
    fix_id = f"FIX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    # Determine fix type based on event
    event_type = event.get("source", "unknown")
    sector_id = event.get("sector_id", "unknown")
    
    # Create a simple rules-based fix
    if "transit" in event_type.lower() or "hotspot" in str(event.get("details", {})).lower():
        # Transit fix
        title = f"Reroute to reduce delays in {sector_id}"
        summary = "Proposed reroute to bypass congestion area"
        action_type = ActionType.TRANSIT_REROUTE_SIM
        target = ActionTarget(route_id="ROUTE-95")
        risk_level = RiskLevel.MED
        delay_reduction = 10.0
    elif "airspace" in event_type.lower() or "conflict" in str(event.get("details", {})).lower():
        # Airspace fix
        title = f"Altitude adjustment for conflict mitigation in {sector_id}"
        summary = "Proposed altitude change to resolve conflict"
        action_type = ActionType.AIRSPACE_MITIGATION_SIM
        target = ActionTarget(sector_id=sector_id)
        risk_level = RiskLevel.LOW
        delay_reduction = 0.0
    elif "power" in event_type.lower():
        # Power fix
        title = f"Power recovery plan for {sector_id}"
        summary = "Proposed power restoration steps"
        action_type = ActionType.POWER_RECOVERY_SIM
        target = ActionTarget(sector_id=sector_id)
        risk_level = RiskLevel.MED
        delay_reduction = 0.0
    else:
        # Generic fix
        title = f"Mitigation plan for {sector_id}"
        summary = "Proposed mitigation actions"
        action_type = ActionType.TRAFFIC_ADVISORY_SIM
        target = ActionTarget(sector_id=sector_id)
        risk_level = RiskLevel.LOW
        delay_reduction = 5.0
    
    return {
        "fix_id": fix_id,
        "correlation_id": correlation_id,
        "source": FixSource.RULES.value,
        "title": title,
        "summary": summary,
        "actions": [
            {
                "type": action_type.value,
                "target": target.dict(exclude_none=True),
                "params": {},
                "verification": {
                    "metric_name": "delay_reduction",
                    "threshold": 5.0,
                    "window_seconds": 300
                }
            }
        ],
        "risk_level": risk_level.value,
        "expected_impact": {
            "delay_reduction": delay_reduction,
            "risk_score_delta": -0.1
        },
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "proposed_by": "agent-fix-generator",
        "requires_human_approval": True
    }


def _validate_fix_proposal(fix_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate fix proposal against FixDetails pydantic model.
    
    Args:
        fix_data: Fix proposal dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields first
    required_fields = ["title", "summary", "actions", "risk_level", "expected_impact"]
    missing_fields = [field for field in required_fields if field not in fix_data]
    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"
    
    # Validate actions array
    if not isinstance(fix_data.get("actions"), list) or len(fix_data["actions"]) == 0:
        return False, "actions must be a non-empty array"
    
    # Validate each action has verification
    for i, action in enumerate(fix_data["actions"]):
        if not isinstance(action, dict):
            return False, f"action[{i}] must be an object"
        if "type" not in action:
            return False, f"action[{i}] missing 'type' field"
        if "target" not in action:
            return False, f"action[{i}] missing 'target' field"
        if "verification" not in action:
            return False, f"action[{i}] missing 'verification' field"
        # Validate verification structure
        verification = action.get("verification", {})
        if not isinstance(verification, dict):
            return False, f"action[{i}].verification must be an object"
        if "metric_name" not in verification or "threshold" not in verification or "window_seconds" not in verification:
            return False, f"action[{i}].verification missing required fields (metric_name, threshold, window_seconds)"
    
    # Remove top-level verification if present (not in schema, but prompt may include it)
    fix_data_clean = fix_data.copy()
    if "verification" in fix_data_clean and isinstance(fix_data_clean["verification"], dict):
        # Top-level verification is optional, remove it for schema validation
        del fix_data_clean["verification"]
    
    try:
        # Validate using pydantic model (without top-level verification)
        fix_details = FixDetails(**fix_data_clean)
        return True, None
    except Exception as e:
        return False, str(e)


async def get_fix_proposal(event: Dict[str, Any], correlation_id: str) -> Optional[Dict[str, Any]]:
    """
    Generate fix proposal using Gemini API with strict JSON output and validation.
    
    SAFETY: This function NEVER crashes. Always falls back to rules-based fix
    if Gemini API fails, timeout, or returns invalid JSON.
    
    On success, publishes:
    - fix.proposed event
    - fix.review_required event
    
    Args:
        event: Event dictionary (incident, hotspot, or plan)
        correlation_id: Correlation ID linking to the original event
        
    Returns:
        Fix proposal dictionary if successful, None if fallback used
    """
    from datetime import timezone
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.info("GEMINI_API_KEY not set, using rules-based fallback fix")
        return None
    
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai library not installed, using rules-based fallback fix")
        return None
    
    try:
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Prepare prompt
        event_json = json.dumps(event, indent=2)
        prompt = FIX_PROPOSAL_PROMPT.format(event_json=event_json)
        
        logger.info("Calling Gemini API to generate fix proposal...")
        
        # Call Gemini API with strict JSON output
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # Lower temperature for more consistent JSON
                "max_output_tokens": 2000,
            },
        )
        
        # Extract text from response
        response_text = response.text if hasattr(response, "text") else str(response)
        logger.debug(f"Gemini response: {response_text[:500]}...")
        
        # Parse JSON from response (STRICT parsing)
        fix_data = _extract_json_from_text(response_text)
        
        if not fix_data:
            logger.warning("Failed to parse JSON from Gemini response, using rules-based fallback")
            return None
        
        # Validate against pydantic FixDetails model
        is_valid, error_msg = _validate_fix_proposal(fix_data)
        if not is_valid:
            logger.warning(f"Gemini fix proposal validation failed: {error_msg}, using rules-based fallback")
            return None
        
        # Add required fields for FixDetails
        fix_id = f"FIX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        fix_data["fix_id"] = fix_id
        fix_data["correlation_id"] = correlation_id
        fix_data["source"] = FixSource.GEMINI.value
        fix_data["created_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        fix_data["proposed_by"] = "agent-fix-generator"
        if "requires_human_approval" not in fix_data:
            fix_data["requires_human_approval"] = True
        
        # Ensure each action has verification (required by prompt)
        for action in fix_data.get("actions", []):
            if "verification" not in action:
                logger.warning("Action missing verification field, using rules-based fallback")
                return None
        
        # Re-validate with all fields (verification at top level is optional, will be removed in validation)
        is_valid, error_msg = _validate_fix_proposal(fix_data)
        if not is_valid:
            logger.warning(f"Fix proposal validation failed after adding fields: {error_msg}, using rules-based fallback")
            return None
        
        logger.info(f"Fix proposal generated successfully using Gemini: {fix_id}")
        
        # Create fix.proposed event
        fix_proposed_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "fix-coordinator",
            "severity": Severity.WARNING.value,
            "sector_id": event.get("sector_id", "unknown"),
            "summary": f"Fix {fix_id} proposed: {fix_data.get('title', 'Untitled')}",
            "correlation_id": correlation_id,
            "details": fix_data
        }
        
        # Publish fix.proposed event
        await publish(FIX_PROPOSED_TOPIC, fix_proposed_event)
        logger.info(f"Published fix.proposed event: {fix_id}")
        
        # Create fix.review_required event
        fix_review_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "fix-reviewer",
            "severity": Severity.WARNING.value,
            "sector_id": event.get("sector_id", "unknown"),
            "summary": f"Fix {fix_id} requires human review",
            "correlation_id": correlation_id,
            "details": fix_data
        }
        
        # Publish fix.review_required event
        await publish(FIX_REVIEW_REQUIRED_TOPIC, fix_review_event)
        logger.info(f"Published fix.review_required event: {fix_id}")
        
        return fix_data
        
    except Exception as e:
        logger.warning(f"Gemini API failed: {e}, using rules-based fallback")
        return None


async def get_fix_proposal_with_fallback(event: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """
    Generate fix proposal with automatic fallback to rules-based fix.
    
    Tries Gemini first, falls back to rules-based fix if Gemini fails.
    Always publishes fix.proposed and fix.review_required events.
    
    Args:
        event: Event dictionary (incident, hotspot, or plan)
        correlation_id: Correlation ID linking to the original event
        
    Returns:
        Fix proposal dictionary (always valid, never None)
    """
    from datetime import timezone
    
    # Try Gemini first (this publishes events on success)
    fix_data = await get_fix_proposal(event, correlation_id)
    
    if fix_data:
        return fix_data
    
    # Fall back to rules-based fix
    logger.info("Using rules-based fallback fix")
    fix_data = _generate_fallback_fix(event, correlation_id)
    
    # Publish events for fallback fix
    fix_id = fix_data.get("fix_id")
    sector_id = event.get("sector_id", "unknown")
    
    # Create fix.proposed event
    fix_proposed_event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "fix-coordinator",
        "severity": Severity.WARNING.value,
        "sector_id": sector_id,
        "summary": f"Fix {fix_id} proposed: {fix_data.get('title', 'Untitled')}",
        "correlation_id": correlation_id,
        "details": fix_data
    }
    
    # Create fix.review_required event
    fix_review_event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "fix-reviewer",
        "severity": Severity.WARNING.value,
        "sector_id": sector_id,
        "summary": f"Fix {fix_id} requires human review",
        "correlation_id": correlation_id,
        "details": fix_data
    }
    
    # Publish both events
    await publish(FIX_PROPOSED_TOPIC, fix_proposed_event)
    logger.info(f"Published fix.proposed event (fallback): {fix_id}")
    
    await publish(FIX_REVIEW_REQUIRED_TOPIC, fix_review_event)
    logger.info(f"Published fix.review_required event (fallback): {fix_id}")
    
    return fix_data


def _validate_defense_assessment(assessment_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate defense assessment against required schema.
    
    Args:
        assessment_data: Assessment dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    required_fields = ["threat_type", "likely_cause", "recommended_posture", "protective_actions", "escalation_needed"]
    missing_fields = [field for field in required_fields if field not in assessment_data]
    
    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"
    
    # Validate threat_type
    valid_threat_types = ["airspace", "cyber_physical", "environmental", "civil"]
    if assessment_data.get("threat_type") not in valid_threat_types:
        return False, f"threat_type must be one of: {valid_threat_types}"
    
    # Validate types
    if not isinstance(assessment_data.get("likely_cause"), str):
        return False, "likely_cause must be a string"
    
    if not isinstance(assessment_data.get("recommended_posture"), str):
        return False, "recommended_posture must be a string"
    
    if not isinstance(assessment_data.get("protective_actions"), list):
        return False, "protective_actions must be a list"
    
    if len(assessment_data.get("protective_actions", [])) == 0:
        return False, "protective_actions must be a non-empty array"
    
    if not all(isinstance(action, str) for action in assessment_data.get("protective_actions", [])):
        return False, "All protective_actions must be strings"
    
    if not isinstance(assessment_data.get("escalation_needed"), bool):
        return False, "escalation_needed must be a boolean"
    
    return True, None


async def assess_defense_threat(
    threat_id: str,
    threat_summary: str,
    sources: List[str],
    confidence_score: float,
    current_posture: str,
    sector_id: str = "unknown",
) -> Optional[Dict[str, Any]]:
    """
    Assess a defense threat using Gemini API with strict JSON output and validation.
    
    SAFETY: This function NEVER crashes. Returns None if Gemini API fails or returns invalid JSON.
    
    On success, publishes:
    - defense.threat.assessed event
    
    Args:
        threat_id: Threat identifier
        threat_summary: Summary of the threat
        sources: List of data sources involved
        confidence_score: Confidence score (0.0-1.0)
        current_posture: Current city defense posture
        sector_id: Sector identifier
        
    Returns:
        Assessment dictionary if successful, None if fallback needed
    """
    from datetime import timezone
    from agents.shared.schema import DefenseThreatAssessedEvent, Severity
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.info("GEMINI_API_KEY not set, skipping Gemini assessment")
        return None
    
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai library not installed, skipping Gemini assessment")
        return None
    
    try:
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Prepare prompt
        sources_str = ", ".join(sources) if sources else "unknown"
        prompt = DEFENSE_ASSESSMENT_PROMPT.format(
            threat_summary=threat_summary,
            sources=sources_str,
            confidence_score=confidence_score,
            current_posture=current_posture,
        )
        
        logger.info(f"Calling Gemini API to assess threat {threat_id}...")
        
        # Call Gemini API with strict JSON output
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # Lower temperature for more consistent JSON
                "max_output_tokens": 1500,
            },
        )
        
        # Extract text from response
        response_text = response.text if hasattr(response, "text") else str(response)
        logger.debug(f"Gemini response: {response_text[:500]}...")
        
        # Parse JSON from response (STRICT parsing)
        assessment_data = _extract_json_from_text(response_text)
        
        if not assessment_data:
            logger.warning("Failed to parse JSON from Gemini response")
            return None
        
        # Validate against schema
        is_valid, error_msg = _validate_defense_assessment(assessment_data)
        if not is_valid:
            logger.warning(f"Gemini assessment validation failed: {error_msg}")
            return None
        
        logger.info(f"Defense assessment generated successfully using Gemini for threat {threat_id}")
        
        # Create assessment event
        assessment_score = confidence_score  # Use confidence score as assessment score
        risk_level = assessment_data.get("recommended_posture", "unknown")
        
        # Determine severity based on escalation_needed and threat_type
        if assessment_data.get("escalation_needed", False):
            severity = Severity.CRITICAL
        elif confidence_score >= 0.8:
            severity = Severity.HIGH
        elif confidence_score >= 0.6:
            severity = Severity.MODERATE
        else:
            severity = Severity.WARNING
        
        # Create assessment notes from likely_cause and protective_actions
        assessment_notes = f"Likely cause: {assessment_data.get('likely_cause', 'Unknown')}. "
        assessment_notes += f"Recommended posture: {assessment_data.get('recommended_posture', 'unknown')}. "
        assessment_notes += f"Protective actions: {', '.join(assessment_data.get('protective_actions', []))}"
        
        assessed_event = DefenseThreatAssessedEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            source="defense-threat-assessor",
            severity=severity,
            sector_id=sector_id,
            summary=f"Threat {threat_id} assessed: {assessment_data.get('likely_cause', 'Assessment complete')}",
            correlation_id=threat_id,
            details={
                "threat_id": threat_id,
                "assessment_score": assessment_score,
                "risk_level": risk_level,
                "assessment_notes": assessment_notes,
                "assessed_by": "defense-assessor-gemini",
                "assessed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                # Include full assessment data for reference
                "_assessment_data": assessment_data,
            }
        )
        
        # Publish defense.threat.assessed event
        await publish(DEFENSE_THREAT_ASSESSED_TOPIC, assessed_event.dict())
        logger.info(f"Published defense.threat.assessed event: {threat_id}")
        
        return assessment_data
        
    except Exception as e:
        logger.warning(f"Gemini API failed for threat assessment: {e}")
        return None
