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
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    # Try to find .env file in project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent  # agents/shared/ -> agents/ -> project root
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass  # python-dotenv not installed, skip

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
                # Validate configuration before attempting connection
                if not self.host or self.host.strip() == "" or "xxx" in self.host.lower():
                    raise ValueError(
                        f"Invalid SOLACE_HOST: '{self.host}'. "
                        "Please set SOLACE_HOST to your actual Solace Cloud hostname "
                        "(e.g., 'xxx.messaging.solace.cloud' - replace 'xxx' with your actual host)."
                    )
                
                if not self.username or self.username.strip() == "":
                    raise ValueError(
                        "SOLACE_USERNAME is required. Please set it in your .env file."
                    )
                
                if not self.password or self.password.strip() == "":
                    raise ValueError(
                        "SOLACE_PASSWORD is required. Please set it in your .env file."
                    )
                
                # Log connection attempt (mask sensitive info)
                logger.info(f"Attempting to connect to Solace...")
                logger.info(f"Host: {self.host}:{self.port}")
                logger.info(f"VPN: {self.vpn}")
                logger.info(f"Username: {self.username}")
                
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
                # Port 55443 is for secured (TLS) connections, use tcps://
                # Port 55555 is for unsecured connections, use tcp://
                use_tls = self.port == 55443
                
                # IMPORTANT: For development, use port 55555 (unsecured) to avoid TLS trust store issues
                # Port 55443 (secured) requires proper certificate configuration
                if use_tls:
                    logger.warning("=" * 60)
                    logger.warning("⚠️  USING SECURED CONNECTION (Port 55443)")
                    logger.warning("⚠️  This requires TLS certificate configuration.")
                    logger.warning("⚠️  For development, consider using port 55555 (unsecured)")
                    logger.warning("=" * 60)
                
                protocol = "tcps" if use_tls else "tcp"
                
                # Strip protocol from host if it was included
                host_clean = self.host
                if "://" in host_clean:
                    host_clean = host_clean.split("://", 1)[1]
                
                # Remove port from host if it was included (e.g., host:port format)
                if ":" in host_clean:
                    host_clean = host_clean.split(":")[0]
                
                connection_string = f"{protocol}://{host_clean}:{self.port}"
                logger.debug(f"Connection string: {connection_string} (TLS: {use_tls})")
                
                # Build connection properties
                connection_properties = {
                    "solace.messaging.transport.host": connection_string,
                    "solace.messaging.service.vpn-name": self.vpn,
                    "solace.messaging.authentication.scheme.basic.username": self.username,
                    "solace.messaging.authentication.scheme.basic.password": self.password,
                    "solace.messaging.transport.connect-timeout-in-millis": "60000",  # 60 seconds (increased from 30)
                    "solace.messaging.transport.reconnect-retries": "3",
                    "solace.messaging.transport.reconnect-retry-wait-in-millis": "1000",
                }

                # Create messaging service builder
                builder = MessagingService.builder().from_properties(connection_properties)
                
                # Add explicit authentication strategy (recommended by Solace docs)
                try:
                    from solace.messaging.config.authentication_strategy import BasicUserNamePassword
                    auth_strategy = BasicUserNamePassword.of(self.username, self.password)
                    builder = builder.with_authentication_strategy(auth_strategy)
                    logger.debug("Explicit authentication strategy configured")
                except ImportError:
                    logger.warning("Could not import BasicUserNamePassword, using property-based auth")
                except Exception as auth_error:
                    logger.warning(f"Could not configure explicit auth strategy: {auth_error}")
                
                # For TLS connections, configure transport security strategy
                if use_tls:
                    try:
                        from solace.messaging.config.transport_security_strategy import TLS
                        from pathlib import Path
                        
                        # Check if user provided a trust store file path
                        trust_store_path = os.getenv("SOLACE_TRUST_STORE_PATH")
                        trust_store_configured = False
                        
                        if trust_store_path:
                            # Resolve relative paths relative to project root
                            if not os.path.isabs(trust_store_path):
                                # Strip leading ./ or .\ from path
                                trust_store_path_clean = trust_store_path.lstrip('./').lstrip('.\\')
                                # Try to find project root (where .env file is)
                                current_file = Path(__file__)
                                project_root = current_file.parent.parent.parent  # agents/shared/ -> agents/ -> project root
                                trust_store_path = str(project_root / trust_store_path_clean)
                            
                            logger.info(f"Checking trust store file: {trust_store_path}")
                            
                            if os.path.exists(trust_store_path):
                                # Use provided trust store file
                                logger.info(f"✅ Using trust store file: {trust_store_path}")
                                try:
                                    tls_strategy = TLS.create().with_certificate_validation(
                                        validate_server_name=False,
                                        ignore_expiration=True,
                                        trust_store_file_path=trust_store_path
                                    )
                                    builder = builder.with_transport_security_strategy(tls_strategy)
                                    logger.info("TLS security strategy configured with trust store")
                                    trust_store_configured = True
                                except Exception as tls_error:
                                    logger.error(f"Failed to configure TLS with trust store: {tls_error}")
                                    raise
                            else:
                                logger.warning(f"⚠️  Trust store file not found: {trust_store_path}")
                                logger.warning("Falling back to alternative TLS configuration...")
                        else:
                            logger.info("SOLACE_TRUST_STORE_PATH not set, using alternative TLS configuration")
                        
                        if not trust_store_configured:
                            # Try to disable certificate validation for development
                            logger.warning("=" * 60)
                            logger.warning("⚠️  TLS CONNECTION WITHOUT CERTIFICATE VALIDATION")
                            logger.warning("⚠️  This is for development only - NOT SECURE for production!")
                            logger.warning("=" * 60)
                            
                            try:
                                # Try using the SDK method to disable validation
                                from solace.messaging.config.certificate_validation_strategy import CertificateValidation
                                tls_strategy = TLS.create().with_certificate_validation(
                                    CertificateValidation.create().without_certificate_validation()
                                )
                                builder = builder.with_transport_security_strategy(tls_strategy)
                                logger.info("TLS security strategy configured (validation disabled)")
                            except (ImportError, AttributeError, Exception) as e:
                                # Fallback: Try to configure with minimal validation
                                logger.warning(f"Could not use without_certificate_validation(): {e}")
                                logger.warning("Attempting alternative TLS configuration...")
                                
                                # Alternative: Use system trust store with relaxed validation
                                try:
                                    tls_strategy = TLS.create().with_certificate_validation(
                                        validate_server_name=False,
                                        ignore_expiration=True,
                                        trust_store_file_path=None  # Use system default
                                    )
                                    builder = builder.with_transport_security_strategy(tls_strategy)
                                    logger.info("TLS security strategy configured (system trust store)")
                                except Exception as alt_error:
                                    logger.error(f"Failed to configure TLS: {alt_error}")
                                    logger.error("=" * 60)
                                    logger.error("SOLUTION: Download Root CA certificate from Solace Cloud")
                                    logger.error("  1. Go to Solace Cloud Console > Connect tab")
                                    logger.error("  2. Download 'Root CA PEM' or 'Root G2 PEM'")
                                    logger.error("  3. Save the file (e.g., as 'solace-ca.pem')")
                                    logger.error("  4. Set environment variable: SOLACE_TRUST_STORE_PATH=/path/to/solace-ca.pem")
                                    logger.error("=" * 60)
                                    raise
                    except ImportError as e:
                        logger.error(f"TLS configuration classes not available: {e}")
                        logger.error("Install solace-pubsubplus package: pip install solace-pubsubplus")
                        raise

                # Build messaging service
                logger.info(f"Building messaging service with connection string: {connection_string}")
                messaging_service = builder.build()
                logger.info("Messaging service built successfully, attempting connection...")

                # Connect (Solace SDK uses synchronous connect)
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                try:
                    logger.info("Calling messaging_service.connect()...")
                    await loop.run_in_executor(None, messaging_service.connect)
                    logger.info("Connection call completed")
                except Exception as e:
                    error_msg = str(e)
                    if "UNRESOLVED_HOST" in error_msg or "Could not be resolved" in error_msg:
                        logger.error(f"Solace connection failed: Cannot resolve host '{self.host}'")
                        logger.error("Possible issues:")
                        logger.error("  1. SOLACE_HOST contains placeholder 'xxx' - replace with actual hostname")
                        logger.error("  2. Hostname is incorrect - check Solace Cloud console")
                        logger.error("  3. Network/DNS issue - verify hostname is reachable")
                        logger.error(f"  4. Current host value: '{self.host}'")
                    elif "TIMEOUT" in error_msg or "timeout" in error_msg.lower():
                        logger.error(f"Solace connection failed: Connection timeout after 60 seconds")
                        logger.error("=" * 60)
                        logger.error("Possible issues:")
                        logger.error(f"  1. Port {self.port} may be blocked by firewall")
                        logger.error("  2. Network connectivity issue - test with: telnet <host> <port>")
                        logger.error("  3. Solace Cloud service may be unreachable from your network")
                        logger.error("  4. VPN or proxy may be blocking the connection")
                        logger.error("=" * 60)
                        logger.error("TROUBLESHOOTING STEPS:")
                        logger.error(f"  1. Test network connectivity:")
                        logger.error(f"     PowerShell: Test-NetConnection -ComputerName {self.host} -Port {self.port}")
                        logger.error(f"     Or: telnet {self.host} {self.port}")
                        logger.error("  2. Verify Solace Cloud service is running (check console)")
                        logger.error("  3. Check if corporate firewall/proxy is blocking outbound connections")
                        logger.error("  4. Try from a different network to rule out network issues")
                        logger.error("=" * 60)
                    else:
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


# Factory function to create broker instance
def create_broker(backend: Optional[str] = None) -> MessageBroker:
    """
    Create a message broker instance based on configuration.
    
    CRITICAL: Only creates the specified backend. Does NOT auto-fallback.
    If Solace is configured but unavailable, connection will fail (as intended).
    This ensures a SINGLE active broker at runtime.

    Args:
        backend: Backend type ("nats" or "solace"). If None, auto-detects from env.

    Returns:
        MessageBroker instance (Solace or NATS based on configuration)

    Raises:
        ValueError: If backend type is unknown or configuration is invalid
    """
    from .config import get_broker_backend

    backend = backend or get_broker_backend()
    
    # Log which backend is being used (CRITICAL for debugging)
    logger.info("=" * 60)
    logger.info(f"Using broker backend: {backend.upper()}")
    logger.info("=" * 60)

    if backend == "solace":
        # Create Solace backend - will fail if config is incomplete (as intended)
        from .config import get_solace_config
        get_solace_config()  # Will raise ValueError if config incomplete
        return SolaceBackend()
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
    Get or create the global broker instance.
    
    CRITICAL: Does NOT auto-fallback. If configured backend fails, connection fails.
    This ensures a SINGLE active broker at runtime and prevents accidental dual connections.

    Returns:
        MessageBroker instance (singleton)
        
    Raises:
        ConnectionError: If broker connection fails (no auto-fallback)
    """
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = create_broker()
        try:
            await _broker_instance.connect()
            # Log successful connection
            backend_type = "Solace" if isinstance(_broker_instance, SolaceBackend) else "NATS"
            logger.info(f"Successfully connected to {backend_type} broker")
        except Exception as e:
            logger.error(f"Failed to connect to broker: {e}")
            logger.error("Broker connection failed. Check configuration and ensure broker is running.")
            raise ConnectionError(f"Failed to connect to broker: {e}") from e
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

