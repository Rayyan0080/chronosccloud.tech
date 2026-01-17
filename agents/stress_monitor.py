"""
Stress Monitor Service

Monitors operator stress levels and publishes operator.status events with autonomy_level.
Supports webcam mode (OpenCV placeholder) and demo toggle mode.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4

from agents.shared.messaging import get_broker, publish
from agents.shared.schema import OperatorStatus, Severity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Topic for operator status events
OPERATOR_STATUS_TOPIC = "chronos.events.operator.status"

# Operator configuration
OPERATOR_ID = os.getenv("OPERATOR_ID", "OP-001")
OPERATOR_NAME = os.getenv("OPERATOR_NAME", "Demo Operator")
OPERATOR_LOCATION = os.getenv("OPERATOR_LOCATION", "control-room-1")

# Autonomy levels
AUTONOMY_NORMAL = "NORMAL"
AUTONOMY_HIGH = "HIGH"


class StressMonitor:
    """Stress monitor with webcam and demo toggle modes."""

    def __init__(self, mode: str = "demo"):
        """
        Initialize stress monitor.

        Args:
            mode: Operating mode - "demo" or "webcam"
        """
        self.mode = mode.lower()
        self.current_autonomy = AUTONOMY_NORMAL
        self.current_status = OperatorStatus.AVAILABLE
        self.webcam_available = False

        if self.mode == "webcam":
            self._check_webcam_support()

    def _check_webcam_support(self) -> None:
        """Check if OpenCV is available for webcam mode."""
        try:
            import cv2
            self.webcam_available = True
            logger.info("OpenCV available - webcam mode enabled")
        except ImportError:
            logger.warning(
                "OpenCV not available. Install with: pip install opencv-python"
            )
            logger.info("Falling back to demo mode")
            self.mode = "demo"
            self.webcam_available = False

    async def _webcam_monitor(self) -> None:
        """
        Webcam monitoring mode (placeholder implementation).

        This is a placeholder that simulates stress detection.
        In a real implementation, this would use OpenCV to analyze
        facial expressions, heart rate, or other stress indicators.
        """
        if not self.webcam_available:
            logger.warning("Webcam mode requested but OpenCV not available")
            return

        try:
            import cv2

            logger.info("Starting webcam monitoring...")
            logger.info("Note: This is a placeholder - no actual ML processing")

            # Try to open webcam
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                logger.warning("Could not open webcam, falling back to demo mode")
                self.mode = "demo"
                return

            logger.info("Webcam opened successfully")
            logger.info("Placeholder: Simulating stress detection every 10 seconds")

            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read from webcam")
                    await asyncio.sleep(1)
                    continue

                frame_count += 1

                # Placeholder: Simulate stress detection every 10 seconds
                # In real implementation, this would analyze the frame
                if frame_count % 300 == 0:  # ~10 seconds at 30fps
                    # Simulate random stress level
                    import random

                    stress_level = random.choice([AUTONOMY_NORMAL, AUTONOMY_HIGH])
                    if stress_level != self.current_autonomy:
                        self.current_autonomy = stress_level
                        await self._publish_status_update()

                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.033)  # ~30fps

        except Exception as e:
            logger.error(f"Error in webcam monitoring: {e}", exc_info=True)
            logger.info("Falling back to demo mode")
            self.mode = "demo"

    async def _publish_status_update(self) -> None:
        """Publish operator status event with current autonomy level."""
        try:
            # Determine severity based on autonomy level
            if self.current_autonomy == AUTONOMY_HIGH:
                severity = Severity.WARNING
                summary = f"{OPERATOR_NAME} stress level HIGH - increased autonomy activated"
            else:
                severity = Severity.INFO
                summary = f"{OPERATOR_NAME} stress level NORMAL - standard operation"

            # Build event
            event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": severity.value,
                "sector_id": OPERATOR_LOCATION,
                "summary": summary,
                "details": {
                    "operator_id": OPERATOR_ID,
                    "operator_name": OPERATOR_NAME,
                    "status": self.current_status.value,
                    "current_task": None,
                    "location": OPERATOR_LOCATION,
                    "last_action": f"autonomy_level_{self.current_autonomy.lower()}",
                    "last_action_time": datetime.utcnow().isoformat() + "Z",
                    "autonomy_level": self.current_autonomy,  # Extended field
                },
            }

            # Log event to console
            logger.info("=" * 60)
            logger.info("OPERATOR STATUS EVENT")
            logger.info("=" * 60)
            logger.info(f"Event ID: {event['event_id']}")
            logger.info(f"Timestamp: {event['timestamp']}")
            logger.info(f"Severity: {event['severity']}")
            logger.info(f"Operator: {OPERATOR_NAME} ({OPERATOR_ID})")
            logger.info(f"Location: {OPERATOR_LOCATION}")
            logger.info(f"Status: {self.current_status.value}")
            logger.info(f"Autonomy Level: {self.current_autonomy}")
            logger.info(f"Summary: {summary}")
            logger.info("=" * 60)
            logger.info(f"Event JSON:\n{json.dumps(event, indent=2)}")
            logger.info("=" * 60)

            # Publish to message broker
            await publish(OPERATOR_STATUS_TOPIC, event)
            logger.info(f"Published to topic: {OPERATOR_STATUS_TOPIC}")

        except Exception as e:
            logger.error(f"Failed to publish operator status event: {e}", exc_info=True)

    async def _demo_toggle_handler(self) -> None:
        """
        Handle keyboard input for demo toggle mode.
        Press 's' to set stress HIGH, 'n' to set NORMAL, 'q' to quit.
        """
        loop = asyncio.get_event_loop()

        def read_input():
            """Read input from stdin (blocking)."""
            try:
                return sys.stdin.read(1)
            except (EOFError, KeyboardInterrupt):
                return None

        logger.info("=" * 60)
        logger.info("DEMO TOGGLE MODE")
        logger.info("=" * 60)
        logger.info("Controls:")
        logger.info("  Press 's' - Set stress HIGH (increased autonomy)")
        logger.info("  Press 'n' - Set stress NORMAL (standard operation)")
        logger.info("  Press 'q' - Quit")
        logger.info("=" * 60)
        logger.info(f"Current autonomy level: {self.current_autonomy}")

        while True:
            try:
                # Read input asynchronously
                char = await loop.run_in_executor(None, read_input)
                if char is None:
                    break

                char = char.lower().strip()

                if char == "s":
                    if self.current_autonomy != AUTONOMY_HIGH:
                        self.current_autonomy = AUTONOMY_HIGH
                        logger.info(">>> Stress level set to HIGH <<<")
                        await self._publish_status_update()
                    else:
                        logger.info("Stress level already HIGH")
                elif char == "n":
                    if self.current_autonomy != AUTONOMY_NORMAL:
                        self.current_autonomy = AUTONOMY_NORMAL
                        logger.info(">>> Stress level set to NORMAL <<<")
                        await self._publish_status_update()
                    else:
                        logger.info("Stress level already NORMAL")
                elif char == "q":
                    logger.info("Quit requested. Shutting down...")
                    break
                elif char:
                    logger.info(
                        f"Unknown command: '{char}'. Use 's' (HIGH), 'n' (NORMAL), or 'q' (quit)"
                    )

            except Exception as e:
                logger.error(f"Error in keyboard input handler: {e}", exc_info=True)
                await asyncio.sleep(0.1)

    async def run(self) -> None:
        """Run the stress monitor in the configured mode."""
        logger.info("Starting Stress Monitor Service")
        logger.info("=" * 60)
        logger.info("Configuration:")
        logger.info(f"  Mode: {self.mode}")
        logger.info(f"  Operator: {OPERATOR_NAME} ({OPERATOR_ID})")
        logger.info(f"  Location: {OPERATOR_LOCATION}")
        logger.info(f"  Topic: {OPERATOR_STATUS_TOPIC}")
        logger.info("=" * 60)

        try:
            # Connect to message broker
            logger.info("Connecting to message broker...")
            broker = await get_broker()
            logger.info("Connected to message broker")

            # Publish initial status
            await self._publish_status_update()

            # Run in appropriate mode
            if self.mode == "webcam" and self.webcam_available:
                # Run webcam monitoring
                await self._webcam_monitor()
            else:
                # Run demo toggle mode
                await self._demo_toggle_handler()

            # Disconnect from broker
            await broker.disconnect()
            logger.info("Disconnected from message broker")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)

        logger.info("Stress Monitor Service stopped")


async def main() -> None:
    """Main entry point for the stress monitor service."""
    # Determine mode from environment or command line
    mode = os.getenv("STRESS_MONITOR_MODE", "demo").lower()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if mode not in ["demo", "webcam"]:
        logger.warning(f"Invalid mode: {mode}, using 'demo'")
        mode = "demo"

    monitor = StressMonitor(mode=mode)
    await monitor.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)

