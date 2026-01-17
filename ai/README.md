# AI/ML Services

AI and machine learning services for Project Chronos.

## Overview

This service provides AI/ML capabilities including prediction, anomaly detection, and decision support.

## Development

[Add service-specific setup instructions here]

## Environment Variables

- `RABBITMQ_HOST`: RabbitMQ host
- `RABBITMQ_PORT`: RabbitMQ port
- `RABBITMQ_USER`: RabbitMQ username
- `RABBITMQ_PASS`: RabbitMQ password
- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port
- `AI_MODEL_PATH`: Path to AI model files
- `AI_USE_GPU`: Enable GPU acceleration (true/false)

## Events

### Consumed Events
- `crisis.alert`
- `agent.status`
- `voice.command`

### Published Events
- `ai.prediction`
- `ai.anomaly`
- `ai.recommendation`

