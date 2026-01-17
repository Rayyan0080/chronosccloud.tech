"""
Crisis Generator Service

Generates power failure events for testing and demonstration.
Publishes events every 5 seconds for random sectors, with manual trigger support.
"""

import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.schema import PowerFailureEvent, Severity
from agents.shared.sentry import init_sentry, capture_startup, capture_published_event, capture_exception

# Optional voice output
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from voice.elevenlabs_client import speak_power_failure
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False
    speak_power_failure = None
from agents.shared.sentry import init_sentry, capture_startup, capture_published_event, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Topic for power failure events
POWER_FAILURE_TOPIC = "chronos.events.power.failure"

# Sector IDs (1-3)
SECTORS = ["sector-1", "sector-2", "sector-3"]


def generate_power_failure_event(sector_id: str, is_manual: bool = False) -> dict:
    """
    Generate a power failure event for the given sector.

    Args:
        sector_id: Sector identifier (sector-1, sector-2, or sector-3)
        is_manual: Whether this is a manually triggered event

    Returns:
        Dictionary containing the power failure event
    """
    # Random severity (weighted towards warning/error for variety)
    severity_weights = {
        Severity.WARNING: 0.3,
        Severity.ERROR: 0.4,
        Severity.CRITICAL: 0.3,
    }
    severity = random.choices(
        list(severity_weights.keys()), weights=list(severity_weights.values())
    )[0]

    # Generate random voltage (0-50V for failures, normal is 120V/240V)
    voltage = random.uniform(0, 50)

    # Generate random load (0-100% of capacity)
    load = random.uniform(0, 100)

    # Random phase (or all phases for critical)
    if severity == Severity.CRITICAL:
        phase = "all"
        backup_status = random.choice(["failed", "active"])
    else:
        phase = random.choice(["phase-1", "phase-2", "phase-3"])
        backup_status = random.choice(["active", "degraded"])

    # Estimate restore time (1-4 hours from now)
    restore_hours = random.uniform(1, 4)
    estimated_restore_time = (datetime.utcnow() + timedelta(hours=restore_hours)).isoformat() + "Z"

    # Create summary
    if is_manual:
        summary = f"Manual power failure triggered for {sector_id}"
    else:
        summary = f"Power failure detected in {sector_id}"

    # Build event using schema
    event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "severity": severity.value,
        "sector_id": sector_id,
        "summary": summary,
        "details": {
            "voltage": round(voltage, 2),
            "load": round(load, 2),  # Load percentage
            "current": round(load * 0.1, 2),  # Estimated current based on load
            "phase": phase,
            "backup_status": backup_status,
            "estimated_restore_time": estimated_restore_time,
        },
    }

    return event


async def publish_power_failure(sector_id: str, is_manual: bool = False) -> None:
    """
    Generate and publish a power failure event.

    Args:
        sector_id: Sector identifier
        is_manual: Whether this is a manually triggered event
    """
    try:
        event = generate_power_failure_event(sector_id, is_manual)

        # Log event to console
        logger.info("=" * 60)
        logger.info("POWER FAILURE EVENT")
        logger.info("=" * 60)
        logger.info(f"Event ID: {event['event_id']}")
        logger.info(f"Timestamp: {event['timestamp']}")
        logger.info(f"Severity: {event['severity']}")
        logger.info(f"Sector: {event['sector_id']}")
        logger.info(f"Summary: {event['summary']}")
        logger.info("Details:")
        logger.info(f"  Voltage: {event['details']['voltage']}V")
        logger.info(f"  Load: {event['details']['load']}%")
        logger.info(f"  Current: {event['details']['current']}A")
        logger.info(f"  Phase: {event['details']['phase']}")
        logger.info(f"  Backup Status: {event['details']['backup_status']}")
        logger.info(f"  Estimated Restore: {event['details']['estimated_restore_time']}")
        logger.info("=" * 60)
        logger.info(f"Event JSON:\n{json.dumps(event, indent=2)}")
        logger.info("=" * 60)

        # Publish to message broker
        await publish(POWER_FAILURE_TOPIC, event)
        logger.info(f"Published to topic: {POWER_FAILURE_TOPIC}")
        
        # Voice announcement (optional)
        if VOICE_ENABLED and speak_power_failure:
            try:
                sector_id = event.get("sector_id", "unknown")
                severity = event.get("severity", "info")
                voltage = event.get("details", {}).get("voltage", 0)
                load = event.get("details", {}).get("load", 0)
                speak_power_failure(sector_id, severity, voltage, load)
            except Exception as e:
                logger.warning(f"Voice announcement failed: {e}")
        
        # Capture to Sentry
        capture_published_event(
            POWER_FAILURE_TOPIC,
            event.get("event_id", "unknown"),
            {
                "sector_id": event.get("sector_id"),
                "severity": event.get("severity"),
                "voltage": event.get("details", {}).get("voltage"),
                "load": event.get("details", {}).get("load"),
            }
        )

    except Exception as e:
        logger.error(f"Failed to publish power failure event: {e}", exc_info=True)
        capture_exception(e, {"service": "crisis_generator", "event_type": "publish_failure"})


async def keyboard_input_handler() -> None:
    """
    Handle keyboard input in a separate async task.
    Press 'f' to force a power failure, 'q' to quit.
    """
    loop = asyncio.get_event_loop()

    def read_input():
        """Read input from stdin (blocking)."""
        try:
            return sys.stdin.read(1)
        except (EOFError, KeyboardInterrupt):
            return None

    logger.info("Keyboard input handler started. Press 'f' to force failure, 'q' to quit")

    while True:
        try:
            # Read input asynchronously
            char = await loop.run_in_executor(None, read_input)
            if char is None:
                break

            char = char.lower().strip()

            if char == "f":
                # Force a power failure in a random sector
                sector = random.choice(SECTORS)
                logger.info(f"Manual trigger: Generating power failure for {sector}")
                await publish_power_failure(sector, is_manual=True)
            elif char == "q":
                logger.info("Quit requested. Shutting down...")
                break
            elif char:
                logger.info(f"Unknown command: '{char}'. Press 'f' to force failure, 'q' to quit")

        except Exception as e:
            logger.error(f"Error in keyboard input handler: {e}", exc_info=True)
            await asyncio.sleep(0.1)


async def periodic_event_generator(interval: int = 5) -> None:
    """
    Generate power failure events periodically.

    Args:
        interval: Interval in seconds between events (default: 5)
    """
    logger.info(f"Starting periodic event generator (interval: {interval}s)")

    while True:
        try:
            # Wait for the interval
            await asyncio.sleep(interval)

            # Select random sector
            sector = random.choice(SECTORS)

            # Generate and publish event
            await publish_power_failure(sector, is_manual=False)

        except asyncio.CancelledError:
            logger.info("Periodic event generator cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic event generator: {e}", exc_info=True)
            await asyncio.sleep(1)  # Brief pause before retry


async def main() -> None:
    """Main entry point for the crisis generator service."""
    # Initialize Sentry
    init_sentry("crisis_generator")
    capture_startup("crisis_generator", {"service_type": "event_generator"})
    
    logger.info("Starting Crisis Generator Service")
    logger.info("=" * 60)
    logger.info("Configuration:")
    logger.info(f"  Topic: {POWER_FAILURE_TOPIC}")
    logger.info(f"  Sectors: {', '.join(SECTORS)}")
    logger.info(f"  Auto-generate interval: 5 seconds")
    logger.info("=" * 60)

    try:
        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        logger.info("Connected to message broker")

        # Start periodic event generator
        periodic_task = asyncio.create_task(periodic_event_generator(interval=5))

        # Start keyboard input handler
        keyboard_task = asyncio.create_task(keyboard_input_handler())

        # Wait for either task to complete (keyboard handler will exit on 'q')
        done, pending = await asyncio.wait(
            [periodic_task, keyboard_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Disconnect from broker
        await broker.disconnect()
        logger.info("Disconnected from message broker")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        capture_exception(e, {"service": "crisis_generator", "error_type": "fatal"})
        sys.exit(1)

    logger.info("Crisis Generator Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

