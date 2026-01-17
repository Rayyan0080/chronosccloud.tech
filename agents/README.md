# Agent Services

Autonomous agent services for Project Chronos.

## Overview

This service manages autonomous agents that monitor, detect, and respond to crisis situations.

## Development

[Add service-specific setup instructions here]

## Environment Variables

- `RABBITMQ_HOST`: RabbitMQ host
- `RABBITMQ_PORT`: RabbitMQ port
- `RABBITMQ_USER`: RabbitMQ username
- `RABBITMQ_PASS`: RabbitMQ password
- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_PORT`: PostgreSQL port
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASS`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `AGENT_POLL_INTERVAL`: Polling interval in milliseconds
- `AGENT_TIMEOUT`: Agent operation timeout in milliseconds

## Events

### Consumed Events
- `crisis.alert`
- `voice.command`
- `ai.prediction`

### Published Events
- `agent.status`
- `crisis.alert`
- `crisis.update`
- `crisis.resolved`

