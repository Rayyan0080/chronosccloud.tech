"""
Query script to fetch recent events from MongoDB.

Usage:
    python agents/query_events.py [--limit N] [--topic TOPIC]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.config import get_mongodb_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB configuration
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "events")


def connect_mongodb():
    """Connect to MongoDB and return collection."""
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

        # Connect to MongoDB
        client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
        )

        # Test connection
        client.admin.command("ping")

        # Get collection
        db = client[config["database"]]
        collection = db[MONGO_COLLECTION]

        return client, collection

    except ImportError:
        logger.error("pymongo not installed. Install with: pip install pymongo")
        raise
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}", exc_info=True)
        raise


def fetch_events(limit: int = 50, topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch recent events from MongoDB.

    Args:
        limit: Maximum number of events to fetch
        topic: Optional topic filter

    Returns:
        List of event documents
    """
    client, collection = connect_mongodb()

    try:
        # Build query
        query = {}
        if topic:
            query["topic"] = topic

        # Fetch events (sorted by timestamp descending)
        cursor = collection.find(query).sort("timestamp", -1).limit(limit)

        events = list(cursor)

        # Convert ObjectId to string for JSON serialization
        for event in events:
            if "_id" in event:
                event["_id"] = str(event["_id"])
            if "timestamp" in event and isinstance(event["timestamp"], datetime):
                event["timestamp"] = event["timestamp"].isoformat()
            if "logged_at" in event and isinstance(event["logged_at"], datetime):
                event["logged_at"] = event["logged_at"].isoformat()

        return events

    finally:
        client.close()


def print_events(events: List[Dict[str, Any]], format: str = "table") -> None:
    """
    Print events in a readable format.

    Args:
        events: List of event documents
        format: Output format - "table", "json", or "summary"
    """
    if format == "json":
        print(json.dumps(events, indent=2))
        return

    if format == "summary":
        print(f"\nFound {len(events)} events:\n")
        for i, event in enumerate(events, 1):
            topic = event.get("topic", "unknown")
            timestamp = event.get("timestamp", "unknown")
            event_id = event.get("payload", {}).get("event_id", "unknown")
            summary = event.get("payload", {}).get("summary", "N/A")

            print(f"{i}. [{topic}]")
            print(f"   Event ID: {event_id}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Summary: {summary}")
            print()
        return

    # Table format
    print("\n" + "=" * 100)
    print(f"{'#':<4} {'Topic':<35} {'Event ID':<40} {'Timestamp':<20}")
    print("=" * 100)

    for i, event in enumerate(events, 1):
        topic = event.get("topic", "unknown")
        timestamp = event.get("timestamp", "unknown")
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        event_id = event.get("payload", {}).get("event_id", "unknown")

        # Truncate long strings
        topic = topic[:33] + ".." if len(topic) > 35 else topic
        event_id = event_id[:38] + ".." if len(event_id) > 40 else event_id
        timestamp = timestamp[:18] if len(str(timestamp)) > 20 else str(timestamp)

        print(f"{i:<4} {topic:<35} {event_id:<40} {timestamp:<20}")

    print("=" * 100)
    print(f"\nTotal: {len(events)} events")


def main():
    """Main entry point for the query script."""
    parser = argparse.ArgumentParser(
        description="Query recent events from MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agents/query_events.py
  python agents/query_events.py --limit 100
  python agents/query_events.py --topic "chronos.events.power.failure"
  python agents/query_events.py --format json
  python agents/query_events.py --format summary
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of events to fetch (default: 50)",
    )

    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Filter events by topic (e.g., 'chronos.events.power.failure')",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "summary"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    try:
        logger.info(f"Fetching {args.limit} events from MongoDB...")
        if args.topic:
            logger.info(f"Filtering by topic: {args.topic}")

        events = fetch_events(limit=args.limit, topic=args.topic)

        if not events:
            print("No events found.")
            return

        print_events(events, format=args.format)

    except Exception as e:
        logger.error(f"Error querying events: {e}", exc_info=True)
        import sys

        sys.exit(1)


if __name__ == "__main__":
    main()

