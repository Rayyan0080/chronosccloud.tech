"""
Solution Generators for Airspace Conflicts and Hotspots

Supports RULES (deterministic) and LLM (Gemini) modes.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


def generate_solutions_rules(
    conflicts: List[Dict[str, Any]],
    hotspots: List[Dict[str, Any]],
    trajectories: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate solutions using deterministic rules/heuristics.

    Proposes: altitude change, speed change, departure shift

    Args:
        conflicts: List of conflict objects
        hotspots: List of hotspot objects
        trajectories: List of flight trajectories

    Returns:
        List of solution dictionaries
    """
    solutions = []

    # Solutions for conflicts using heuristics
    for conflict in conflicts:
        solution_id = f"SOL-RULES-{str(uuid4())[:8].upper()}"
        flight_ids = conflict.get("flight_ids", [])
        conflict_details = conflict.get("details", conflict)

        if len(flight_ids) >= 2:
            # Heuristic 1: Altitude change for first flight
            # Heuristic 2: Speed change for second flight
            # Heuristic 3: Departure shift if time-based conflict

            proposed_actions = []

            # Flight 1: Altitude change (increase by 2000 feet)
            flight1_altitude = None
            if trajectories:
                for traj in trajectories:
                    if traj.get("flight_id") == flight_ids[0]:
                        flight1_altitude = traj.get("altitude", 35000)
                        break

            # Default altitude if not found in trajectories
            if flight1_altitude is None:
                flight1_altitude = 35000

            new_altitude = min(flight1_altitude + 2000, 41000)  # Max FL410
            proposed_actions.append({
                "flight_id": flight_ids[0],
                "action": "altitude_change",
                "new_altitude": new_altitude,
                "delay_minutes": 0,
                "reasoning": "Increase altitude to create vertical separation",
            })

            # Flight 2: Speed change (reduce by 15 knots)
            flight2_speed = None
            if trajectories:
                for traj in trajectories:
                    if traj.get("flight_id") == flight_ids[1]:
                        flight2_speed = traj.get("speed", 450)
                        break

            # Default speed if not found in trajectories
            if flight2_speed is None:
                flight2_speed = 450

            new_speed = max(flight2_speed - 15, 300)  # Min 300 knots
            proposed_actions.append({
                "flight_id": flight_ids[1],
                "action": "speed_change",
                "speed_change_knots": -15,
                "new_speed": new_speed,
                "delay_minutes": 0,
                "reasoning": "Reduce speed to create temporal separation",
            })

            # If conflict is time-based, add departure shift
            conflict_time = conflict_details.get("conflict_time")
            if conflict_time:
                proposed_actions.append({
                    "flight_id": flight_ids[0],
                    "action": "departure_shift",
                    "delay_minutes": 5,
                    "reasoning": "Shift departure time to avoid conflict window",
                })

            if proposed_actions:
                solutions.append({
                    "solution_id": solution_id,
                    "solution_type": "multi_action",
                    "problem_id": conflict.get("conflict_id"),
                    "affected_flights": flight_ids,
                    "proposed_actions": proposed_actions,
                    "estimated_impact": {
                        "total_delay_minutes": sum(a.get("delay_minutes", 0) for a in proposed_actions),
                        "fuel_impact_percent": 1.5,
                        "affected_passengers": len(flight_ids) * 150,
                    },
                    "confidence_score": 0.85,
                    "generated_by": "rules-engine",
                    "requires_approval": True,
                })

    # Solutions for hotspots using heuristics
    for hotspot in hotspots:
        solution_id = f"SOL-RULES-{str(uuid4())[:8].upper()}"
        affected_flights = hotspot.get("affected_flights", [])
        hotspot_details = hotspot.get("details", hotspot)

        if len(affected_flights) > 0:
            proposed_actions = []

            # Apply speed reduction to first 3 flights
            for flight_id in affected_flights[:3]:
                # Find flight trajectory
                flight_speed = None
                if trajectories:
                    for traj in trajectories:
                        if traj.get("flight_id") == flight_id:
                            flight_speed = traj.get("speed", 450)
                            break

                # Default speed if not found
                if flight_speed is None:
                    flight_speed = 450

                new_speed = max(flight_speed - 20, 300)
                proposed_actions.append({
                    "flight_id": flight_id,
                    "action": "speed_reduction",
                    "speed_change_knots": -20,
                    "new_speed": new_speed,
                    "delay_minutes": 2,
                    "reasoning": "Reduce speed to decrease hotspot density",
                })

            if proposed_actions:
                solutions.append({
                    "solution_id": solution_id,
                    "solution_type": "speed_adjustment",
                    "problem_id": hotspot.get("hotspot_id"),
                    "affected_flights": affected_flights[:3],
                    "proposed_actions": proposed_actions,
                    "estimated_impact": {
                        "total_delay_minutes": 2,
                        "fuel_impact_percent": 1.0,
                        "affected_passengers": len(affected_flights[:3]) * 150,
                    },
                    "confidence_score": 0.80,
                    "generated_by": "rules-engine",
                    "requires_approval": False,
                })

    return solutions


def generate_solutions_llm(
    conflicts: List[Dict[str, Any]],
    hotspots: List[Dict[str, Any]],
    trajectories: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate solutions using LLM (Gemini).

    Sends conflict/hotspot summaries to Gemini and asks for STRICT JSON solutions.
    Falls back to RULES if parsing fails.

    Args:
        conflicts: List of conflict objects
        hotspots: List of hotspot objects
        trajectories: List of flight trajectories

    Returns:
        List of solution dictionaries
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.warning("GEMINI_API_KEY not set, falling back to RULES")
        return generate_solutions_rules(conflicts, hotspots, trajectories)

    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai not installed, falling back to RULES")
        return generate_solutions_rules(conflicts, hotspots, trajectories)

    try:
        genai.configure(api_key=gemini_api_key)

        # Build summary for LLM
        summary = {
            "conflicts": [
                {
                    "conflict_id": c.get("conflict_id"),
                    "flight_ids": c.get("flight_ids", []),
                    "severity": c.get("severity_level"),
                    "minimum_separation": c.get("minimum_separation"),
                    "required_separation": c.get("required_separation"),
                }
                for c in conflicts
            ],
            "hotspots": [
                {
                    "hotspot_id": h.get("hotspot_id"),
                    "affected_flights": h.get("affected_flights", []),
                    "severity": h.get("severity"),
                    "density": h.get("density"),
                }
                for h in hotspots
            ],
            "trajectories": [
                {
                    "flight_id": t.get("flight_id"),
                    "altitude": t.get("altitude"),
                    "speed": t.get("speed"),
                    "route": t.get("route", []),
                }
                for t in trajectories
            ],
        }

        prompt = f"""You are an air traffic control AI assistant. Analyze the following airspace conflicts and hotspots, and generate solutions.

Return ONLY valid JSON, no other text. Use this exact structure:

{{
  "solutions": [
    {{
      "solution_id": "SOL-LLM-XXXXX",
      "solution_type": "altitude_change|speed_change|departure_shift|reroute|multi_action",
      "problem_id": "conflict_id or hotspot_id",
      "affected_flights": ["FLT-XXX", "FLT-YYY"],
      "proposed_actions": [
        {{
          "flight_id": "FLT-XXX",
          "action": "altitude_change|speed_change|departure_shift|reroute",
          "new_altitude": 37000 (if altitude_change),
          "speed_change_knots": -15 (if speed_change),
          "delay_minutes": 5 (if departure_shift),
          "new_waypoints": ["WP1", "WP2"] (if reroute),
          "reasoning": "Brief explanation"
        }}
      ],
      "estimated_impact": {{
        "total_delay_minutes": 5,
        "fuel_impact_percent": 2.0,
        "affected_passengers": 300
      }},
      "confidence_score": 0.85,
      "requires_approval": true
    }}
  ]
}}

Airspace Situation:
{json.dumps(summary, indent=2)}

Generate solutions for all conflicts and hotspots. Prioritize safety and minimize delays."""

        logger.info("Calling Gemini API for airspace solutions...")
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # Lower temperature for more deterministic output
                "max_output_tokens": 2000,
            },
        )

        response_text = response.text if hasattr(response, "text") else str(response)
        logger.debug(f"Gemini response: {response_text[:500]}...")

        # Extract JSON
        json_data = _extract_json_from_text(response_text)
        if not json_data or "solutions" not in json_data:
            logger.warning("Failed to parse Gemini response, falling back to RULES")
            return generate_solutions_rules(conflicts, hotspots, trajectories)

        solutions = json_data.get("solutions", [])
        # Add generated_by field
        for solution in solutions:
            solution["generated_by"] = "llm-gemini"

        logger.info(f"Generated {len(solutions)} solutions from LLM")
        return solutions

    except Exception as e:
        logger.error(f"LLM solution generation failed: {e}, falling back to RULES")
        return generate_solutions_rules(conflicts, hotspots, trajectories)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text response."""
    try:
        # Try parsing entire text
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from code blocks
    import re
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None

