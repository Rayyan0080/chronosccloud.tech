"""
Message broker abstraction layer for Project Chronos.

Provides a unified pub/sub interface that can work with different backends:
- NATS (local development)
- Solace PubSub+ (production)
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class MessageBroker(ABC):
    """Abstract base class for message broker implementations."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the message broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the message broker."""
        pass

    @abstractmethod
    async def publish(self, topic: str, payload: dict) -> None:
        """
        Publish a message to a topic.

        Args:
            topic: Topic name (e.g., "chronos.events.power.failure")
            payload: Message payload as dictionary
        """
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: Callable) -> None:
        """
        Subscribe to a topic and register a handler function.

        Args:
            topic: Topic name to subscribe to
            handler: Async function that will be called with (topic, payload) when messages arrive
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the broker connection is active."""
        pass


class NATSBackend(MessageBroker):
    """NATS message broker backend for local development."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize NATS backend.

        Args:
            host: NATS server host (default: from env NATS_HOST or localhost)
            port: NATS server port (default: from env NATS_PORT or 4222)
        """
        self.host = host or os.getenv("NATS_HOST", "localhost")
        self.port = port or int(os.getenv("NATS_PORT", "4222"))
        self.nc = None
        self._subscriptions = {}  # Track active subscriptions

    async def connect(self) -> None:
        """Connect to NATS server."""
        try:
            import nats
            from nats.aio.client import Client as NATS

            servers = [f"nats://{self.host}:{self.port}"]
            self.nc = await nats.connect(servers=servers)
            logger.info(f"Connected to NATS at {self.host}:{self.port}")
        except ImportError:
            raise ImportError(
                "NATS client library not installed. Install with: pip install nats-py"
            )
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def disconnect(self) -> None:
        """Close NATS connection."""
        if self.nc:
            await self.nc.close()
            self.nc = None
            self._subscriptions.clear()
            logger.info("Disconnected from NATS")

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish message to NATS topic."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS. Call connect() first.")

        try:
            message_data = json.dumps(payload).encode()
            await self.nc.publish(topic, message_data)
            logger.debug(f"Published to {topic}: {payload}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            raise

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to NATS topic."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS. Call connect() first.")

        async def message_handler(msg):
            try:
                payload = json.loads(msg.data.decode())
                await handler(topic, payload)
            except Exception as e:
                logger.error(f"Error handling message from {topic}: {e}")

        try:
            sub = await self.nc.subscribe(topic, cb=message_handler)
            self._subscriptions[topic] = sub
            logger.info(f"Subscribed to {topic}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            raise

    async def is_connected(self) -> bool:
        """Check if NATS connection is active."""
        return self.nc is not None and not self.nc.is_closed


class SolaceBackend(MessageBroker):
    """
    Solace PubSub+ message broker backend (stub implementation).

    TODO: Implement full Solace PubSub+ integration:
    1. Install Solace Python API: pip install solace-pubsubplus
    2. Configure connection using environment variables:
       - SOLACE_HOST
       - SOLACE_PORT
       - SOLACE_USERNAME
       - SOLACE_PASSWORD
       - SOLACE_VPN
    3. Implement connect() using MessagingService
    4. Implement publish() using DirectMessagePublisher
    5. Implement subscribe() using MessageReceiver
    6. Handle topic name conversion (dots to slashes: chronos.events -> chronos/events)
    7. Add error handling and reconnection logic
    8. Add message persistence and guaranteed delivery configuration
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        vpn: Optional[str] = None,
    ):
        """
        Initialize Solace backend (stub).

        Args:
            host: Solace host (default: from env SOLACE_HOST)
            port: Solace port (default: from env SOLACE_PORT or 55555)
            username: Solace username (default: from env SOLACE_USERNAME)
            password: Solace password (default: from env SOLACE_PASSWORD)
            vpn: Solace VPN name (default: from env SOLACE_VPN or "default")
        """
        self.host = host or os.getenv("SOLACE_HOST", "localhost")
        self.port = port or int(os.getenv("SOLACE_PORT", "55555"))
        self.username = username or os.getenv("SOLACE_USERNAME", "default")
        self.password = password or os.getenv("SOLACE_PASSWORD", "default")
        self.vpn = vpn or os.getenv("SOLACE_VPN", "default")
        self.messaging_service = None
        self.publisher = None
        self._subscriptions = {}  # Track active subscriptions
        self._connected = False

    async def connect(self) -> None:
        """
        Connect to Solace PubSub+ (stub implementation).

        TODO: Implement actual Solace connection:
        ```python
        from solace.messaging.messaging_service import MessagingService
        from solace.messaging.config.transport_security_configuration import TransportSecurityConfiguration

        messaging_service = MessagingService.builder() \
            .from_properties({
                "solace.messaging.transport.host": f"tcp://{self.host}:{self.port}",
                "solace.messaging.service.vpn-name": self.vpn,
                "solace.messaging.authentication.scheme.basic.username": self.username,
                "solace.messaging.authentication.scheme.basic.password": self.password,
            }) \
            .build()

        await messaging_service.connect()
        self.messaging_service = messaging_service
        self._connected = True
        ```
        """
        logger.warning("Solace backend is a stub. Connection not implemented.")
        logger.info(
            f"Solace connection parameters: {self.host}:{self.port}, VPN: {self.vpn}, User: {self.username}"
        )
        # Placeholder: simulate connection
        self._connected = True
        logger.warning("TODO: Implement actual Solace PubSub+ connection")

    async def disconnect(self) -> None:
        """
        Disconnect from Solace PubSub+ (stub implementation).

        TODO: Implement actual Solace disconnection:
        ```python
        if self.publisher:
            await self.publisher.terminate()
        if self.messaging_service:
            await self.messaging_service.disconnect()
        self._connected = False
        ```
        """
        logger.warning("Solace backend is a stub. Disconnection not implemented.")
        self._connected = False
        self._subscriptions.clear()
        logger.warning("TODO: Implement actual Solace PubSub+ disconnection")

    async def publish(self, topic: str, payload: dict) -> None:
        """
        Publish message to Solace topic (stub implementation).

        TODO: Implement actual Solace publishing:
        1. Convert topic format: "chronos.events.power.failure" -> "chronos/events/power/failure"
        2. Create DirectMessagePublisher if not exists
        3. Create OutboundMessage with JSON payload
        4. Publish to topic using Topic.of()
        5. Handle errors and retries

        Example:
        ```python
        from solace.messaging.resources.topic import Topic
        from solace.messaging.publisher.direct_message_publisher import PublishFailureListener

        # Convert topic format
        solace_topic = topic.replace(".", "/")
        
        # Create publisher if needed
        if not self.publisher:
            self.publisher = self.messaging_service.create_direct_message_publisher_builder() \
                .build()
            await self.publisher.start()

        # Create and publish message
        message = self.messaging_service.message_builder() \
            .with_application_message_id(str(uuid.uuid4())) \
            .with_property("application", "chronos") \
            .build(json.dumps(payload))
        
        await self.publisher.publish(message, Topic.of(solace_topic))
        ```
        """
        # Convert topic format: dots to slashes for Solace
        solace_topic = topic.replace(".", "/")
        logger.warning(
            f"Solace backend is a stub. Would publish to {solace_topic}: {payload}"
        )
        logger.warning("TODO: Implement actual Solace PubSub+ publishing")

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """
        Subscribe to Solace topic (stub implementation).

        TODO: Implement actual Solace subscription:
        1. Convert topic format: "chronos.events.power.failure" -> "chronos/events/power/failure"
        2. Create MessageReceiver with topic subscription
        3. Set up async message handler
        4. Handle topic subscriptions and message callbacks
        5. Support wildcard subscriptions if needed

        Example:
        ```python
        from solace.messaging.resources.topic import Topic
        from solace.messaging.receiver.message_receiver import MessageReceiver

        # Convert topic format
        solace_topic = topic.replace(".", "/")
        
        # Create receiver
        receiver = self.messaging_service.create_message_receiver_builder() \
            .with_subscriptions(Topic.of(solace_topic)) \
            .build()
        
        # Start receiver
        await receiver.start()
        
        # Set up message handler
        async def message_handler(message):
            payload = json.loads(message.get_payload_as_string())
            await handler(topic, payload)
        
        receiver.receive_async(message_handler)
        self._subscriptions[topic] = receiver
        ```
        """
        # Convert topic format: dots to slashes for Solace
        solace_topic = topic.replace(".", "/")
        logger.warning(
            f"Solace backend is a stub. Would subscribe to {solace_topic}"
        )
        logger.warning("TODO: Implement actual Solace PubSub+ subscription")
        # Placeholder: store subscription
        self._subscriptions[topic] = {"topic": solace_topic, "handler": handler}

    async def is_connected(self) -> bool:
        """Check if Solace connection is active (stub)."""
        return self._connected


# Factory function to create broker instance
def create_broker(backend: Optional[str] = None) -> MessageBroker:
    """
    Create a message broker instance based on configuration.

    Args:
        backend: Backend type ("nats" or "solace"). If None, reads from env BROKER_BACKEND.

    Returns:
        MessageBroker instance

    Raises:
        ValueError: If backend type is unknown
    """
    from .config import get_broker_backend

    backend = backend or get_broker_backend()

    if backend == "nats":
        return NATSBackend()
    elif backend == "solace":
        return SolaceBackend()
    else:
        raise ValueError(
            f"Unknown broker backend: {backend}. Supported: 'nats', 'solace'"
        )


# Convenience functions for easy usage
_broker_instance: Optional[MessageBroker] = None


async def get_broker() -> MessageBroker:
    """
    Get or create the global broker instance.

    Returns:
        MessageBroker instance (singleton)
    """
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = create_broker()
        await _broker_instance.connect()
    return _broker_instance


async def publish(topic: str, payload: dict) -> None:
    """
    Convenience function to publish a message.

    Args:
        topic: Topic name
        payload: Message payload
    """
    broker = await get_broker()
    await broker.publish(topic, payload)


async def subscribe(topic: str, handler: Callable) -> None:
    """
    Convenience function to subscribe to a topic.

    Args:
        topic: Topic name
        handler: Async handler function(topic, payload)
    """
    broker = await get_broker()
    await broker.subscribe(topic, handler)

