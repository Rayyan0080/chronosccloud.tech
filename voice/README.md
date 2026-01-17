# Voice Services

Voice processing and interaction services for Project Chronos.

## Overview

This service handles voice input processing, speech-to-text, and voice commands.

## Development

[Add service-specific setup instructions here]

## Environment Variables

- `RABBITMQ_HOST`: RabbitMQ host
- `RABBITMQ_PORT`: RabbitMQ port
- `RABBITMQ_USER`: RabbitMQ username
- `RABBITMQ_PASS`: RabbitMQ password
- `VOICE_PORT`: Service port
- `VOICE_SAMPLE_RATE`: Audio sample rate (default: 16000)

## Events

### Consumed Events
- `crisis.alert` (for voice alerts)

### Published Events
- `voice.command`
- `voice.transcription`
- `voice.status`

