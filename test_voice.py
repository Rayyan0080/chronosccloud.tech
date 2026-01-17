"""
Quick test script for ElevenLabs voice output.
"""
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.elevenlabs_client import speak_power_failure, speak_autonomy_takeover

print("=" * 60)
print("TESTING ELEVENLABS VOICE OUTPUT")
print("=" * 60)
print()

# Test 1: Power failure announcement
print("Test 1: Power failure announcement...")
speak_power_failure("sector-1", "critical", 12.5, 85.3)
print()

# Wait a moment
import time
time.sleep(2)

# Test 2: Autonomy takeover announcement
print("Test 2: Autonomy takeover announcement...")
speak_autonomy_takeover("Emergency Power Restoration", "sector-1")
print()

print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print()
print("If you heard audio, ElevenLabs is working!")
print("If you only saw console output, check your ELEVENLABS_API_KEY in .env")

