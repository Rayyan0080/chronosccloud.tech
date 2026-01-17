"""
Trajectory Analyzer

Analyzes flight trajectories to detect conflicts, hotspots, violations, and generate solutions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


def analyze(
    flights: List[Dict[str, Any]],
    plan_window_seconds: int = 3600,
    sample_step_seconds: int = 60,
) -> Dict[str, Any]:
    """
    Analyze flight trajectories for conflicts, hotspots, violations, and solutions.

    Args:
        flights: List of flight records with trajectory data
        plan_window_seconds: Time window for analysis in seconds (default: 3600 = 1 hour)
        sample_step_seconds: Sampling interval in seconds (default: 60 = 1 minute)

    Returns:
        Dictionary containing:
        - conflicts: List of conflict objects
        - hotspots: List of hotspot objects
        - violations: List of violation objects
        - summary: Summary statistics
        - solutions: List of proposed solutions
    """
    logger.info(f"Analyzing {len(flights)} flights with window={plan_window_seconds}s, step={sample_step_seconds}s")

    conflicts = []
    hotspots = []
    violations = []
    solutions = []

    # Extract flight trajectories
    flight_trajectories = []
    for flight in flights:
        flight_id = flight.get("flight_id", f"FLT-{str(uuid4())[:8].upper()}")
        route = flight.get("route", [])
        departure_time = flight.get("departure_time")
        arrival_time = flight.get("arrival_time")
        altitude = flight.get("altitude", 35000)
        speed = flight.get("speed", 450)

        # Build trajectory points
        trajectory = {
            "flight_id": flight_id,
            "route": route,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "altitude": altitude,
            "speed": speed,
        }
        flight_trajectories.append(trajectory)

    # Detect conflicts (simplified: check for overlapping routes at similar times/altitudes)
    conflicts = _detect_conflicts(flight_trajectories, plan_window_seconds, sample_step_seconds)

    # Detect hotspots (areas with high flight density)
    hotspots = _detect_hotspots(flight_trajectories, plan_window_seconds)

    # Detect violations (altitude, speed, separation violations)
    violations = _detect_violations(flight_trajectories)

    # Generate solutions for conflicts and hotspots
    solutions = _generate_solutions(conflicts, hotspots, flight_trajectories)

    # Create summary
    summary = {
        "total_flights": len(flights),
        "conflicts_detected": len(conflicts),
        "hotspots_detected": len(hotspots),
        "violations_detected": len(violations),
        "solutions_proposed": len(solutions),
        "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
        "plan_window_seconds": plan_window_seconds,
        "sample_step_seconds": sample_step_seconds,
    }

    logger.info(
        f"Analysis complete: {len(conflicts)} conflicts, {len(hotspots)} hotspots, "
        f"{len(violations)} violations, {len(solutions)} solutions"
    )

    return {
        "conflicts": conflicts,
        "hotspots": hotspots,
        "violations": violations,
        "summary": summary,
        "solutions": solutions,
    }


def _detect_conflicts(
    trajectories: List[Dict[str, Any]],
    window_seconds: int,
    step_seconds: int,
) -> List[Dict[str, Any]]:
    """Detect conflicts between flight trajectories."""
    conflicts = []

    # Simple conflict detection: check pairs of flights
    for i, traj1 in enumerate(trajectories):
        for j, traj2 in enumerate(trajectories[i + 1 :], start=i + 1):
            flight_id_1 = traj1["flight_id"]
            flight_id_2 = traj2["flight_id"]

            # Check if flights have overlapping routes and similar altitudes
            route1 = traj1.get("route", [])
            route2 = traj2.get("route", [])
            alt1 = traj1.get("altitude", 0)
            alt2 = traj2.get("altitude", 0)

            # Simple overlap check: if routes share waypoints or are close
            has_overlap = _routes_overlap(route1, route2)
            altitude_proximity = abs(alt1 - alt2) < 2000  # Within 2000 feet
            
            # For demo: also detect conflicts if flights share origin/destination even with different altitudes
            shares_origin = route1 and route2 and route1[0] == route2[0]
            shares_destination = route1 and route2 and route1[-1] == route2[-1]

            if (has_overlap and altitude_proximity) or (shares_origin and altitude_proximity):
                # Check time overlap
                dep1 = _parse_time(traj1.get("departure_time"))
                arr1 = _parse_time(traj1.get("arrival_time"))
                dep2 = _parse_time(traj2.get("departure_time"))
                arr2 = _parse_time(traj2.get("arrival_time"))

                if dep1 and dep2:
                    # Check if time windows overlap (relaxed for demo - check departure times are close)
                    # For demo: consider it a conflict if departures are within 1 hour of each other
                    time_diff = abs((dep1 - dep2).total_seconds())
                    has_time_overlap = time_diff < 3600  # Within 1 hour
                    
                    if has_time_overlap:
                        # Conflict detected
                        conflict_id = f"CONF-{str(uuid4())[:8].upper()}"
                        conflict_time = max(dep1, dep2) if dep1 and dep2 else datetime.utcnow()

                        # Calculate minimum separation (simplified)
                        min_separation = abs(alt1 - alt2) / 6076.12  # Convert feet to nautical miles
                        required_separation = 5.0  # Standard separation requirement

                        severity = "high" if min_separation < 2.0 else "medium" if min_separation < 3.0 else "low"

                        conflicts.append({
                            "conflict_id": conflict_id,
                            "conflict_type": "separation",
                            "severity_level": severity,
                            "flight_ids": [flight_id_1, flight_id_2],
                            "conflict_location": {
                                "latitude": 39.8283,  # Synthetic location
                                "longitude": -98.5795,
                                "altitude": (alt1 + alt2) / 2,
                            },
                            "conflict_time": conflict_time.isoformat() + "Z",
                            "minimum_separation": round(min_separation, 2),
                            "required_separation": required_separation,
                            "conflict_duration": 120.0,  # Estimated duration
                            "detection_method": "trajectory-intersection",
                        })

    return conflicts


def _detect_hotspots(
    trajectories: List[Dict[str, Any]],
    window_seconds: int,
) -> List[Dict[str, Any]]:
    """Detect hotspots (high-density areas) in airspace."""
    hotspots = []

    if len(trajectories) < 2:
        return hotspots  # Need at least 2 flights for a hotspot (lowered for demo)

    # Group flights by approximate location (simplified: use route start/end)
    location_groups = {}
    for traj in trajectories:
        route = traj.get("route", [])
        if len(route) >= 2:
            # Use first waypoint as location key
            location_key = route[0]
            if location_key not in location_groups:
                location_groups[location_key] = []
            location_groups[location_key].append(traj)

    # Find locations with high density
    for location_key, trajs in location_groups.items():
        if len(trajs) >= 2:  # Hotspot threshold (lowered for demo - 2 flights from same origin)
            hotspot_id = f"HOTSPOT-{str(uuid4())[:8].upper()}"

            # Calculate time window
            departure_times = [_parse_time(t.get("departure_time")) for t in trajs]
            departure_times = [dt for dt in departure_times if dt]
            if not departure_times:
                continue

            start_time = min(departure_times)
            end_time = max(departure_times) + timedelta(seconds=window_seconds)

            affected_flights = [t["flight_id"] for t in trajs]
            density = len(trajs) / max(1, window_seconds / 3600)  # Flights per hour
            capacity_limit = 50  # Synthetic capacity
            current_count = len(trajs)

            severity = "high" if density > 0.8 else "medium" if density > 0.5 else "low"

            hotspots.append({
                "hotspot_id": hotspot_id,
                "hotspot_type": "congestion",
                "location": {
                    "latitude": 40.7128,  # Synthetic location
                    "longitude": -74.0060,
                    "altitude": 30000.0,
                    "radius_nm": 25.0,
                },
                "affected_flights": affected_flights,
                "severity": severity,
                "start_time": start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "density": round(density, 2),
                "capacity_limit": capacity_limit,
                "current_count": current_count,
                "description": f"High traffic congestion near {location_key}",
            })

    return hotspots


def _detect_violations(trajectories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect violations (altitude, speed, separation)."""
    violations = []

    for traj in trajectories:
        flight_id = traj.get("flight_id")
        altitude = traj.get("altitude", 0)
        speed = traj.get("speed", 0)

        # Check altitude violations (too low or too high)
        if altitude < 10000:
            violations.append({
                "violation_id": f"VIOL-{str(uuid4())[:8].upper()}",
                "flight_id": flight_id,
                "violation_type": "altitude",
                "severity": "warning",
                "description": f"Flight {flight_id} below minimum altitude",
                "value": altitude,
                "threshold": 10000,
            })

        # Check speed violations (too fast)
        if speed > 500:
            violations.append({
                "violation_id": f"VIOL-{str(uuid4())[:8].upper()}",
                "flight_id": flight_id,
                "violation_type": "speed",
                "severity": "warning",
                "description": f"Flight {flight_id} exceeds speed limit",
                "value": speed,
                "threshold": 500,
            })

    return violations


def _generate_solutions(
    conflicts: List[Dict[str, Any]],
    hotspots: List[Dict[str, Any]],
    trajectories: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate solutions for conflicts and hotspots."""
    solutions = []

    # Solutions for conflicts
    for conflict in conflicts:
        solution_id = f"SOL-{str(uuid4())[:8].upper()}"
        flight_ids = conflict.get("flight_ids", [])

        if len(flight_ids) >= 2:
            solutions.append({
                "solution_id": solution_id,
                "solution_type": "reroute",
                "problem_id": conflict.get("conflict_id"),
                "affected_flights": flight_ids,
                "proposed_actions": [
                    {
                        "flight_id": flight_ids[0],
                        "action": "reroute",
                        "new_waypoints": ["WAYPOINT1", "WAYPOINT2", "WAYPOINT3"],
                        "delay_minutes": 5,
                    },
                    {
                        "flight_id": flight_ids[1],
                        "action": "altitude_change",
                        "new_altitude": 37000,
                        "delay_minutes": 0,
                    },
                ],
                "estimated_impact": {
                    "total_delay_minutes": 5,
                    "fuel_impact_percent": 2.5,
                    "affected_passengers": 350,
                },
                "confidence_score": 0.87,
                "generated_by": "trajectory-insight-analyzer",
                "requires_approval": True,
            })

    # Solutions for hotspots
    for hotspot in hotspots:
        solution_id = f"SOL-{str(uuid4())[:8].upper()}"
        affected_flights = hotspot.get("affected_flights", [])

        if len(affected_flights) > 0:
            solutions.append({
                "solution_id": solution_id,
                "solution_type": "speed_adjustment",
                "problem_id": hotspot.get("hotspot_id"),
                "affected_flights": affected_flights[:3],  # Limit to first 3 flights
                "proposed_actions": [
                    {
                        "flight_id": flight_id,
                        "action": "speed_reduction",
                        "speed_change_knots": -20,
                        "delay_minutes": 3,
                    }
                    for flight_id in affected_flights[:3]
                ],
                "estimated_impact": {
                    "total_delay_minutes": 3,
                    "fuel_impact_percent": 1.2,
                    "affected_passengers": len(affected_flights) * 150,
                },
                "confidence_score": 0.75,
                "generated_by": "trajectory-insight-analyzer",
                "requires_approval": False,
            })

    return solutions


def _routes_overlap(route1: List[str], route2: List[str]) -> bool:
    """Check if two routes overlap (share waypoints or are close)."""
    if not route1 or not route2:
        return False

    # Check for shared waypoints
    set1 = set(route1)
    set2 = set(route2)
    if set1.intersection(set2):
        return True

    # Check if routes are adjacent (simplified heuristic)
    if len(route1) >= 2 and len(route2) >= 2:
        # If start/end points are close, consider overlap
        if route1[0] == route2[0] or route1[-1] == route2[-1]:
            return True

    return False


def _parse_time(time_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 time string to datetime."""
    if not time_str:
        return None

    try:
        # Handle both with and without Z
        if time_str.endswith("Z"):
            time_str = time_str[:-1] + "+00:00"
        return datetime.fromisoformat(time_str)
    except Exception:
        return None

