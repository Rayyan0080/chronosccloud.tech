# QNX Services

QNX-based services and integrations for Project Chronos.

## Overview

This service handles QNX-specific integrations and real-time operations.

## Development

[Add service-specific setup instructions here]

## Environment Variables

- `RABBITMQ_HOST`: RabbitMQ host
- `RABBITMQ_PORT`: RabbitMQ port
- `RABBITMQ_USER`: RabbitMQ username
- `RABBITMQ_PASS`: RabbitMQ password
- `QNX_ENDPOINT`: QNX system endpoint
- `QNX_TIMEOUT`: Request timeout in milliseconds

## Events

### Consumed Events
- `crisis.alert`
- `agent.status`

### Published Events
- `qnx.status`
- `qnx.response`

