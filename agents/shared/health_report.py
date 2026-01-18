"""
Startup Health Report Module

Provides a comprehensive health summary at service startup showing:
- Broker backend status
- Planner provider status
- Voice output status
- Audit logging status
- Map terrain status
- Observability status
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_planner_provider() -> str:
    """
    Determine which planner provider is active.
    
    Returns:
        "rules" | "gemini" | "cerebras"
    """
    cerebras_key = os.getenv("LLM_SERVICE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if cerebras_key:
        return "cerebras"
    elif gemini_key:
        return "gemini"
    else:
        return "rules"


def get_voice_output() -> str:
    """
    Determine which voice output is active.
    
    Returns:
        "elevenlabs" | "browser" | "console"
    """
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    
    if elevenlabs_key:
        return "elevenlabs"
    else:
        # Browser Web Speech API is always available in dashboard
        # Console is fallback for Python agents
        return "console"  # For Python agents, browser is handled separately


def get_audit_logging() -> str:
    """
    Determine which audit logging is active.
    
    Returns:
        "solana" | "local"
    """
    solana_rpc = os.getenv("SOLANA_RPC_URL")
    solana_key = os.getenv("SOLANA_PRIVATE_KEY")
    
    if solana_rpc and solana_key:
        return "solana"
    else:
        return "local"


def get_map_terrain() -> str:
    """
    Determine if map terrain is enabled.
    
    Returns:
        "enabled" | "disabled"
    """
    cesium_token = os.getenv("NEXT_PUBLIC_CESIUM_ION_TOKEN")
    
    if cesium_token:
        return "enabled"
    else:
        return "disabled"


def get_observability() -> str:
    """
    Determine if observability (Sentry) is enabled.
    
    Returns:
        "enabled" | "disabled"
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    if sentry_dsn:
        return "enabled"
    else:
        return "disabled"


def get_broker_backend_status() -> str:
    """
    Get broker backend status.
    
    Returns:
        "nats" | "solace"
    """
    from .config import get_broker_backend
    return get_broker_backend()


def print_startup_health_report(service_name: str) -> None:
    """
    Print a comprehensive startup health report.
    
    Args:
        service_name: Name of the service starting up
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("STARTUP HEALTH REPORT")
    logger.info("=" * 70)
    logger.info(f"Service: {service_name}")
    logger.info("")
    logger.info("Configuration Status:")
    logger.info(f"  Broker Backend:     {get_broker_backend_status().upper()}")
    logger.info(f"  Planner Provider:   {get_planner_provider().upper()}")
    logger.info(f"  Voice Output:        {get_voice_output().upper()}")
    logger.info(f"  Audit Logging:      {get_audit_logging().upper()}")
    logger.info(f"  Map Terrain:        {get_map_terrain().upper()}")
    logger.info(f"  Observability:      {get_observability().upper()}")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")


def get_health_summary() -> Dict[str, Any]:
    """
    Get health summary as dictionary.
    
    Returns:
        Dictionary with health status for all components
    """
    return {
        "broker_backend": get_broker_backend_status(),
        "planner_provider": get_planner_provider(),
        "voice_output": get_voice_output(),
        "audit_logging": get_audit_logging(),
        "map_terrain": get_map_terrain(),
        "observability": get_observability(),
    }

