"""
Configuration management for agents service.

Handles environment variable loading and broker backend selection.
"""

import os
from typing import Optional


def get_broker_backend() -> str:
    """
    Get the message broker backend type from environment variable.
    Enforces a SINGLE active broker at runtime.
    
    CRITICAL: Only ONE broker backend can be active at a time.
    - If BROKER_BACKEND is explicitly set, use that (nats|solace)
    - If not set, auto-detects: Solace if SOLACE_HOST is set, otherwise NATS
    - If Solace connection fails, does NOT auto-fallback (must be explicit)

    Returns:
        Backend type: "nats" or "solace"

    Environment Variables:
        BROKER_BACKEND: Backend type ("nats" or "solace") - optional, auto-detected if not set
        SOLACE_HOST: If set and BROKER_BACKEND not set, will use Solace backend
    """
    # Check if explicitly set (PREFERRED - explicit configuration)
    backend = os.getenv("BROKER_BACKEND", "").lower().strip()
    
    if backend:
        if backend not in ["nats", "solace"]:
            raise ValueError(
                f"Invalid BROKER_BACKEND: {backend}. Must be 'nats' or 'solace'"
            )
        return backend
    
    # Auto-detect: if SOLACE_HOST is set, use Solace
    if os.getenv("SOLACE_HOST"):
        return "solace"
    
    # Default to NATS (most stable for demos)
    return "nats"


def get_nats_config() -> dict:
    """
    Get NATS connection configuration from environment variables.

    Returns:
        Dictionary with NATS connection parameters
    """
    return {
        "host": os.getenv("NATS_HOST", "localhost"),
        "port": int(os.getenv("NATS_PORT", "4222")),
    }


def get_solace_config() -> dict:
    """
    Get Solace PubSub+ connection configuration from environment variables.

    Returns:
        Dictionary with Solace connection parameters

    Environment Variables:
        SOLACE_HOST: Solace host (required for Solace backend)
        SOLACE_VPN: Solace VPN name (required)
        SOLACE_USERNAME: Solace username (required)
        SOLACE_PASSWORD: Solace password (required)
        SOLACE_PORT: Solace port (default: 55555)
    
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    host = os.getenv("SOLACE_HOST", "").strip()
    if not host:
        raise ValueError(
            "SOLACE_HOST environment variable is required for Solace backend. "
            "Get it from Solace Cloud console → Your Service → Connect tab."
        )
    
    # Strip protocol if included (tcp://, tcps://, etc.)
    # User might include protocol in SOLACE_HOST, but we handle that separately
    if "://" in host:
        # Extract just the hostname:port part
        host = host.split("://", 1)[1]  # Remove protocol prefix
    
    # Warn if host looks like a placeholder
    if "xxx" in host.lower():
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"⚠️  SOLACE_HOST contains 'xxx' placeholder: '{host}'. "
            "Please replace with your actual Solace Cloud hostname."
        )
    
    username = os.getenv("SOLACE_USERNAME") or os.getenv("SOLACE_USER")
    password = os.getenv("SOLACE_PASSWORD") or os.getenv("SOLACE_PASS")
    
    if not username:
        raise ValueError(
            "SOLACE_USERNAME (or SOLACE_USER) environment variable is required. "
            "Get it from Solace Cloud console → Your Service → Connect tab."
        )
    
    if not password:
        raise ValueError(
            "SOLACE_PASSWORD (or SOLACE_PASS) environment variable is required. "
            "Get it from Solace Cloud console → Your Service → Connect tab."
        )
    
    return {
        "host": host,
        "port": int(os.getenv("SOLACE_PORT", "55555")),
        "username": username,
        "password": password,
        "vpn": os.getenv("SOLACE_VPN", "default"),
    }


def get_mongodb_config() -> dict:
    """
    Get MongoDB connection configuration from environment variables.

    Returns:
        Dictionary with MongoDB connection parameters
    """
    return {
        "host": os.getenv("MONGO_HOST", "localhost"),
        "port": int(os.getenv("MONGO_PORT", "27017")),
        "username": os.getenv("MONGO_USER", "chronos"),
        "password": os.getenv("MONGO_PASS", "chronos"),
        "database": os.getenv("MONGO_DB", "chronos"),
    }


def get_log_level() -> str:
    """
    Get log level from environment variable.

    Returns:
        Log level string (default: "INFO")
    """
    return os.getenv("LOG_LEVEL", "INFO").upper()


def is_development() -> bool:
    """
    Check if running in development mode.

    Returns:
        True if NODE_ENV or PYTHON_ENV is "development"
    """
    node_env = os.getenv("NODE_ENV", "").lower()
    python_env = os.getenv("PYTHON_ENV", "").lower()
    return node_env == "development" or python_env == "development"

