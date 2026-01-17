"""
State Logger Service

Subscribes to all event topics and logs them to MongoDB for persistence and analysis.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, subscribe
from agents.shared.config import get_mongodb_config
from agents.shared.sentry import init_sentry, capture_startup, capture_received_event, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# All event topics to subscribe to
EVENT_TOPICS = [
    "chronos.events.power.failure",
    "chronos.events.recovery.plan",
    "chronos.events.operator.status",
    "chronos.events.audit.decision",
    "chronos.events.system.action",
    "chronos.events.approval.required",
    "chronos.events.agent.compare",
    "chronos.events.agent.compare.result",
    # Airspace domain events
    "chronos.events.airspace.plan.uploaded",
    "chronos.events.airspace.flight.parsed",
    "chronos.events.airspace.trajectory.sampled",
    "chronos.events.airspace.conflict.detected",
    "chronos.events.airspace.hotspot.detected",
    "chronos.events.airspace.solution.proposed",
    "chronos.events.airspace.report.ready",
    "chronos.events.airspace.mitigation.applied",
    # Geospatial domain events
    "chronos.events.geo.incident",
    "chronos.events.geo.risk_area",
]

# MongoDB configuration
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "events")


class StateLogger:
    """Logs events to MongoDB."""

    def __init__(self):
        """Initialize the state logger."""
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_collection = None
        self.connected = False

    async def _connect_mongodb(self) -> None:
        """Connect to MongoDB and create indexes."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure

            config = get_mongodb_config()

            # Build connection string
            if config["username"] and config["password"]:
                connection_string = (
                    f"mongodb://{config['username']}:{config['password']}"
                    f"@{config['host']}:{config['port']}/{config['database']}"
                    f"?authSource=admin"
                )
            else:
                connection_string = (
                    f"mongodb://{config['host']}:{config['port']}/{config['database']}"
                )

            logger.info(f"Connecting to MongoDB at {config['host']}:{config['port']}...")

            # Connect to MongoDB
            self.mongo_client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )

            # Test connection
            self.mongo_client.admin.command("ping")
            logger.info("Connected to MongoDB")

            # Get database and collection
            self.mongo_db = self.mongo_client[config["database"]]
            self.mongo_collection = self.mongo_db[MONGO_COLLECTION]

            # Create indexes
            await self._create_indexes()

            self.connected = True

        except ImportError:
            logger.error(
                "pymongo not installed. Install with: pip install pymongo"
            )
            raise
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}", exc_info=True)
            raise

    async def _create_indexes(self) -> None:
        """Create indexes on timestamp and topic for efficient queries."""
        try:
            # Create index on timestamp (descending for recent events first)
            self.mongo_collection.create_index([("timestamp", -1)])
            logger.info("Created index on 'timestamp'")

            # Create index on topic
            self.mongo_collection.create_index([("topic", 1)])
            logger.info("Created index on 'topic'")

            # Create compound index on topic and timestamp
            self.mongo_collection.create_index([("topic", 1), ("timestamp", -1)])
            logger.info("Created compound index on 'topic' and 'timestamp'")

        except Exception as e:
            logger.error(f"Error creating indexes: {e}", exc_info=True)
            # Don't fail if indexes already exist

    async def _log_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Log an event to MongoDB.

        Args:
            topic: Event topic
            payload: Event payload
        """
        if not self.connected:
            logger.warning("MongoDB not connected, skipping event log")
            return

        try:
            # Create document
            document = {
                "topic": topic,
                "payload": payload,
                "timestamp": datetime.utcnow(),
                "logged_at": datetime.utcnow(),
            }

            # Insert into MongoDB
            result = self.mongo_collection.insert_one(document)
            logger.debug(
                f"Logged event to MongoDB: topic={topic}, id={result.inserted_id}"
            )

        except Exception as e:
            logger.error(f"Error logging event to MongoDB: {e}", exc_info=True)

    async def _handle_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Handle incoming event and log it to MongoDB.

        Args:
            topic: Event topic
            payload: Event payload
        """
        try:
            logger.info(f"Received event on {topic}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

            # Log to MongoDB
            await self._log_event(topic, payload)

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def run(self) -> None:
        """Run the state logger service."""
        logger.info("Starting State Logger Service")
        logger.info("=" * 60)
        logger.info("Configuration:")
        logger.info(f"  MongoDB Collection: {MONGO_COLLECTION}")
        logger.info(f"  Subscribed Topics: {len(EVENT_TOPICS)}")
        for topic in EVENT_TOPICS:
            logger.info(f"    - {topic}")
        logger.info("=" * 60)

        try:
            # Connect to MongoDB
            await self._connect_mongodb()

            # Connect to message broker
            logger.info("Connecting to message broker...")
            broker = await get_broker()
            logger.info("Connected to message broker")

            # Subscribe to all event topics
            for topic in EVENT_TOPICS:
                await subscribe(topic, self._handle_event)
                logger.info(f"Subscribed to: {topic}")

            logger.info("=" * 60)
            logger.info("State Logger is running. Logging events to MongoDB...")
            logger.info("=" * 60)

            # Keep running
            try:
                await asyncio.Event().wait()  # Wait indefinitely
            except asyncio.CancelledError:
                logger.info("Service cancelled")

            # Disconnect
            await broker.disconnect()
            if self.mongo_client:
                self.mongo_client.close()
            logger.info("Disconnected from services")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise

        logger.info("State Logger Service stopped")


async def main() -> None:
    """Main entry point for the state logger service."""
    logger_instance = StateLogger()
    await logger_instance.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        import sys

        sys.exit(0)

