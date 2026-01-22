"""
Event topic constants for Project Chronos.

All event topics are defined here in one place for consistency and easy reference.
"""

# Power domain topics
POWER_FAILURE_TOPIC = "chronos.events.power.failure"
RECOVERY_PLAN_TOPIC = "chronos.events.recovery.plan"

# Operator domain topics
OPERATOR_STATUS_TOPIC = "chronos.events.operator.status"

# Audit domain topics
AUDIT_DECISION_TOPIC = "chronos.events.audit.decision"

# Fix (audit + actuation) domain topics
FIX_PROPOSED_TOPIC = "chronos.events.fix.proposed"
FIX_REVIEW_REQUIRED_TOPIC = "chronos.events.fix.review_required"
FIX_APPROVED_TOPIC = "chronos.events.fix.approved"
FIX_REJECTED_TOPIC = "chronos.events.fix.rejected"
FIX_DEPLOY_REQUESTED_TOPIC = "chronos.events.fix.deploy_requested"
FIX_DEPLOY_STARTED_TOPIC = "chronos.events.fix.deploy_started"
FIX_DEPLOY_SUCCEEDED_TOPIC = "chronos.events.fix.deploy_succeeded"
FIX_DEPLOY_FAILED_TOPIC = "chronos.events.fix.deploy_failed"
FIX_VERIFIED_TOPIC = "chronos.events.fix.verified"
FIX_ROLLBACK_REQUESTED_TOPIC = "chronos.events.fix.rollback_requested"
FIX_ROLLBACK_SUCCEEDED_TOPIC = "chronos.events.fix.rollback_succeeded"

# System domain topics
SYSTEM_ACTION_TOPIC = "chronos.events.system.action"
APPROVAL_REQUIRED_TOPIC = "chronos.events.approval.required"

# Agent domain topics
AGENT_COMPARE_TOPIC = "chronos.events.agent.compare"
AGENT_COMPARE_RESULT_TOPIC = "chronos.events.agent.compare.result"

# Airspace domain topics
AIRSPACE_PLAN_UPLOADED_TOPIC = "chronos.events.airspace.plan.uploaded"
AIRSPACE_AIRCRAFT_POSITION_TOPIC = "chronos.events.airspace.aircraft.position"
AIRSPACE_FLIGHT_PARSED_TOPIC = "chronos.events.airspace.flight.parsed"
AIRSPACE_TRAJECTORY_SAMPLED_TOPIC = "chronos.events.airspace.trajectory.sampled"
AIRSPACE_CONFLICT_DETECTED_TOPIC = "chronos.events.airspace.conflict.detected"
AIRSPACE_HOTSPOT_DETECTED_TOPIC = "chronos.events.airspace.hotspot.detected"
AIRSPACE_SOLUTION_PROPOSED_TOPIC = "chronos.events.airspace.solution.proposed"
AIRSPACE_REPORT_READY_TOPIC = "chronos.events.airspace.report.ready"
AIRSPACE_MITIGATION_APPLIED_TOPIC = "chronos.events.airspace.mitigation.applied"

# Task domain topics (for AGENTIC mode)
TASK_AIRSPACE_DECONFLICT_TOPIC = "chronos.tasks.airspace.deconflict"
TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC = "chronos.tasks.airspace.hotspot_mitigation"
TASK_AIRSPACE_VALIDATION_FIX_TOPIC = "chronos.tasks.airspace.validation_fix"
TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC = "chronos.tasks.airspace.partial_solution"

# Geospatial domain topics
GEO_INCIDENT_TOPIC = "chronos.events.geo.incident"
GEO_RISK_AREA_TOPIC = "chronos.events.geo.risk_area"

# Transit domain topics (OC Transpo)
TRANSIT_GTFSRT_FETCH_STARTED_TOPIC = "chronos.events.transit.gtfsrt.fetch.started"
TRANSIT_VEHICLE_POSITION_TOPIC = "chronos.events.transit.vehicle.position"
TRANSIT_TRIP_UPDATE_TOPIC = "chronos.events.transit.trip.update"
TRANSIT_DISRUPTION_RISK_TOPIC = "chronos.events.transit.disruption.risk"
TRANSIT_HOTSPOT_TOPIC = "chronos.events.transit.hotspot"
TRANSIT_REPORT_READY_TOPIC = "chronos.events.transit.report.ready"
TRANSIT_MITIGATION_APPLIED_TOPIC = "chronos.events.transit.mitigation.applied"

# Defense domain topics
DEFENSE_THREAT_DETECTED_TOPIC = "chronos.events.defense.threat.detected"
DEFENSE_THREAT_ASSESSED_TOPIC = "chronos.events.defense.threat.assessed"
DEFENSE_THREAT_ESCALATED_TOPIC = "chronos.events.defense.threat.escalated"
DEFENSE_POSTURE_CHANGED_TOPIC = "chronos.events.defense.posture.changed"
DEFENSE_ACTION_PROPOSED_TOPIC = "chronos.events.defense.action.proposed"
DEFENSE_ACTION_APPROVED_TOPIC = "chronos.events.defense.action.approved"
DEFENSE_ACTION_DEPLOYED_TOPIC = "chronos.events.defense.action.deployed"
DEFENSE_THREAT_RESOLVED_TOPIC = "chronos.events.defense.threat.resolved"

# Disclaimer banner text constants
DISCLAIMER_AIRSPACE = "SYNTHETIC / NOT FOR OPS"
DISCLAIMER_TRANSIT = "Transit data is informational only"
DISCLAIMER_DEFENSE = "Defense features are non-kinetic and informational only."

# All topics list (for subscription)
ALL_TOPICS = [
    POWER_FAILURE_TOPIC,
    RECOVERY_PLAN_TOPIC,
    OPERATOR_STATUS_TOPIC,
    AUDIT_DECISION_TOPIC,
    SYSTEM_ACTION_TOPIC,
    APPROVAL_REQUIRED_TOPIC,
    AGENT_COMPARE_TOPIC,
    AGENT_COMPARE_RESULT_TOPIC,
    AIRSPACE_PLAN_UPLOADED_TOPIC,
    AIRSPACE_AIRCRAFT_POSITION_TOPIC,
    AIRSPACE_FLIGHT_PARSED_TOPIC,
    AIRSPACE_TRAJECTORY_SAMPLED_TOPIC,
    AIRSPACE_CONFLICT_DETECTED_TOPIC,
    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
    AIRSPACE_SOLUTION_PROPOSED_TOPIC,
    AIRSPACE_REPORT_READY_TOPIC,
    AIRSPACE_MITIGATION_APPLIED_TOPIC,
    TASK_AIRSPACE_DECONFLICT_TOPIC,
    TASK_AIRSPACE_HOTSPOT_MITIGATION_TOPIC,
    TASK_AIRSPACE_VALIDATION_FIX_TOPIC,
    TASK_AIRSPACE_PARTIAL_SOLUTION_TOPIC,
    GEO_INCIDENT_TOPIC,
    GEO_RISK_AREA_TOPIC,
    TRANSIT_GTFSRT_FETCH_STARTED_TOPIC,
    TRANSIT_VEHICLE_POSITION_TOPIC,
    TRANSIT_TRIP_UPDATE_TOPIC,
    TRANSIT_DISRUPTION_RISK_TOPIC,
    TRANSIT_HOTSPOT_TOPIC,
    TRANSIT_REPORT_READY_TOPIC,
    TRANSIT_MITIGATION_APPLIED_TOPIC,
    FIX_PROPOSED_TOPIC,
    FIX_REVIEW_REQUIRED_TOPIC,
    FIX_APPROVED_TOPIC,
    FIX_REJECTED_TOPIC,
    FIX_DEPLOY_REQUESTED_TOPIC,
    FIX_DEPLOY_STARTED_TOPIC,
    FIX_DEPLOY_SUCCEEDED_TOPIC,
    FIX_DEPLOY_FAILED_TOPIC,
    FIX_VERIFIED_TOPIC,
    FIX_ROLLBACK_REQUESTED_TOPIC,
    FIX_ROLLBACK_SUCCEEDED_TOPIC,
    DEFENSE_THREAT_DETECTED_TOPIC,
    DEFENSE_THREAT_ASSESSED_TOPIC,
    DEFENSE_THREAT_ESCALATED_TOPIC,
    DEFENSE_POSTURE_CHANGED_TOPIC,
    DEFENSE_ACTION_PROPOSED_TOPIC,
    DEFENSE_ACTION_APPROVED_TOPIC,
    DEFENSE_ACTION_DEPLOYED_TOPIC,
    DEFENSE_THREAT_RESOLVED_TOPIC,
]

