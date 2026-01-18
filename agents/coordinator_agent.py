"""
Coordinator Agent

Merges power failures and airspace conflicts/hotspots into unified crisis context.
Generates recovery plans when high-severity events occur or airport regions are impacted.
Supports RULES/LLM/AGENTIC modes with fallback to RULES.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.constants import (
    POWER_FAILURE_TOPIC,
    AIRSPACE_CONFLICT_DETECTED_TOPIC,
    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
    AIRSPACE_SOLUTION_PROPOSED_TOPIC,
    AIRSPACE_MITIGATION_APPLIED_TOPIC,
    RECOVERY_PLAN_TOPIC,
    SYSTEM_ACTION_TOPIC,
    TASK_AIRSPACE_DECONFLICT_TOPIC,
    TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC,
    TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC,
)
from agents.shared.schema import Severity
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_published_event,
    capture_exception,
)
from agents.frameworks.rules_engine import RulesEngineFramework
from agents.frameworks.single_llm import SingleLLMFramework
from agents.frameworks.agentic_mesh import AgenticMeshFramework
from ai.llm_client import get_recovery_plan
from trajectory_insight.solution_generators import generate_solutions_rules, generate_solutions_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Enabled frameworks (can be configured via env)
ENABLED_FRAMEWORKS = os.getenv(
    "ENABLED_FRAMEWORKS", "RULES_ENGINE,SINGLE_LLM,AGENTIC_MESH"
).split(",")

# Recovery planning mode: RULES, LLM, or AGENTIC
RECOVERY_MODE = os.getenv("RECOVERY_MODE", "RULES").upper()
# Autonomy mode for airspace solutions: RULES, LLM, or AGENTIC
AUTONOMY_MODE = os.getenv("AUTONOMY_MODE", "RULES").upper()

# Airport sector identifiers (heuristic)
AIRPORT_SECTORS = ["airport", "terminal", "runway", "tower", "kord", "kjfk", "klax", "kdfw", "kmia", "ksea"]

# Priority facilities (hospitals, medevac, critical infrastructure)
PRIORITY_FACILITIES = {
    "hospital": ["hospital", "medical", "clinic", "emergency"],
    "medevac": ["medevac", "helicopter", "ambulance"],
    "airport": AIRPORT_SECTORS,
}


class CoordinatorAgent:
    """Coordinates crisis response with unified context from power and airspace events."""

    def __init__(self):
        """Initialize the coordinator agent."""
        self.frameworks = {}
        self.selected_framework = os.getenv("SELECTED_FRAMEWORK", "AGENTIC_MESH")

        # Crisis context state
        self.crisis_context = {
            "power_state": {},  # sector_id -> latest power event
            "airspace_state": {
                "conflicts": [],  # Latest conflicts
                "hotspots": [],  # Latest hotspots
            },
            "priorities": {
                "hospitals": [],
                "airport": [],
                "medevac": [],
            },
            "last_updated": None,
        }

        # Track applied solutions for airspace.mitigation.applied events
        self.applied_solutions: Dict[str, Dict[str, Any]] = {}

        # Track partial solutions for AGENTIC mode (task_id -> list of partial solutions)
        self.pending_partial_solutions: Dict[str, List[Dict[str, Any]]] = {}
        # Track active tasks (task_id -> task details)
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

        # Initialize frameworks
        if "RULES_ENGINE" in ENABLED_FRAMEWORKS:
            self.frameworks["RULES_ENGINE"] = RulesEngineFramework()
        if "SINGLE_LLM" in ENABLED_FRAMEWORKS:
            self.frameworks["SINGLE_LLM"] = SingleLLMFramework()
        if "AGENTIC_MESH" in ENABLED_FRAMEWORKS:
            self.frameworks["AGENTIC_MESH"] = AgenticMeshFramework()

        logger.info(f"Initialized frameworks: {list(self.frameworks.keys())}")
        logger.info(f"Recovery mode: {RECOVERY_MODE}")
        logger.info(f"Autonomy mode: {AUTONOMY_MODE}")
        logger.info(f"Selected framework: {self.selected_framework}")

    def _update_power_state(self, event: Dict[str, Any]) -> None:
        """Update power state for a sector."""
        sector_id = event.get("sector_id", "unknown")
        self.crisis_context["power_state"][sector_id] = {
            "event_id": event.get("event_id"),
            "timestamp": event.get("timestamp"),
            "severity": event.get("severity"),
            "details": event.get("details", {}),
            "summary": event.get("summary"),
        }
        self.crisis_context["last_updated"] = datetime.utcnow().isoformat() + "Z"

    def _update_airspace_state(self, event: Dict[str, Any], event_type: str) -> None:
        """Update airspace state with conflict or hotspot."""
        details = event.get("details", {})
        event_data = {
            "event_id": event.get("event_id"),
            "timestamp": event.get("timestamp"),
            "severity": event.get("severity"),
            "details": details,
            "summary": event.get("summary"),
        }

        if event_type == "conflict":
            # Add to conflicts, keep only latest 10
            self.crisis_context["airspace_state"]["conflicts"].append(event_data)
            self.crisis_context["airspace_state"]["conflicts"] = self.crisis_context[
                "airspace_state"
            ]["conflicts"][-10:]
        elif event_type == "hotspot":
            # Add to hotspots, keep only latest 10
            self.crisis_context["airspace_state"]["hotspots"].append(event_data)
            self.crisis_context["airspace_state"]["hotspots"] = self.crisis_context[
                "airspace_state"
            ]["hotspots"][-10:]

        self.crisis_context["last_updated"] = datetime.utcnow().isoformat() + "Z"

    def _update_priorities(self, event: Dict[str, Any]) -> None:
        """Update priority facilities based on event sector."""
        sector_id = event.get("sector_id", "").lower()
        summary = event.get("summary", "").lower()

        # Check for hospital/medical facilities
        for keyword in PRIORITY_FACILITIES["hospital"]:
            if keyword in sector_id or keyword in summary:
                if sector_id not in self.crisis_context["priorities"]["hospitals"]:
                    self.crisis_context["priorities"]["hospitals"].append(sector_id)
                break

        # Check for airport facilities
        for keyword in PRIORITY_FACILITIES["airport"]:
            if keyword in sector_id or keyword in summary:
                if sector_id not in self.crisis_context["priorities"]["airport"]:
                    self.crisis_context["priorities"]["airport"].append(sector_id)
                break

        # Check for medevac
        for keyword in PRIORITY_FACILITIES["medevac"]:
            if keyword in sector_id or keyword in summary:
                if sector_id not in self.crisis_context["priorities"]["medevac"]:
                    self.crisis_context["priorities"]["medevac"].append(sector_id)
                break

    def _is_airport_region(self, sector_id: str) -> bool:
        """Check if sector is an airport region."""
        sector_lower = sector_id.lower()
        return any(keyword in sector_lower for keyword in AIRPORT_SECTORS)
    
    def _should_trigger_recovery_plan(self, event: Dict[str, Any], event_type: str) -> bool:
        """
        Determine if recovery plan should be triggered.

        Triggers when:
        - High severity airspace conflict (warning/critical)
        - Power failure impacts airport region
        - Critical power failure in any sector
        """
        severity = event.get("severity", "").lower()
        sector_id = event.get("sector_id", "")

        if event_type == "airspace_conflict":
            # High severity conflict
            if severity in ["warning", "critical", "moderate", "error"]:  # 'error' kept for backward compatibility
                conflict_details = event.get("details", {})
                severity_level = conflict_details.get("severity_level", "").lower()
                if severity_level in ["high", "critical"]:
                    return True

        elif event_type == "power_failure":
            # Critical power failure
            if severity == "critical":
                return True
            # Power failure in airport region
            if self._is_airport_region(sector_id):
                return True

        return False

    def _build_crisis_context(self) -> Dict[str, Any]:
        """Build unified crisis context object."""
        return {
            "power_state": self.crisis_context["power_state"],
            "airspace_state": self.crisis_context["airspace_state"],
            "priorities": self.crisis_context["priorities"],
            "context_timestamp": self.crisis_context.get("last_updated"),
        }

    async def _generate_recovery_plan(self, trigger_event: Dict[str, Any], event_type: str) -> Optional[Dict[str, Any]]:
        """
        Generate recovery plan using configured mode (RULES/LLM/AGENTIC).

        Args:
            trigger_event: Event that triggered recovery planning
            event_type: Type of event (power_failure, airspace_conflict, etc.)

        Returns:
            Recovery plan dictionary or None if generation failed
        """
        try:
            # Build crisis context
            crisis_context = self._build_crisis_context()

            # Create enhanced event with crisis context
            enhanced_event = {
                **trigger_event,
                "crisis_context": crisis_context,
                "event_type": event_type,
            }

            logger.info("=" * 80)
            logger.info("GENERATING RECOVERY PLAN")
            logger.info("=" * 80)
            logger.info(f"Mode: {RECOVERY_MODE}")
            logger.info(f"Event Type: {event_type}")
            logger.info(f"Power Sectors Affected: {len(crisis_context['power_state'])}")
            logger.info(f"Active Conflicts: {len(crisis_context['airspace_state']['conflicts'])}")
            logger.info(f"Active Hotspots: {len(crisis_context['airspace_state']['hotspots'])}")
            logger.info("=" * 80)

            plan_details = None

            # Use RULES mode (fallback or explicit)
            if RECOVERY_MODE == "RULES" or "RULES_ENGINE" not in self.frameworks:
                if "RULES_ENGINE" in self.frameworks:
                    logger.info("Using RULES_ENGINE framework")
                    rules_result = await asyncio.to_thread(
                        self.frameworks["RULES_ENGINE"].generate_plan, enhanced_event
                    )
                    plan_details = rules_result.get("plan_output")
                else:
                    logger.warning("RULES_ENGINE not available, using LLM fallback")
                    plan_details = get_recovery_plan(enhanced_event)

            # Use LLM mode (via ai/llm_client)
            elif RECOVERY_MODE == "LLM":
                logger.info("Using LLM mode (via ai/llm_client)")
                plan_details = get_recovery_plan(enhanced_event)

            # Use AGENTIC mode (via frameworks)
            elif RECOVERY_MODE == "AGENTIC":
                logger.info("Using AGENTIC mode (via frameworks)")
                if self.selected_framework in self.frameworks:
                    framework = self.frameworks[self.selected_framework]
                    if self.selected_framework == "RULES_ENGINE":
                        result = await asyncio.to_thread(framework.generate_plan, enhanced_event)
                    else:
                        result = await framework.generate_plan(enhanced_event)
                    plan_details = result.get("plan_output")
                else:
                    logger.warning(f"Selected framework {self.selected_framework} not available, falling back to RULES")
                    if "RULES_ENGINE" in self.frameworks:
                        rules_result = await asyncio.to_thread(
                            self.frameworks["RULES_ENGINE"].generate_plan, enhanced_event
                        )
                        plan_details = rules_result.get("plan_output")
                    else:
                        plan_details = get_recovery_plan(enhanced_event)

            # Fallback to RULES if plan generation failed
            if not plan_details:
                logger.warning("Plan generation failed, using RULES fallback")
                if "RULES_ENGINE" in self.frameworks:
                    rules_result = await asyncio.to_thread(
                        self.frameworks["RULES_ENGINE"].generate_plan, enhanced_event
                    )
                    plan_details = rules_result.get("plan_output")
                else:
                    # Last resort: use LLM client fallback
                    plan_details = get_recovery_plan(enhanced_event)

            if not plan_details:
                logger.error("Failed to generate recovery plan with all methods")
                return None

            # Add crisis context to plan
            plan_details["crisis_context"] = crisis_context
            plan_details["trigger_event_type"] = event_type
            plan_details["trigger_event_id"] = trigger_event.get("event_id")

            logger.info(f"✓ Recovery plan generated: {plan_details.get('plan_id')}")
            return plan_details

        except Exception as e:
            logger.error(f"Error generating recovery plan: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "method": "generate_recovery_plan"})
            return None

    async def _publish_recovery_plan(self, plan_details: Dict[str, Any], trigger_event: Dict[str, Any]) -> None:
        """Publish recovery.plan and system.action events."""
        try:
            sector_id = trigger_event.get("sector_id", "unknown")
            severity = trigger_event.get("severity", "info")

            # Publish recovery.plan event
            recovery_plan_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "coordinator-agent",
                "severity": severity,
                "sector_id": sector_id,
                "summary": f"Recovery plan {plan_details.get('plan_id')} generated",
                "correlation_id": trigger_event.get("correlation_id"),
                "details": plan_details,
            }

            await publish(RECOVERY_PLAN_TOPIC, recovery_plan_event)
            logger.info(f"Published recovery.plan: {plan_details.get('plan_id')}")
            capture_published_event(
                RECOVERY_PLAN_TOPIC,
                recovery_plan_event["event_id"],
                {"plan_id": plan_details.get("plan_id"), "mode": RECOVERY_MODE},
            )

            # Publish system.action event
            system_action_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "coordinator-agent",
                "severity": Severity.INFO.value,
                "sector_id": sector_id,
                "summary": f"System executing recovery plan: {plan_details.get('plan_name')}",
                "correlation_id": trigger_event.get("correlation_id"),
                "details": {
                    "action_type": "execute_recovery_plan",
                    "plan_id": plan_details.get("plan_id"),
                    "plan_name": plan_details.get("plan_name"),
                    "executor": "coordinator-agent",
                    "recovery_mode": RECOVERY_MODE,
                    "status": "executing",
                    "related_events": [trigger_event.get("event_id")],
                },
            }

            await publish(SYSTEM_ACTION_TOPIC, system_action_event)
            logger.info(f"Published system.action for plan: {plan_details.get('plan_id')}")
            capture_published_event(
                SYSTEM_ACTION_TOPIC,
                system_action_event["event_id"],
                {"plan_id": plan_details.get("plan_id"), "action_type": "execute_recovery_plan"},
            )

        except Exception as e:
            logger.error(f"Error publishing recovery plan events: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "method": "publish_recovery_plan"})

    async def _handle_power_failure(self, topic: str, payload: dict) -> None:
        """Handle power.failure events."""
        try:
            event_id = payload.get("event_id")
            sector_id = payload.get("sector_id")
            capture_received_event(topic, event_id, {"sector_id": sector_id, "severity": payload.get("severity")})

            logger.info("=" * 80)
            logger.info("POWER FAILURE EVENT RECEIVED")
            logger.info("=" * 80)
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Sector: {sector_id}")
            logger.info(f"Severity: {payload.get('severity')}")
            logger.info("=" * 80)

            # Update crisis context
            self._update_power_state(payload)
            self._update_priorities(payload)

            # Check if recovery plan should be triggered
            if self._should_trigger_recovery_plan(payload, "power_failure"):
                logger.info("Triggering recovery plan generation...")
                plan_details = await self._generate_recovery_plan(payload, "power_failure")
                if plan_details:
                    await self._publish_recovery_plan(plan_details, payload)
                else:
                    logger.warning("Recovery plan generation failed")

        except Exception as e:
            logger.error(f"Error handling power failure: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "event_type": "power_failure"})

    async def _handle_airspace_conflict(self, topic: str, payload: dict) -> None:
        """Handle airspace.conflict.detected events."""
        try:
            event_id = payload.get("event_id")
            capture_received_event(topic, event_id, {"severity": payload.get("severity")})

            logger.info("=" * 80)
            logger.info("AIRSPACE CONFLICT DETECTED")
            logger.info("=" * 80)
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Conflict ID: {payload.get('details', {}).get('conflict_id')}")
            logger.info(f"Severity: {payload.get('severity')}")
            logger.info(f"Autonomy Mode: {AUTONOMY_MODE}")
            logger.info("=" * 80)

            # Update crisis context
            self._update_airspace_state(payload, "conflict")
            self._update_priorities(payload)

            # Generate solution based on AUTONOMY_MODE
            conflict_details = payload.get("details", {})
            if AUTONOMY_MODE == "AGENTIC":
                # Publish task for deconflict agent
                await self._publish_deconflict_task(payload)
            else:
                # Generate solution directly (RULES or LLM)
                solutions = await self._generate_airspace_solutions([conflict_details], [], [])
                for solution in solutions:
                    solution_event = self._create_solution_event(
                        solution, payload.get("sector_id", "airspace-sector-1"), payload.get("correlation_id")
                    )
                    await publish(AIRSPACE_SOLUTION_PROPOSED_TOPIC, solution_event)
                    logger.info(f"Published solution: {solution.get('solution_id')}")

            # Check if recovery plan should be triggered
            if self._should_trigger_recovery_plan(payload, "airspace_conflict"):
                logger.info("Triggering recovery plan generation...")
                plan_details = await self._generate_recovery_plan(payload, "airspace_conflict")
                if plan_details:
                    await self._publish_recovery_plan(plan_details, payload)
                else:
                    logger.warning("Recovery plan generation failed")

        except Exception as e:
            logger.error(f"Error handling airspace conflict: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "event_type": "airspace_conflict"})

    async def _handle_airspace_hotspot(self, topic: str, payload: dict) -> None:
        """Handle airspace.hotspot.detected events."""
        try:
            event_id = payload.get("event_id")
            capture_received_event(topic, event_id, {"severity": payload.get("severity")})

            logger.info("=" * 80)
            logger.info("AIRSPACE HOTSPOT DETECTED")
            logger.info("=" * 80)
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Hotspot ID: {payload.get('details', {}).get('hotspot_id')}")
            logger.info(f"Severity: {payload.get('severity')}")
            logger.info(f"Autonomy Mode: {AUTONOMY_MODE}")
            logger.info("=" * 80)

            # Update crisis context
            self._update_airspace_state(payload, "hotspot")
            self._update_priorities(payload)

            # Generate solution based on AUTONOMY_MODE
            hotspot_details = payload.get("details", {})
            if AUTONOMY_MODE == "AGENTIC":
                # Publish task for hotspot agent
                await self._publish_hotspot_task(payload)
            else:
                # Generate solution directly (RULES or LLM)
                solutions = await self._generate_airspace_solutions([], [hotspot_details], [])
                for solution in solutions:
                    solution_event = self._create_solution_event(
                        solution, payload.get("sector_id", "airspace-sector-1"), payload.get("correlation_id")
                    )
                    await publish(AIRSPACE_SOLUTION_PROPOSED_TOPIC, solution_event)
                    logger.info(f"Published solution: {solution.get('solution_id')}")

        except Exception as e:
            logger.error(f"Error handling airspace hotspot: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "event_type": "airspace_hotspot"})
    
    async def _generate_airspace_solutions(
        self,
        conflicts: List[Dict[str, Any]],
        hotspots: List[Dict[str, Any]],
        trajectories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate airspace solutions based on AUTONOMY_MODE.

        Args:
            conflicts: List of conflict objects
            hotspots: List of hotspot objects
            trajectories: List of flight trajectories

        Returns:
            List of solution dictionaries
        """
        if AUTONOMY_MODE == "RULES":
            # Run in thread pool since it's synchronous
            return await asyncio.to_thread(generate_solutions_rules, conflicts, hotspots, trajectories)
        elif AUTONOMY_MODE == "LLM":
            # Run in thread pool since it's synchronous (but may call async LLM internally)
            return await asyncio.to_thread(generate_solutions_llm, conflicts, hotspots, trajectories)
        else:
            # Fallback to RULES
            logger.warning(f"Unknown AUTONOMY_MODE: {AUTONOMY_MODE}, using RULES")
            return await asyncio.to_thread(generate_solutions_rules, conflicts, hotspots, trajectories)

    async def _publish_deconflict_task(self, conflict_event: Dict[str, Any]) -> None:
        """Publish deconflict task for AGENTIC mode."""
        try:
            task_id = f"TASK-DECONF-{str(uuid4())[:8].upper()}"
            conflict_details = conflict_event.get("details", {})

            task_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "coordinator-agent",
                "severity": Severity.INFO.value,
                "sector_id": conflict_event.get("sector_id", "airspace-sector-1"),
                "summary": f"Deconflict task {task_id} for conflict {conflict_details.get('conflict_id')}",
                "correlation_id": conflict_event.get("correlation_id"),
                "details": {
                    "task_id": task_id,
                    "task_type": "deconflict",
                    "conflict": conflict_details,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                },
            }

            await publish(TASK_AIRSPACE_DECONFLICT_TOPIC, task_event)
            logger.info(f"Published deconflict task: {task_id}")

            # Track task
            self.active_tasks[task_id] = {
                "task_type": "deconflict",
                "conflict": conflict_details,
                "created_at": datetime.utcnow(),
            }
            self.pending_partial_solutions[task_id] = []

            capture_published_event(
                TASK_AIRSPACE_DECONFLICT_TOPIC,
                task_event["event_id"],
                {"task_id": task_id, "conflict_id": conflict_details.get("conflict_id")},
            )

        except Exception as e:
            logger.error(f"Error publishing deconflict task: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "method": "publish_deconflict_task"})

    async def _publish_hotspot_task(self, hotspot_event: Dict[str, Any]) -> None:
        """Publish hotspot mitigation task for AGENTIC mode."""
        try:
            task_id = f"TASK-HOTSPOT-{str(uuid4())[:8].upper()}"
            hotspot_details = hotspot_event.get("details", {})

            task_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "coordinator-agent",
                "severity": Severity.INFO.value,
                "sector_id": hotspot_event.get("sector_id", "airspace-sector-1"),
                "summary": f"Hotspot mitigation task {task_id} for hotspot {hotspot_details.get('hotspot_id')}",
                "correlation_id": hotspot_event.get("correlation_id"),
                "details": {
                    "task_id": task_id,
                    "task_type": "hotspot_mitigation",
                    "hotspot": hotspot_details,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                },
            }

            await publish(TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC, task_event)
            logger.info(f"Published hotspot task: {task_id}")

            # Track task
            self.active_tasks[task_id] = {
                "task_type": "hotspot_mitigation",
                "hotspot": hotspot_details,
                "created_at": datetime.utcnow(),
            }
            self.pending_partial_solutions[task_id] = []

            capture_published_event(
                TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC,
                task_event["event_id"],
                {"task_id": task_id, "hotspot_id": hotspot_details.get("hotspot_id")},
            )

        except Exception as e:
            logger.error(f"Error publishing hotspot task: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "method": "publish_hotspot_task"})

    async def _handle_partial_solution(self, topic: str, payload: dict) -> None:
        """Handle partial solution from task agents and merge into complete solution."""
        try:
            partial_solution = payload.get("details", {})
            task_id = partial_solution.get("task_id")
            correlation_id = payload.get("correlation_id")

            capture_received_event(topic, payload.get("event_id", "unknown"), {"task_id": task_id})

            logger.info("=" * 80)
            logger.info("PARTIAL SOLUTION RECEIVED")
            logger.info("=" * 80)
            logger.info(f"Task ID: {task_id}")
            logger.info(f"Solution Type: {partial_solution.get('solution_type')}")
            logger.info(f"Agent: {partial_solution.get('agent_name')}")
            logger.info("=" * 80)

            if task_id not in self.pending_partial_solutions:
                logger.warning(f"Received partial solution for unknown task: {task_id}")
                return

            # Add partial solution
            self.pending_partial_solutions[task_id].append(partial_solution)

            # Check if we have enough partial solutions to merge
            task_info = self.active_tasks.get(task_id, {})
            task_type = task_info.get("task_type")

            # Wait a bit for more partial solutions, then merge
            await asyncio.sleep(2)  # Wait 2 seconds for other agents

            # Merge partial solutions into complete solution
            await self._merge_partial_solutions(task_id, correlation_id)

        except Exception as e:
            logger.error(f"Error handling partial solution: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "event_type": "partial_solution"})

    async def _merge_partial_solutions(self, task_id: str, correlation_id: Optional[str]) -> None:
        """Merge partial solutions into a complete solution."""
        try:
            if task_id not in self.pending_partial_solutions:
                return

            partial_solutions = self.pending_partial_solutions[task_id]
            if len(partial_solutions) == 0:
                return

            task_info = self.active_tasks.get(task_id, {})
            task_type = task_info.get("task_type")

            # Merge all proposed actions
            all_proposed_actions = []
            affected_flights = set()
            problem_id = None

            for partial in partial_solutions:
                all_proposed_actions.extend(partial.get("proposed_actions", []))
                affected_flights.update(partial.get("affected_flights", []))
                if not problem_id:
                    problem_id = partial.get("problem_id")

            # Calculate combined impact
            total_delay = sum(a.get("delay_minutes", 0) for a in all_proposed_actions)
            total_passengers = len(affected_flights) * 150  # Estimate

            # Create merged solution
            merged_solution = {
                "solution_id": f"SOL-MERGED-{str(uuid4())[:8].upper()}",
                "solution_type": "multi_action" if len(all_proposed_actions) > 1 else partial_solutions[0].get("solution_type"),
                "problem_id": problem_id,
                "affected_flights": list(affected_flights),
                "proposed_actions": all_proposed_actions,
                "estimated_impact": {
                    "total_delay_minutes": total_delay,
                    "fuel_impact_percent": 2.0,
                    "affected_passengers": total_passengers,
                },
                "confidence_score": sum(p.get("confidence_score", 0.5) for p in partial_solutions) / len(partial_solutions),
                "generated_by": "coordinator-agent-merged",
                "requires_approval": True,
                "partial_solutions": [p.get("agent_name") for p in partial_solutions],
            }

            # Publish merged solution
            solution_event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "coordinator-agent",
                "severity": Severity.INFO.value,
                "sector_id": "airspace-sector-1",
                "summary": f"Merged solution {merged_solution['solution_id']} from {len(partial_solutions)} partial solutions",
                "correlation_id": correlation_id,
                "details": merged_solution,
            }

            await publish(AIRSPACE_SOLUTION_PROPOSED_TOPIC, solution_event)
            logger.info(f"Published merged solution: {merged_solution['solution_id']}")
            capture_published_event(
                AIRSPACE_SOLUTION_PROPOSED_TOPIC,
                solution_event["event_id"],
                {"solution_id": merged_solution["solution_id"], "task_id": task_id},
            )

            # Clean up
            del self.pending_partial_solutions[task_id]
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

        except Exception as e:
            logger.error(f"Error merging partial solutions: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "method": "merge_partial_solutions", "task_id": task_id})

    def _create_solution_event(
        self,
        solution: Dict[str, Any],
        sector_id: str,
        correlation_id: Optional[str],
    ) -> Dict[str, Any]:
        """Create an airspace.solution.proposed event."""
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "coordinator-agent",
            "severity": Severity.INFO.value,
            "sector_id": sector_id,
            "summary": f"Solution {solution.get('solution_id')} proposed",
            "correlation_id": correlation_id,
            "details": solution,
        }

    async def _handle_airspace_solution(self, topic: str, payload: dict) -> None:
        """Handle airspace.solution.proposed events and apply in demo mode."""
        try:
            event_id = payload.get("event_id")
            solution_details = payload.get("details", {})
            solution_id = solution_details.get("solution_id")

            capture_received_event(topic, event_id, {"solution_id": solution_id})

            logger.info("=" * 80)
            logger.info("AIRSPACE SOLUTION PROPOSED")
            logger.info("=" * 80)
            logger.info(f"Solution ID: {solution_id}")
            logger.info(f"Solution Type: {solution_details.get('solution_type')}")
            logger.info("=" * 80)

            # In demo mode, automatically apply solutions
            demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
            if demo_mode and solution_id:
                # Store solution as applied
                self.applied_solutions[solution_id] = {
                    "solution_id": solution_id,
                    "applied_at": datetime.utcnow().isoformat() + "Z",
                    "solution_details": solution_details,
                }

                # Publish airspace.mitigation.applied event
                mitigation_event = {
                    "event_id": str(uuid4()),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "coordinator-agent",
                    "severity": Severity.INFO.value,
                    "sector_id": payload.get("sector_id", "airspace-sector-1"),
                    "summary": f"Airspace mitigation applied: {solution_id}",
                    "correlation_id": payload.get("correlation_id"),
                    "details": {
                        "mitigation_id": f"MIT-{str(uuid4())[:8].upper()}",
                        "solution_id": solution_id,
                        "solution_type": solution_details.get("solution_type"),
                        "applied_at": datetime.utcnow().isoformat() + "Z",
                        "applied_by": "coordinator-agent",
                        "demo_mode": True,
                        "affected_flights": solution_details.get("affected_flights", []),
                        "proposed_actions": solution_details.get("proposed_actions", []),
                    },
                }

                await publish(AIRSPACE_MITIGATION_APPLIED_TOPIC, mitigation_event)
                logger.info(f"Published airspace.mitigation.applied: {solution_id}")
                capture_published_event(
                    AIRSPACE_MITIGATION_APPLIED_TOPIC,
                    mitigation_event["event_id"],
                    {"solution_id": solution_id, "demo_mode": True},
                )

        except Exception as e:
            logger.error(f"Error handling airspace solution: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "event_type": "airspace_solution"})

    async def run(self) -> None:
        """Run the coordinator agent service."""
        # Initialize Sentry
        autonomy_mode = os.getenv("SELECTED_FRAMEWORK", "AGENTIC_MESH")
        init_sentry("coordinator_agent", autonomy_mode)
        capture_startup("coordinator_agent", {
            "service_type": "coordinator",
            "enabled_frameworks": list(self.frameworks.keys()),
            "selected_framework": self.selected_framework,
            "recovery_mode": RECOVERY_MODE,
            "autonomy_mode": AUTONOMY_MODE,
        })

        logger.info("=" * 80)
        logger.info("COORDINATOR AGENT")
        logger.info("=" * 80)
        logger.info("Configuration:")
        logger.info(f"  Enabled Frameworks: {list(self.frameworks.keys())}")
        logger.info(f"  Selected Framework: {self.selected_framework}")
        logger.info(f"  Recovery Mode: {RECOVERY_MODE}")
        logger.info(f"  Autonomy Mode: {AUTONOMY_MODE}")
        logger.info("=" * 80)
        logger.info("Subscribed Topics:")
        logger.info(f"  - {POWER_FAILURE_TOPIC}")
        logger.info(f"  - {AIRSPACE_CONFLICT_DETECTED_TOPIC}")
        logger.info(f"  - {AIRSPACE_HOTSPOT_DETECTED_TOPIC}")
        logger.info(f"  - {AIRSPACE_SOLUTION_PROPOSED_TOPIC}")
        logger.info("=" * 80)

        try:
            # Connect to message broker
            logger.info("Connecting to message broker...")
            broker = await get_broker()
            logger.info("Connected to message broker")

            # Subscribe to events
            await subscribe(POWER_FAILURE_TOPIC, self._handle_power_failure)
            logger.info(f"Subscribed to: {POWER_FAILURE_TOPIC}")

            await subscribe(AIRSPACE_CONFLICT_DETECTED_TOPIC, self._handle_airspace_conflict)
            logger.info(f"Subscribed to: {AIRSPACE_CONFLICT_DETECTED_TOPIC}")

            await subscribe(AIRSPACE_HOTSPOT_DETECTED_TOPIC, self._handle_airspace_hotspot)
            logger.info(f"Subscribed to: {AIRSPACE_HOTSPOT_DETECTED_TOPIC}")

            await subscribe(AIRSPACE_SOLUTION_PROPOSED_TOPIC, self._handle_airspace_solution)
            logger.info(f"Subscribed to: {AIRSPACE_SOLUTION_PROPOSED_TOPIC}")

            # Subscribe to partial solutions if in AGENTIC mode
            if AUTONOMY_MODE == "AGENTIC":
                await subscribe(TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC, self._handle_partial_solution)
                logger.info(f"Subscribed to: {TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC}")

            logger.info("=" * 80)
            logger.info("Coordinator Agent is running. Waiting for events...")
            logger.info("=" * 80)

            # Keep running
            try:
                await asyncio.Event().wait()  # Wait indefinitely
            except asyncio.CancelledError:
                logger.info("Service cancelled")

            # Disconnect from broker
            await broker.disconnect()
            logger.info("Disconnected from message broker")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            capture_exception(e, {"service": "coordinator_agent", "error_type": "fatal"})
            raise

        logger.info("Coordinator Agent stopped")


async def main() -> None:
    """Main entry point for the coordinator agent service."""
    coordinator = CoordinatorAgent()
    await coordinator.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)
