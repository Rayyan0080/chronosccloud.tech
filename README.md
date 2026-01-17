# Project Chronos

A software-only digital twin crisis system built with event-driven architecture.

## Architecture Overview

Project Chronos is designed as a distributed system with the following components:

- **qnx/**: QNX-based services and integrations
- **agents/**: Autonomous agent services
- **ai/**: AI/ML services and models
- **voice/**: Voice processing and interaction services
- **dashboard/**: Web-based monitoring and control dashboard
- **infra/**: Infrastructure as code, deployment configs, and shared utilities
- **docs/**: Documentation and specifications

### Design Principles

- **Demo-first**: Optimized for rapid demonstration and iteration
- **Stable**: Production-ready with error handling and resilience
- **Minimal**: Lean implementations without unnecessary complexity
- **Event-driven**: JSON-based event messaging between services
- **Service-oriented**: Small, independently runnable services
- **Fault-tolerant**: Mocks and fallbacks for external integrations

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Git
- Node.js 18+ (for local development)
- Python 3.10+ (for AI/ML services)

## Quick Start

### Using Docker Compose

1. **Clone and navigate to the repository:**
   ```bash
   cd Chronos-Cloud
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop all services:**
   ```bash
   docker-compose down
   ```

5. **Rebuild services after changes:**
   ```bash
   docker-compose up -d --build
   ```

### Service Endpoints

Once running, services will be available at:

- **Dashboard**: http://localhost:3000
- **Event Bus (RabbitMQ Management)**: http://localhost:15672 (guest/guest)
- **API Gateway**: http://localhost:8080

### Development Workflow

1. **Start infrastructure services only:**
   ```bash
   docker-compose up -d rabbitmq redis postgres
   ```

2. **Run services locally** (see individual service READMEs in each directory)

3. **Run full stack:**
   ```bash
   docker-compose up
   ```

## Project Structure

```
Chronos-Cloud/
├── qnx/              # QNX services and integrations
├── agents/           # Autonomous agent services
├── ai/               # AI/ML services
├── voice/            # Voice processing services
├── dashboard/        # Web dashboard frontend
├── infra/            # Infrastructure configs and shared utilities
│   ├── docker/       # Dockerfiles and compose configs
│   ├── k8s/          # Kubernetes manifests (optional)
│   └── shared/       # Shared libraries and utilities
└── docs/             # Documentation
```

## Event-Driven Architecture

All services communicate via JSON events through a message broker (RabbitMQ). Events follow this structure:

```json
{
  "eventType": "crisis.alert",
  "timestamp": "2024-01-01T12:00:00Z",
  "source": "agent.sensor-01",
  "payload": {
    "severity": "high",
    "location": "building-a",
    "details": {}
  },
  "correlationId": "uuid-here"
}
```

### Event Types

- `crisis.alert`: Crisis detection event
- `crisis.update`: Status update on ongoing crisis
- `crisis.resolved`: Crisis resolution notification
- `agent.status`: Agent health/status update
- `voice.command`: Voice command received
- `ai.prediction`: AI model prediction result

## Local Development

### Environment Variables

Create a `.env` file in the root directory:

```env
# Message Broker
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=chronos
POSTGRES_PASS=chronos
POSTGRES_DB=chronos

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Services
DASHBOARD_PORT=3000
API_GATEWAY_PORT=8080
```

### Running Individual Services

Each service directory contains its own README with specific instructions. Generally:

1. Install dependencies
2. Set environment variables
3. Run the service (usually `npm start`, `python main.py`, etc.)

## Testing

Run tests for all services:

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

Or test individual services (see service-specific READMEs).

## Contributing

1. Create a feature branch
2. Make changes in the appropriate service directory
3. Update documentation in `docs/`
4. Test locally with docker-compose
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue in the repository.

