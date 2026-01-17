"""
QNX Event Source Service

Reads newline-delimited JSON power events from stdin (piped from QNX grid simulator)
and publishes them as power.failure events to the message broker.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.schema import Severity
from agents.shared.sentry import init_sentry, capture_startup, capture_published_event, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Event topic
POWER_FAILURE_TOPIC = "chronos.events.power.failure"


async def process_qnx_event(qnx_data: dict) -> None:
    """
    Process a QNX power event and publish as power.failure event.

    Args:
        qnx_data: QNX event data with sector_id, voltage, load, timestamp, status
    """
    try:
        sector_id = qnx_data.get("sector_id", "unknown")
        voltage = qnx_data.get("voltage", 0.0)
        load = qnx_data.get("load", 0.0)
        status = qnx_data.get("status", "normal")

        # Determine severity based on voltage and status
        if status == "failure" or voltage < 10:
            severity = Severity.CRITICAL
        elif voltage < 50:
            severity = Severity.ERROR
        elif voltage < 90:
            severity = Severity.WARNING
        else:
            severity = Severity.INFO

        # Only publish failures or warnings (skip normal events)
        if severity in [Severity.INFO]:
            logger.debug(f"Skipping normal event for {sector_id} (voltage: {voltage}V)")
            return

        # Determine phase based on voltage level
        if voltage < 10:
            phase = "all"
        elif voltage < 50:
            phase = "partial"
        else:
            phase = "normal"

        # Build power failure event
        event = {
            "event_id": str(uuid4()),
            "timestamp": qnx_data.get("timestamp") or datetime.utcnow().isoformat() + "Z",
            "severity": severity.value,
            "sector_id": sector_id,
            "summary": f"Power event detected in {sector_id}: voltage {voltage}V, load {load}%",
            "details": {
                "voltage": round(voltage, 2),
                "load": round(load, 2),
                "current": round(load * 0.1, 2),  # Estimated current
                "phase": phase,
                "backup_status": "unknown",
                "source": "qnx-grid-simulator",
            },
        }

        # Log event
        logger.info("=" * 60)
        logger.info("QNX POWER EVENT RECEIVED")
        logger.info("=" * 60)
        logger.info(f"Sector: {sector_id}")
        logger.info(f"Voltage: {voltage}V")
        logger.info(f"Load: {load}%")
        logger.info(f"Status: {status}")
        logger.info(f"Severity: {severity.value}")
        logger.info("=" * 60)

        # Publish to message broker
        await publish(POWER_FAILURE_TOPIC, event)
        logger.info(f"Published to topic: {POWER_FAILURE_TOPIC}")

    except Exception as e:
        logger.error(f"Error processing QNX event: {e}", exc_info=True)


async def read_stdin_events() -> None:
    """
    Read newline-delimited JSON events from stdin and process them.
    """
    logger.info("Reading QNX events from stdin...")
    logger.info("Waiting for newline-delimited JSON events...")

    try:
        loop = asyncio.get_event_loop()
        
        while True:
            # Read line from stdin (blocking, run in executor)
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")
                break

            if not line:
                # EOF reached
                logger.info("EOF reached, exiting")
                break

            line = line.strip()
            if not line:
                continue

            try:
                # Parse JSON
                qnx_data = json.loads(line)
                logger.debug(f"Received QNX event: {qnx_data}")

                # Process event
                await process_qnx_event(qnx_data)

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received: {line[:100]}... Error: {e}")
            except Exception as e:
                logger.error(f"Error processing line: {e}", exc_info=True)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error reading from stdin: {e}", exc_info=True)


async def main() -> None:
    """Main entry point for the QNX event source service."""
    logger.info("Starting QNX Event Source Service")
    logger.info("=" * 60)
    logger.info("Configuration:")
    logger.info(f"  Input: stdin (newline-delimited JSON)")
    logger.info(f"  Output Topic: {POWER_FAILURE_TOPIC}")
    logger.info("=" * 60)

    try:
        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        logger.info("Connected to message broker")

        logger.info("=" * 60)
        logger.info("QNX Event Source is running. Reading from stdin...")
        logger.info("Pipe QNX grid simulator output to this script:")
        logger.info("  ./grid_sim | python agents/qnx_event_source.py")
        logger.info("=" * 60)

        # Read events from stdin
        await read_stdin_events()

        # Disconnect from broker
        await broker.disconnect()
        logger.info("Disconnected from message broker")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

    logger.info("QNX Event Source Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

