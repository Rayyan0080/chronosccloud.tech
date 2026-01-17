"""
Sentry observability integration for Project Chronos agents.

Provides centralized Sentry initialization and helper functions for logging.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env from project root (2 levels up from agents/shared/)
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip

logger = logging.getLogger(__name__)

_sentry_initialized = False
_service_name: Optional[str] = None


def init_sentry(service_name: str, autonomy_mode: Optional[str] = None) -> None:
    """
    Initialize Sentry for the service.

    Args:
        service_name: Name of the service (e.g., "crisis_generator", "coordinator_agent")
        autonomy_mode: Optional autonomy mode (e.g., "NORMAL", "HIGH")
    """
    global _sentry_initialized, _service_name

    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        logger.info("SENTRY_DSN not set, skipping Sentry initialization")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Configure Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
            release=os.getenv("SENTRY_RELEASE", "unknown"),
            send_default_pii=True,  # Add data like request headers and IP for users
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR,  # Send errors as events
                ),
            ],
        )

        # Set service tags
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("service_name", service_name)
            if autonomy_mode:
                scope.set_tag("autonomy_mode", autonomy_mode)

        _sentry_initialized = True
        _service_name = service_name

        logger.info("=" * 60)
        logger.info("SENTRY INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"Service: {service_name}")
        logger.info(f"Environment: {os.getenv('SENTRY_ENVIRONMENT', 'development')}")
        if autonomy_mode:
            logger.info(f"Autonomy Mode: {autonomy_mode}")
        logger.info("=" * 60)

    except ImportError:
        logger.warning("sentry-sdk not installed. Install with: pip install sentry-sdk")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)


def capture_startup(service_name: str, additional_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture service startup event.

    Args:
        service_name: Name of the service
        additional_data: Optional additional context data
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("event_type", "startup")
            if additional_data:
                for key, value in additional_data.items():
                    scope.set_extra(key, value)

        sentry_sdk.capture_message(
            f"Service {service_name} started",
            level="info",
        )

        logger.debug(f"Sentry: Captured startup for {service_name}")

    except Exception as e:
        logger.warning(f"Failed to capture startup to Sentry: {e}")


def capture_received_event(topic: str, event_id: str, additional_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture received event.

    Args:
        topic: Event topic
        event_id: Event ID
        additional_data: Optional additional context data
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("event_type", "received_event")
            scope.set_tag("event_topic", topic)
            scope.set_extra("event_id", event_id)
            if additional_data:
                for key, value in additional_data.items():
                    scope.set_extra(key, value)

        sentry_sdk.capture_message(
            f"Received event: {topic}",
            level="info",
        )

        logger.debug(f"Sentry: Captured received event {topic} ({event_id})")

    except Exception as e:
        logger.warning(f"Failed to capture received event to Sentry: {e}")


def capture_published_event(topic: str, event_id: str, additional_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture published event.

    Args:
        topic: Event topic
        event_id: Event ID
        additional_data: Optional additional context data
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("event_type", "published_event")
            scope.set_tag("event_topic", topic)
            scope.set_extra("event_id", event_id)
            if additional_data:
                for key, value in additional_data.items():
                    scope.set_extra(key, value)

        sentry_sdk.capture_message(
            f"Published event: {topic}",
            level="info",
        )

        logger.debug(f"Sentry: Captured published event {topic} ({event_id})")

    except Exception as e:
        logger.warning(f"Failed to capture published event to Sentry: {e}")


def capture_exception(error: Exception, additional_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture exception.

    Args:
        error: Exception to capture
        additional_data: Optional additional context data (will be redacted if contains large lists)
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        # Redact large lists from additional_data to avoid logging entire flight lists
        redacted_data = _redact_large_lists(additional_data) if additional_data else None

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("event_type", "exception")
            if redacted_data:
                for key, value in redacted_data.items():
                    scope.set_extra(key, value)

        sentry_sdk.capture_exception(error)

        logger.debug(f"Sentry: Captured exception: {type(error).__name__}")

    except Exception as e:
        logger.warning(f"Failed to capture exception to Sentry: {e}")


def add_breadcrumb(message: str, category: str, level: str = "info", data: Optional[Dict[str, Any]] = None) -> None:
    """
    Add a breadcrumb to the current Sentry scope.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category (e.g., "topic.receive", "topic.publish")
        level: Breadcrumb level (info, warning, error)
        data: Optional additional data (will be redacted if contains large lists)
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        # Redact large lists from data
        redacted_data = _redact_large_lists(data) if data else None

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=redacted_data,
        )

        logger.debug(f"Sentry: Added breadcrumb: {category} - {message}")

    except Exception as e:
        logger.warning(f"Failed to add breadcrumb to Sentry: {e}")


def set_tag(key: str, value: str) -> None:
    """
    Set a tag on the current Sentry scope.

    Args:
        key: Tag key
        value: Tag value
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag(key, value)

        logger.debug(f"Sentry: Set tag {key}={value}")

    except Exception as e:
        logger.warning(f"Failed to set tag in Sentry: {e}")


def _redact_large_lists(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Redact large lists from data to avoid logging entire flight lists.

    Args:
        data: Dictionary that may contain large lists

    Returns:
        Dictionary with large lists replaced by summaries
    """
    if not data:
        return data

    redacted = {}
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 10:
            # Replace large lists with summary
            redacted[key] = f"[REDACTED: {len(value)} items]"
        elif isinstance(value, dict):
            # Recursively redact nested dictionaries
            redacted[key] = _redact_large_lists(value)
        else:
            redacted[key] = value

    return redacted


def is_initialized() -> bool:
    """Check if Sentry is initialized."""
    return _sentry_initialized


def get_service_name() -> Optional[str]:
    """Get the current service name."""
    return _service_name

