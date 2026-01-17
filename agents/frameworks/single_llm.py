"""
Single LLM Framework

Uses Gemini API for single-shot plan generation (no agent coordination).
"""

import asyncio
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SingleLLMFramework:
    """Single-shot LLM decision framework using Gemini."""

    def __init__(self):
        """Initialize the single LLM framework."""
        self.framework_name = "SINGLE_LLM"
        self.confidence_score = 0.8  # LLM confidence (estimated)

    async def generate_plan(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate recovery plan using Gemini API (single-shot).

        Args:
            event: Power failure event

        Returns:
            Framework result with plan and metrics
        """
        start_time = time.time()

        try:
            # Import Gemini client
            import sys
            import os

            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from ai.llm_client import get_recovery_plan

            # Generate plan using Gemini (synchronous function)
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            plan_details = await loop.run_in_executor(None, get_recovery_plan, event)

            execution_time_ms = (time.time() - start_time) * 1000

            # Extract metrics
            steps = plan_details.get("steps", [])
            priority_violations = []  # Single LLM doesn't track violations

            return {
                "framework_name": self.framework_name,
                "plan_output": plan_details,
                "execution_time_ms": round(execution_time_ms, 2),
                "number_of_actions": len(steps),
                "priority_violations": priority_violations,
                "confidence_score": self.confidence_score,
                "metadata": {
                    "llm_model": "gemini-pro",
                    "single_shot": True,
                    "fallback_used": plan_details.get("_fallback", False),
                },
            }

        except Exception as e:
            logger.error(f"Single LLM framework error: {e}", exc_info=True)
            # Return fallback plan
            return self._generate_fallback(event, start_time)

    def _generate_fallback(self, event: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Generate fallback plan if LLM fails."""
        from datetime import datetime, timedelta

        sector_id = event.get("sector_id", "unknown")
        severity = event.get("severity", "error")

        plan_output = {
            "plan_id": f"RP-LLM-FALLBACK-{datetime.utcnow().year}",
            "plan_name": f"{sector_id} Recovery Plan (LLM Fallback)",
            "status": "draft",
            "steps": [
                "Assess situation",
                "Apply standard recovery procedures",
                "Monitor system status",
            ],
            "estimated_completion": (datetime.utcnow() + timedelta(hours=2)).isoformat()
            + "Z",
            "assigned_agents": ["agent-001"],
            "reasoning": "LLM unavailable, using fallback plan",
        }

        execution_time_ms = (time.time() - start_time) * 1000

        return {
            "framework_name": self.framework_name,
            "plan_output": plan_output,
            "execution_time_ms": round(execution_time_ms, 2),
            "number_of_actions": len(plan_output["steps"]),
            "priority_violations": [],
            "confidence_score": 0.5,  # Lower confidence for fallback
            "metadata": {
                "llm_model": "fallback",
                "error": True,
            },
        }


