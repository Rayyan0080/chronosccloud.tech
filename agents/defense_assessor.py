"""
Defense Assessor Agent

Subscribes to defense.threat.detected events and automatically generates AI assessments
using Gemini. Publishes defense.threat.assessed events with recommended actions.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, subscribe, publish
from agents.shared.constants import (
    DEFENSE_THREAT_DETECTED_TOPIC,
    DEFENSE_THREAT_ASSESSED_TOPIC,
)
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_exception,
)
from ai.llm_client import assess_defense_threat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default city posture (can be made configurable)
DEFAULT_CITY_POSTURE = "normal"


class DefenseAssessorAgent:
    """Automatically assesses detected threats using AI."""
    
    def __init__(self):
        """Initialize the defense assessor agent."""
        self.processed_threats = set()  # Track processed threats to avoid duplicates
    
    async def _handle_threat_detected(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle a defense.threat.detected event and generate AI assessment."""
        try:
            event_id = payload.get("event_id")
            details = payload.get("details", {})
            threat_id = details.get("threat_id")
            
            if not threat_id:
                logger.warning(f"Received threat event {event_id} without threat_id, skipping")
                return
            
            # Skip if already processed
            if threat_id in self.processed_threats:
                logger.debug(f"Threat {threat_id} already processed, skipping")
                return
            
            # Extract threat information
            threat_summary = details.get("summary", "Unknown threat detected")
            sources = details.get("sources", [])
            confidence_score = details.get("confidence_score", 0.5)
            sector_id = payload.get("sector_id", "unknown")
            
            # Get current city posture (default to "normal" for now)
            current_posture = DEFAULT_CITY_POSTURE
            
            logger.info(f"Assessing threat {threat_id} (confidence: {confidence_score:.2f}, sources: {sources})")
            
            # Call AI assessment function
            assessment_result = await assess_defense_threat(
                threat_id=threat_id,
                threat_summary=threat_summary,
                sources=sources,
                confidence_score=confidence_score,
                current_posture=current_posture,
                sector_id=sector_id,
            )
            
            if assessment_result:
                # Assessment was successful and event was published by assess_defense_threat
                logger.info(f"✓ Successfully assessed threat {threat_id}")
                self.processed_threats.add(threat_id)
                capture_received_event(DEFENSE_THREAT_ASSESSED_TOPIC, threat_id, {"sources": sources})
            else:
                # Assessment failed (Gemini not available or invalid response)
                logger.warning(f"Failed to assess threat {threat_id} (Gemini may not be configured or returned invalid response)")
                # Still mark as processed to avoid retrying
                self.processed_threats.add(threat_id)
        
        except Exception as e:
            logger.error(f"Error handling threat detected event: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "event_id": payload.get("event_id")})
    
    async def run(self) -> None:
        """Main run loop for the defense assessor agent."""
        # Initialize Sentry
        init_sentry("defense_assessor")
        capture_startup("defense-assessor")
        
        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        await broker.connect()
        logger.info("✓ Connected to message broker")
        
        # Subscribe to defense.threat.detected
        logger.info("Subscribing to defense.threat.detected...")
        await subscribe(DEFENSE_THREAT_DETECTED_TOPIC, self._handle_threat_detected)
        logger.info("✓ Subscribed to defense.threat.detected")
        
        logger.info("=" * 80)
        logger.info("DEFENSE ASSESSOR AGENT RUNNING")
        logger.info("=" * 80)
        logger.info("Automatically assessing detected threats using AI (Gemini)")
        logger.info("Publishes defense.threat.assessed events")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            capture_exception(e, {"service": "defense_assessor", "error_type": "fatal"})
            raise
        finally:
            await broker.disconnect()
            logger.info("Disconnected from message broker")
        
        logger.info("Defense Assessor Agent stopped")


async def main():
    """Main entry point."""
    agent = DefenseAssessorAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

