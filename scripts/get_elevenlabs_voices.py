#!/usr/bin/env python3
"""
Quick script to list all available ElevenLabs voices and their IDs.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def get_voices():
    """Fetch all voices from ElevenLabs API."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        print("[ERROR] ELEVENLABS_API_KEY not found in .env file")
        print("\nPlease add your API key to .env:")
        print("ELEVENLABS_API_KEY=sk-your-key-here")
        return
    
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {
            "xi-api-key": api_key
        }
        
        print("Fetching voices from ElevenLabs...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            voices = data.get("voices", [])
            
            if not voices:
                print("No voices found in your account.")
                return
            
            print(f"\n[OK] Found {len(voices)} voice(s):\n")
            print("=" * 80)
            
            for i, voice in enumerate(voices, 1):
                voice_id = voice.get("voice_id", "N/A")
                name = voice.get("name", "Unknown")
                description = voice.get("description", "")
                category = voice.get("category", "")
                
                print(f"\n{i}. {name}")
                print(f"   ID: {voice_id}")
                if description:
                    print(f"   Description: {description}")
                if category:
                    print(f"   Category: {category}")
                print("-" * 80)
            
            print("\n[TIP] To use a voice, add to your .env file:")
            print("   ELEVENLABS_VOICE_ID=voice_id_here")
            print("\n[TIP] Or copy one of the IDs above and update your .env file.")
            
        elif response.status_code == 401:
            print("[ERROR] Authentication failed. Please check your ELEVENLABS_API_KEY")
        else:
            print(f"[ERROR] Error: {response.status_code}")
            try:
                error = response.json()
                print(f"   {error}")
            except:
                print(f"   {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error: {e}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    get_voices()

