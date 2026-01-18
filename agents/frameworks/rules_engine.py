"""
Rules Engine Framework

Deterministic rule-based decision framework with no LLM dependency.
Uses predefined rules to generate recovery plans.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RulesEngineFramework:
    """Deterministic rules-based decision framework."""

    def __init__(self):
        """Initialize the rules engine."""
        self.framework_name = "RULES_ENGINE"
        self.confidence_score = 1.0  # Rules are deterministic

    def generate_plan(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate recovery plan using deterministic rules.

        Args:
            event: Power failure event

        Returns:
            Framework result with plan and metrics
        """
        start_time = time.time()

        sector_id = event.get("sector_id", "unknown")
        severity = event.get("severity", "info")  # Default to info, not error
        details = event.get("details", {})
        voltage = details.get("voltage", 0)
        load = details.get("load", 0)

        # Rule 1: Critical voltage (< 10V) = immediate action
        if voltage < 10:
            steps = [
                "Immediate safety shutdown of affected sector",
                "Activate emergency backup power",
                "Notify emergency response team",
                "Isolate sector from grid",
                "Begin damage assessment",
                "Coordinate restoration with maintenance",
            ]
            priority_violations = []
            hours = 4.0

        # Rule 2: Low voltage (10-50V) = standard recovery
        elif voltage < 50:
            steps = [
                "Assess circuit integrity",
                "Isolate affected circuits",
                "Activate backup power systems",
                "Verify backup system operation",
                "Restore primary power gradually",
                "Monitor system stability",
            ]
            priority_violations = []
            hours = 2.5

        # Rule 3: Warning voltage (50-90V) = monitoring + correction
        elif voltage < 90:
            steps = [
                "Monitor power levels continuously",
                "Investigate voltage fluctuation cause",
                "Apply voltage regulation",
                "Verify system returns to normal",
            ]
            priority_violations = []
            hours = 1.0

        # Rule 4: Normal voltage but high load = capacity management
        elif load > 80:
            steps = [
                "Monitor load levels",
                "Distribute load across sectors",
                "Activate additional capacity if available",
                "Verify load balancing",
            ]
            priority_violations = []
            hours = 0.5

        # Rule 5: Normal operation
        else:
            steps = [
                "Continue normal operation monitoring",
                "Log event for analysis",
            ]
            priority_violations = []
            hours = 0.0

        # Generate plan
        year = datetime.utcnow().year
        plan_id = f"RP-RULES-{year}-{str(uuid4())[:8].upper()}"

        plan_output = {
            "plan_id": plan_id,
            "plan_name": f"{sector_id.replace('-', ' ').title()} Recovery Plan (Rules-Based)",
            "status": "draft",
            "steps": steps,
            "estimated_completion": (datetime.utcnow() + timedelta(hours=hours)).isoformat()
            + "Z",
            "assigned_agents": self._assign_agents(severity),
            "reasoning": f"Rules-based decision: voltage={voltage}V, load={load}%, severity={severity}",
        }

        execution_time_ms = (time.time() - start_time) * 1000

        return {
            "framework_name": self.framework_name,
            "plan_output": plan_output,
            "execution_time_ms": round(execution_time_ms, 2),
            "number_of_actions": len(steps),
            "priority_violations": priority_violations,
            "confidence_score": self.confidence_score,
            "metadata": {
                "rule_applied": self._get_rule_applied(voltage, load),
                "deterministic": True,
            },
        }

    def _assign_agents(self, severity: str) -> list:
        """Assign agents based on severity."""
        if severity == "critical":
            return ["agent-001", "agent-002", "agent-003"]
        elif severity == "moderate" or severity == "error":  # 'error' kept for backward compatibility
            return ["agent-001", "agent-002"]
        else:
            return ["agent-001"]

    def _get_rule_applied(self, voltage: float, load: float) -> str:
        """Get the rule that was applied."""
        if voltage < 10:
            return "critical_voltage_shutdown"
        elif voltage < 50:
            return "low_voltage_recovery"
        elif voltage < 90:
            return "voltage_regulation"
        elif load > 80:
            return "load_balancing"
        else:
            return "normal_operation"


