# Voice Services

Voice processing and interaction services for Project Chronos.

## Overview

This service provides text-to-speech (TTS) functionality using ElevenLabs API for voice announcements of critical events. Falls back to console output if the API is unavailable.

## Features

- **ElevenLabs Integration**: High-quality voice synthesis for announcements
- **Console Fallback**: Automatic fallback to formatted console output
- **Event Announcements**: Voice output for:
  - Power failure events
  - Autonomy takeover events

## Setup

### ElevenLabs API (Optional)

1. **Sign up for ElevenLabs**:
   - Go to https://elevenlabs.io
   - Create an account
   - Get your API key from the dashboard

2. **Set Environment Variables**:
   ```bash
   export ELEVENLABS_API_KEY="your_api_key_here"
   export ELEVENLABS_VOICE_ID="21m00Tcm4TlvDq8ikWAM"  # Optional, uses default if not set
   ```

   Or in PowerShell:
   ```powershell
   $env:ELEVENLABS_API_KEY="your_api_key_here"
   $env:ELEVENLABS_VOICE_ID="21m00Tcm4TlvDq8ikWAM"
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r voice/requirements.txt
   ```

### Console Fallback

If `ELEVENLABS_API_KEY` is not set, the system automatically uses console output with color-coded formatting. No additional setup required.

## Usage

### Power Failure Announcements

When a power failure event is published, the system automatically announces:

```
"Power failure detected in sector-1. Severity: CRITICAL. Voltage: 0.0 volts. Load: 100.0 percent."
```

**Triggered by**: `agents/crisis_generator.py` when publishing `power.failure` events.

### Autonomy Takeover Announcements

When high autonomy mode activates and executes a recovery plan:

```
"High autonomy mode activated. Automatically executing recovery plan: Sector 1 Recovery Plan for sector sector-1."
```

**Triggered by**: `agents/autonomy_router.py` when executing recovery plans in HIGH autonomy mode.

## Voice Configuration

### Available Voices

ElevenLabs provides multiple voices. You can set a custom voice ID:

```bash
export ELEVENLABS_VOICE_ID="your_voice_id"
```

Find voice IDs in the ElevenLabs dashboard under "Voices".

### Voice Settings

The client uses these default settings:
- **Model**: `eleven_monolingual_v1`
- **Stability**: 0.5
- **Similarity Boost**: 0.5

These can be customized in `voice/elevenlabs_client.py`.

## Console Fallback Format

When ElevenLabs is unavailable, announcements are printed to console with color coding:

- **Critical**: Red
- **Error**: Yellow
- **Warning**: Magenta
- **Info**: Blue
- **Autonomy**: Cyan

Example console output:
```
============================================================
[VOICE ANNOUNCEMENT]
============================================================
Power failure detected in sector-1. Severity: CRITICAL...
============================================================
```

## Integration

Voice announcements are automatically integrated into:

1. **Crisis Generator** (`agents/crisis_generator.py`):
   - Announces power failure events
   - Includes sector, severity, voltage, and load

2. **Autonomy Router** (`agents/autonomy_router.py`):
   - Announces autonomy takeover
   - Includes plan name and sector

## Audio Playback

The system automatically plays audio based on your platform:

- **Windows**: Uses `os.startfile()`
- **macOS**: Uses `afplay` command
- **Linux**: Uses `mpg123` (must be installed)

For Linux, install mpg123:
```bash
sudo apt-get install mpg123  # Debian/Ubuntu
sudo yum install mpg123       # RHEL/CentOS
```

## Troubleshooting

### Voice Not Playing

1. **Check API Key**:
   ```bash
   echo $ELEVENLABS_API_KEY
   ```

2. **Check Console Output**:
   - If API key is missing, check console for fallback output
   - Look for `[VOICE ANNOUNCEMENT]` messages

3. **Check Logs**:
   - Look for "ElevenLabs API failed" warnings
   - Check for import errors

### Audio Playback Issues

1. **Linux**: Ensure `mpg123` is installed
2. **macOS**: `afplay` should be available by default
3. **Windows**: Should work automatically

### API Errors

- Check your ElevenLabs API key is valid
- Verify you have API credits available
- Check network connectivity

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | No | None | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | No | `21m00Tcm4TlvDq8ikWAM` | Voice ID to use |

## Code Example

```python
from voice.elevenlabs_client import speak_power_failure, speak_autonomy_takeover

# Announce power failure
speak_power_failure("sector-1", "critical", 0.0, 100.0)

# Announce autonomy takeover
speak_autonomy_takeover("Sector 1 Recovery Plan", "sector-1")
```

## Future Enhancements

- Support for multiple languages
- Custom voice settings per event type
- Audio file caching
- WebSocket streaming for real-time announcements
- Integration with dashboard for browser-based audio
