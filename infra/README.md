# Infrastructure

Infrastructure configuration, deployment scripts, and shared utilities.

## Structure

- `docker/`: Dockerfiles and Docker Compose configurations
- `k8s/`: Kubernetes manifests (optional)
- `shared/`: Shared libraries and utilities used across services
- `docker-compose.yml`: Local infrastructure services (NATS, MongoDB)

## Local Infrastructure Services

The `docker-compose.yml` in this directory provides local development infrastructure:

- **NATS**: Lightweight message broker placeholder for local development
- **MongoDB**: Document database for storing event history and system state
- **Mongo Express** (optional): Web-based MongoDB administration tool

### Starting Local Infrastructure

```bash
# Start all infrastructure services
docker-compose -f infra/docker-compose.yml up -d

# Start with MongoDB Express (database UI)
docker-compose -f infra/docker-compose.yml --profile tools up -d

# View logs
docker-compose -f infra/docker-compose.yml logs -f

# Stop services
docker-compose -f infra/docker-compose.yml down
```

### Service Endpoints

- **NATS**: `nats://localhost:4222` (client connections)
- **NATS Monitoring**: http://localhost:8222
- **MongoDB**: `mongodb://localhost:27017`
- **Mongo Express**: http://localhost:8081 (when using `--profile tools`)

## Message Broker: NATS to Solace PubSub+ Migration

### Current Setup (Local Development)

The `docker-compose.yml` uses **NATS** as a lightweight message broker placeholder. NATS is ideal for local development because:

- Lightweight and fast
- Easy to run locally
- Supports pub/sub messaging patterns
- Compatible with event-driven architectures

### Production Migration to Solace PubSub+

For production deployments, you should migrate to **Solace PubSub+** for enterprise-grade messaging capabilities:

- High availability and fault tolerance
- Advanced routing and filtering
- Enterprise security features
- Better observability and monitoring
- Guaranteed message delivery

### Migration Steps

#### 1. Update Environment Variables

Update your `.env` file to use Solace connection details instead of NATS:

```env
# Replace NATS variables with Solace
SOLACE_HOST=your-solace-host.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_USERNAME=your-username
SOLACE_PASSWORD=your-password
SOLACE_VPN=default
SOLACE_CLIENT_NAME=chronos-client

# Remove or comment out NATS variables
# NATS_HOST=localhost
# NATS_PORT=4222
```

#### 2. Update Service Code

Replace NATS client libraries with Solace client libraries in your services:

**Before (NATS - Python example):**
```python
import nats
from nats.aio.client import Client as NATS

nc = await nats.connect("nats://localhost:4222")
await nc.publish("chronos.events.power.failure", event_json.encode())
```

**After (Solace - Python example):**
```python
from solace.messaging.messaging_service import MessagingService
from solace.messaging.resources.topic import Topic

messaging_service = MessagingService.builder() \
    .from_properties({
        "solace.messaging.transport.host": os.getenv("SOLACE_HOST"),
        "solace.messaging.service.vpn-name": os.getenv("SOLACE_VPN"),
        "solace.messaging.authentication.scheme.basic.username": os.getenv("SOLACE_USERNAME"),
        "solace.messaging.authentication.scheme.basic.password": os.getenv("SOLACE_PASSWORD"),
    }) \
    .build()

publisher = messaging_service.create_direct_message_publisher_builder().build()
publisher.start()
publisher.publish(direct_message, Topic.of("chronos/events/power/failure"))
```

#### 3. Update Topic Naming

Solace uses `/` as topic separators, while NATS uses `.`. Update your topic names:

- NATS: `chronos.events.power.failure`
- Solace: `chronos/events/power/failure`

Or create a topic mapping utility to handle both formats.

#### 4. Update Docker Compose

Remove the NATS service from `docker-compose.yml` and update service dependencies:

```yaml
# Remove or comment out:
# nats:
#   ...

# Update service environment variables to use Solace
services:
  agent-service:
    environment:
      SOLACE_HOST: ${SOLACE_HOST}
      SOLACE_PORT: ${SOLACE_PORT}
      SOLACE_USERNAME: ${SOLACE_USERNAME}
      SOLACE_PASSWORD: ${SOLACE_PASSWORD}
      SOLACE_VPN: ${SOLACE_VPN}
```

#### 5. Connection Abstraction Layer

Create an abstraction layer in `infra/shared/` to support both brokers:

```python
# infra/shared/message_broker.py
from abc import ABC, abstractmethod

class MessageBroker(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: bytes):
        pass
    
    @abstractmethod
    async def subscribe(self, topic: str, callback):
        pass

class NATSBroker(MessageBroker):
    # NATS implementation
    
class SolaceBroker(MessageBroker):
    # Solace implementation

# Factory pattern
def create_broker(broker_type: str) -> MessageBroker:
    if broker_type == "nats":
        return NATSBroker()
    elif broker_type == "solace":
        return SolaceBroker()
    else:
        raise ValueError(f"Unknown broker type: {broker_type}")
```

#### 6. Testing the Migration

1. **Test locally with NATS** to ensure everything works
2. **Set up Solace PubSub+** (cloud or on-premises)
3. **Update environment variables** to point to Solace
4. **Run integration tests** to verify message flow
5. **Monitor message delivery** and latency
6. **Gradually migrate services** one at a time

### Solace PubSub+ Setup Options

#### Option 1: Solace Cloud (Recommended for Quick Start)

1. Sign up at https://console.solace.cloud
2. Create a messaging service
3. Get connection details from the service dashboard
4. Update environment variables with connection details

#### Option 2: Solace PubSub+ Software (On-Premises)

1. Download Solace PubSub+ Software from https://solace.com/downloads
2. Run in Docker:
   ```bash
   docker run -d -p 8080:8080 -p 55555:55555 -p 8008:8008 -p 1883:1883 -p 8000:8000 -p 5672:5672 -p 9000:9000 -p 2222:2222 --shm-size=2g --env username_admin_globalaccesslevel=admin --env username_admin_password=admin --name=solace solace/solace-pubsub-standard
   ```
3. Access management UI at http://localhost:8080
4. Configure VPNs and client profiles

### Broker Feature Comparison

| Feature | NATS | Solace PubSub+ |
|---------|------|----------------|
| Local Development | ✅ Easy | ⚠️ Requires setup |
| Production Ready | ⚠️ Limited | ✅ Enterprise-grade |
| High Availability | ⚠️ Basic | ✅ Advanced |
| Message Persistence | ⚠️ JetStream | ✅ Guaranteed Delivery |
| Topic Routing | ✅ Basic | ✅ Advanced |
| Security | ⚠️ Basic | ✅ Enterprise |
| Monitoring | ⚠️ Basic | ✅ Comprehensive |

### Rollback Plan

If issues occur during migration:

1. Revert environment variables to NATS
2. Redeploy services with NATS configuration
3. Investigate issues in staging environment
4. Fix and retry migration

## Shared Utilities

Common utilities for:
- Event serialization/deserialization
- Service discovery
- Health checks
- Logging
- Configuration management
- Message broker abstraction (NATS/Solace)

## Deployment

### Local Development

```bash
# Start infrastructure
docker-compose -f infra/docker-compose.yml up -d

# Start application services (from root)
docker-compose up -d
```

### Production

See main README.md for production deployment instructions.

## Environment Variables

See `env.example` in this directory (`infra/env.example`) for all required environment variables. Copy it to `.env` in the root directory:

```bash
cp infra/env.example .env
```

Then update the values as needed for your environment.
