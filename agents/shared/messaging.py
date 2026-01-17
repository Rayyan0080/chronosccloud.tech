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
from uuid import uuid4

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
    Solace PubSub+ message broker backend with automatic reconnection.
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
        Initialize Solace backend.

        Args:
            host: Solace host (default: from env SOLACE_HOST)
            port: Solace port (default: from env SOLACE_PORT or 55555)
            username: Solace username (default: from env SOLACE_USERNAME)
            password: Solace password (default: from env SOLACE_PASSWORD)
            vpn: Solace VPN name (default: from env SOLACE_VPN)
        """
        from .config import get_solace_config

        try:
            config = get_solace_config()
            self.host = host or config["host"]
            self.port = port or config["port"]
            self.username = username or config["username"]
            self.password = password or config["password"]
            self.vpn = vpn or config["vpn"]
        except ValueError:
            # Fallback if config not available
            self.host = host or os.getenv("SOLACE_HOST", "localhost")
            self.port = port or int(os.getenv("SOLACE_PORT", "55555"))
            self.username = username or os.getenv("SOLACE_USERNAME", "default")
            self.password = password or os.getenv("SOLACE_PASSWORD", "default")
            self.vpn = vpn or os.getenv("SOLACE_VPN", "default")

        self.messaging_service = None
        self.publisher = None
        self._subscriptions = {}  # Track active subscriptions
        self._connected = False
        self._reconnect_task = None
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to Solace PubSub+ with automatic reconnection."""
        async with self._connection_lock:
            try:
                # Try to import Solace libraries
                try:
                    from solace.messaging.messaging_service import MessagingService
                except ImportError:
                    raise ImportError(
                        "solace-pubsubplus library not installed. "
                        "Install with: pip install solace-pubsubplus"
                    )

                # Build connection properties
                # Solace SDK uses property-based configuration
                connection_properties = {
                    "solace.messaging.transport.host": f"tcp://{self.host}:{self.port}",
                    "solace.messaging.service.vpn-name": self.vpn,
                    "solace.messaging.authentication.scheme.basic.username": self.username,
                    "solace.messaging.authentication.scheme.basic.password": self.password,
                }

                # Create messaging service
                messaging_service = MessagingService.builder().from_properties(
                    connection_properties
                ).build()

                # Connect (Solace SDK uses synchronous connect)
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                try:
                    await loop.run_in_executor(None, messaging_service.connect)
                except Exception as e:
                    logger.error(f"Solace connection failed: {e}")
                    raise

                self.messaging_service = messaging_service
                self._connected = True

                logger.info("=" * 60)
                logger.info("Connected to Solace Cloud")
                logger.info(f"Host: {self.host}:{self.port}")
                logger.info(f"VPN: {self.vpn}")
                logger.info(f"Username: {self.username}")
                logger.info("=" * 60)

                # Start reconnection monitoring
                self._start_reconnect_monitor()

            except ImportError as e:
                logger.error(f"Solace library not available: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Solace: {e}")
                logger.warning("Falling back to NATS backend")
                raise

    def _start_reconnect_monitor(self) -> None:
        """Start background task to monitor connection and reconnect if needed."""
        async def monitor_connection():
            while True:
                try:
                    await asyncio.sleep(10)  # Check every 10 seconds
                    if not self._connected or not await self.is_connected():
                        logger.warning("Solace connection lost, attempting reconnect...")
                        await self._reconnect()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in reconnect monitor: {e}")

        if self._reconnect_task:
            self._reconnect_task.cancel()
        self._reconnect_task = asyncio.create_task(monitor_connection())

    async def _reconnect(self, max_retries: int = 5, retry_delay: int = 5) -> None:
        """Attempt to reconnect to Solace with exponential backoff."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries}")
                await self.connect()
                logger.info("Successfully reconnected to Solace")
                return
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error("Max reconnection attempts reached")
                    raise

    async def disconnect(self) -> None:
        """Disconnect from Solace PubSub+."""
        async with self._connection_lock:
            try:
                if self._reconnect_task:
                    self._reconnect_task.cancel()
                    try:
                        await self._reconnect_task
                    except asyncio.CancelledError:
                        pass

                if self.publisher:
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, self.publisher.terminate)
                    except Exception as e:
                        logger.warning(f"Error terminating publisher: {e}")

                if self.messaging_service:
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, self.messaging_service.disconnect
                        )
                    except Exception as e:
                        logger.warning(f"Error disconnecting messaging service: {e}")

                self._connected = False
                self._subscriptions.clear()
                logger.info("Disconnected from Solace")

            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish message to Solace topic."""
        if not self._connected or not await self.is_connected():
            raise RuntimeError("Not connected to Solace. Call connect() first.")

        try:
            from solace.messaging.resources.topic import Topic
            from solace.messaging.publisher.direct_message_publisher import (
                PublishFailureListener,
            )

            # Convert topic format: dots to slashes for Solace
            solace_topic = topic.replace(".", "/")

            # Create publisher if needed
            if not self.publisher:
                loop = asyncio.get_event_loop()
                self.publisher = (
                    self.messaging_service.create_direct_message_publisher_builder()
                    .build()
                )
                await loop.run_in_executor(None, self.publisher.start)

            # Create message
            message = (
                self.messaging_service.message_builder()
                .with_application_message_id(str(uuid4()))
                .with_property("application", "chronos")
                .with_property("original_topic", topic)
                .build(json.dumps(payload))
            )

            # Publish (blocking call, run in executor)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self.publisher.publish, message, Topic.of(solace_topic)
            )

            logger.debug(f"Published to Solace topic {solace_topic}: {payload}")

        except Exception as e:
            logger.error(f"Failed to publish to Solace: {e}")
            # Attempt reconnection if connection lost
            if not await self.is_connected():
                await self._reconnect()
            raise

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to Solace topic."""
        if not self._connected or not await self.is_connected():
            raise RuntimeError("Not connected to Solace. Call connect() first.")

        try:
            from solace.messaging.resources.topic import Topic
            from solace.messaging.receiver.message_receiver import MessageReceiver

            # Convert topic format: dots to slashes for Solace
            solace_topic = topic.replace(".", "/")

            # Create receiver
            receiver = (
                self.messaging_service.create_message_receiver_builder()
                .with_subscriptions(Topic.of(solace_topic))
                .build()
            )

            # Start receiver (blocking call, run in executor)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, receiver.start)

            # Set up message handler
            def message_handler(message):
                try:
                    payload_str = message.get_payload_as_string()
                    payload = json.loads(payload_str)
                    # Run handler in async context
                    asyncio.create_task(handler(topic, payload))
                except Exception as e:
                    logger.error(f"Error handling Solace message: {e}")

            # Register async message handler
            receiver.receive_async(message_handler)

            self._subscriptions[topic] = receiver
            logger.info(f"Subscribed to Solace topic: {solace_topic}")

        except Exception as e:
            logger.error(f"Failed to subscribe to Solace: {e}")
            raise

    async def is_connected(self) -> bool:
        """Check if Solace connection is active."""
        if not self.messaging_service:
            return False
        try:
            # Check connection status (Solace SDK method)
            return self.messaging_service.is_connected()
        except Exception:
            return False


# Factory function to create broker instance with fallback
def create_broker(backend: Optional[str] = None) -> MessageBroker:
    """
    Create a message broker instance based on configuration.
    Automatically falls back to NATS if Solace is unavailable.

    Args:
        backend: Backend type ("nats" or "solace"). If None, auto-detects from env.

    Returns:
        MessageBroker instance (Solace if available, otherwise NATS)

    Raises:
        ValueError: If backend type is unknown
    """
    from .config import get_broker_backend

    backend = backend or get_broker_backend()

    if backend == "solace":
        try:
            # Try to create Solace backend
            solace_backend = SolaceBackend()
            # Test if Solace config is available
            from .config import get_solace_config
            get_solace_config()  # Will raise ValueError if config incomplete
            return solace_backend
        except (ImportError, ValueError) as e:
            logger.warning(
                f"Solace backend unavailable ({e}), falling back to NATS"
            )
            return NATSBackend()
    elif backend == "nats":
        return NATSBackend()
    else:
        raise ValueError(
            f"Unknown broker backend: {backend}. Supported: 'nats', 'solace'"
        )


# Convenience functions for easy usage
_broker_instance: Optional[MessageBroker] = None


async def get_broker() -> MessageBroker:
    """
    Get or create the global broker instance with automatic fallback.

    Returns:
        MessageBroker instance (singleton)
    """
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = create_broker()
        try:
            await _broker_instance.connect()
        except Exception as e:
            logger.error(f"Failed to connect to broker: {e}")
            # If Solace fails, try NATS fallback
            if isinstance(_broker_instance, SolaceBackend):
                logger.info("Falling back to NATS backend")
                _broker_instance = NATSBackend()
                await _broker_instance.connect()
            else:
                raise
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

