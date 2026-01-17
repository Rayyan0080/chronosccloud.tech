"""
ElevenLabs Voice Output Client

Provides text-to-speech functionality using ElevenLabs API with console fallback.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env from project root (1 level up from voice/)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip

logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ElevenLabsClient:
    """ElevenLabs TTS client with console fallback."""

    def __init__(self):
        """Initialize the ElevenLabs client."""
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            logger.info(f"ElevenLabs enabled (voice_id: {self.voice_id[:10]}...)")
        else:
            logger.info("ElevenLabs API key not set, using console fallback")

    def speak(self, text: str, event_type: str = "info") -> None:
        """
        Convert text to speech using ElevenLabs API, or fallback to console.

        Args:
            text: Text to speak
            event_type: Type of event (for console formatting)
        """
        if self.enabled:
            try:
                self._speak_elevenlabs(text)
            except Exception as e:
                logger.warning(f"ElevenLabs API failed: {e}, falling back to console")
                self._speak_console(text, event_type)
        else:
            self._speak_console(text, event_type)

    def _speak_elevenlabs(self, text: str) -> None:
        """Speak using ElevenLabs API."""
        try:
            import requests

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            }

            data = {
                "text": text,
                "model_id": "eleven_turbo_v2",  # Updated model (eleven_monolingual_v1 is deprecated on free tier)
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5,
                },
            }

            response = requests.post(url, json=data, headers=headers, timeout=10)

            if response.status_code == 200:
                # Save audio to temporary file and play
                import tempfile
                import subprocess
                import platform

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name

                # Play audio based on platform
                system = platform.system()
                if system == "Windows":
                    os.startfile(tmp_file_path)
                elif system == "Darwin":  # macOS
                    subprocess.run(["afplay", tmp_file_path], check=False)
                else:  # Linux
                    subprocess.run(["mpg123", tmp_file_path], check=False)

                # Clean up after a delay
                import threading
                import time

                def cleanup():
                    time.sleep(5)
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass

                threading.Thread(target=cleanup, daemon=True).start()

                print(f"\n[VOICE] Audio played successfully: {text[:50]}...\n")
                logger.info(f"[VOICE] Spoke: {text[:50]}...")
            else:
                # Provide more detailed error information
                error_msg = f"ElevenLabs API error: {response.status_code}"
                try:
                    error_detail = response.json()
                    if "detail" in error_detail:
                        error_msg += f" - {error_detail['detail']}"
                except:
                    pass
                
                if response.status_code == 401:
                    error_msg += " (Unauthorized - check your API key and ensure 'Text to Speech' access is enabled)"
                elif response.status_code == 404:
                    error_msg += " (Not Found - check your voice ID)"
                
                raise Exception(error_msg)

        except ImportError:
            logger.warning("requests library not installed, using console fallback")
            self._speak_console(text, "info")
        except Exception as e:
            logger.error(f"ElevenLabs API error: {e}")
            raise

    def _speak_console(self, text: str, event_type: str) -> None:
        """Fallback to console output with formatting."""
        # Color codes for different event types
        colors = {
            "critical": "\033[91m",  # Red
            "error": "\033[93m",     # Yellow
            "warning": "\033[95m",   # Magenta
            "info": "\033[94m",      # Blue
            "autonomy": "\033[96m",  # Cyan
        }
        reset = "\033[0m"
        
        color = colors.get(event_type, colors["info"])
        
        print(f"\n{color}{'=' * 60}")
        print(f"[VOICE ANNOUNCEMENT]")
        print(f"{'=' * 60}")
        print(f"{text}")
        print(f"{'=' * 60}{reset}\n")
        
        logger.info(f"[VOICE] Console output: {text}")


# Global instance
_client: Optional[ElevenLabsClient] = None


def get_client() -> ElevenLabsClient:
    """Get or create the global ElevenLabs client instance."""
    global _client
    if _client is None:
        _client = ElevenLabsClient()
    return _client


def speak_power_failure(sector_id: str, severity: str, voltage: float, load: float) -> None:
    """
    Announce power failure event.

    Args:
        sector_id: Affected sector
        severity: Event severity
        voltage: Current voltage
        load: Current load percentage
    """
    severity_text = {
        "critical": "CRITICAL",
        "error": "ERROR",
        "warning": "WARNING",
        "info": "INFORMATION",
    }.get(severity, "ALERT")

    text = (
        f"Power failure detected in {sector_id}. "
        f"Severity: {severity_text}. "
        f"Voltage: {voltage:.1f} volts. "
        f"Load: {load:.1f} percent."
    )

    client = get_client()
    client.speak(text, event_type=severity)


def speak_autonomy_takeover(plan_name: str, sector_id: str) -> None:
    """
    Announce autonomy takeover event.

    Args:
        plan_name: Name of the recovery plan
        sector_id: Affected sector
    """
    text = (
        f"High autonomy mode activated. "
        f"Automatically executing recovery plan: {plan_name} "
        f"for sector {sector_id}."
    )

    client = get_client()
    client.speak(text, event_type="autonomy")

