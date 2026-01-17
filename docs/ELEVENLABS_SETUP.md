# ElevenLabs Voice Setup Guide

This guide shows you how to set up ElevenLabs API for voice announcements in Project Chronos.

---

## What is ElevenLabs?

ElevenLabs provides text-to-speech (TTS) API that converts text into natural-sounding voice. In Project Chronos, it's used to announce:
- **Power failure events**: "Power failure detected in sector-1..."
- **Autonomy takeover**: "High autonomy mode activated..."

---

## Step-by-Step Setup

### Step 1: Sign Up for ElevenLabs

1. **Visit**: https://elevenlabs.io
2. **Click** "Sign Up" or "Get Started" button (usually top right)
3. **Fill out registration form**:
   - Email address
   - Password
   - Name (optional)
4. **Verify your email** (check inbox/spam folder)
5. **Complete any onboarding steps**

### Step 2: Create API Key

1. **Log in** to your ElevenLabs account
2. **Go to your Profile**:
   - Click your profile icon (usually top right)
   - Or go to: https://elevenlabs.io/app/settings/api-keys
3. **Navigate to API Keys section**:
   - Look for "API Keys" or "API Settings" in the menu
   - Click on it
4. **Create new API key**:
   - Click "Create API Key" or "+ New Key" button
   - Give it a name (e.g., "Chronos Project")
   - Click "Create" or "Generate"
5. **Copy the API key**:
   - **Important**: Copy it immediately - you won't see it again!
   - It looks like: `sk_2e10035416f48fa7752e35eb79ec491848d982d14d17d327`

### Step 3: (Optional) Choose a Voice

1. **Go to Voices section**:
   - Navigate to: https://elevenlabs.io/app/voices
   - Or click "Voices" in the main menu
2. **Browse available voices**:
   - You can listen to voice samples
   - Choose one you like
3. **Copy the Voice ID**:
   - Click on a voice to see details
   - Copy the Voice ID (e.g., `21m00Tcm4TlvDq8ikWAM`)
   - **Note**: You can skip this - system uses a default voice

### Step 4: Add to `.env` File

1. **Open your `.env` file** in the project root:

   **Windows (PowerShell):**
   ```powershell
   notepad .env
   ```

   **Mac/Linux:**
   ```bash
   nano .env
   ```

2. **Add ElevenLabs configuration**:

   ```bash
   # ElevenLabs Voice API
   ELEVENLABS_API_KEY=sk-your-api-key-here
   ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
   ```

   **Example:**
   ```bash
   ELEVENLABS_API_KEY=sk-abc123xyz789def456ghi012jkl345mno678
   ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
   ```

3. **Save and close** the file

### Step 5: Set Environment Variables (Alternative)

If you prefer to set environment variables directly:

**Windows (PowerShell):**
```powershell
$env:ELEVENLABS_API_KEY="sk-your-api-key-here"
$env:ELEVENLABS_VOICE_ID="21m00Tcm4TlvDq8ikWAM"
```

**Mac/Linux:**
```bash
export ELEVENLABS_API_KEY="sk-your-api-key-here"
export ELEVENLABS_VOICE_ID="21m00Tcm4TlvDq8ikWAM"
```

---

## Verification

### Test the Setup

1. **Start the crisis generator**:
   ```bash
   cd agents
   python crisis_generator.py
   ```

2. **Trigger a power failure**:
   - Press `f` in the terminal
   - Press Enter

3. **Listen for voice announcement**:
   - You should hear audio: "Power failure detected in sector-1..."
   - Or see console output if audio doesn't play

### Check Logs

Look for these messages in the terminal:

**Success:**
```
[VOICE] Spoke: Power failure detected in sector-1...
```

**Fallback (if API fails):**
```
ElevenLabs API failed: ..., falling back to console
============================================================
[VOICE ANNOUNCEMENT]
============================================================
Power failure detected in sector-1...
============================================================
```

---

## Free Tier Limits

- **10,000 characters/month** (free tier)
- Perfect for development and demos
- No credit card required
- Resets monthly

### Check Your Usage

1. Go to: https://elevenlabs.io/app/settings/usage
2. See your current usage and remaining quota

---

## Troubleshooting

### Problem: "ElevenLabs API key not set"

**Solution:**
1. Check your `.env` file has `ELEVENLABS_API_KEY=...`
2. Make sure there are no spaces around the `=` sign
3. Verify the API key starts with `sk-`
4. Restart your agent services after adding the key

### Problem: "ElevenLabs API error: 401"

**Solution:**
1. Check your API key is correct (no typos)
2. Make sure you copied the entire key
3. Try generating a new API key
4. Verify you're logged into the correct ElevenLabs account

### Problem: "ElevenLabs API error: 429"

**Solution:**
- You've exceeded your free tier limit (10,000 chars/month)
- Wait for monthly reset, or upgrade to paid plan
- System will automatically use console fallback

### Problem: Audio not playing

**Solution:**
1. **Windows**: Should play automatically
2. **Mac**: Make sure `afplay` is available (usually is)
3. **Linux**: Install `mpg123`:
   ```bash
   sudo apt-get install mpg123  # Debian/Ubuntu
   sudo yum install mpg123       # RHEL/CentOS
   ```

### Problem: Voice ID not working

**Solution:**
1. Check the Voice ID is correct
2. Make sure the voice exists in your account
3. Try using the default voice ID: `21m00Tcm4TlvDq8ikWAM`
4. Or leave `ELEVENLABS_VOICE_ID` unset to use default

---

## Available Voices

### Default Voice
- **ID**: `21m00Tcm4TlvDq8ikWAM`
- **Name**: Rachel (English, female)
- **Use**: If you don't set `ELEVENLABS_VOICE_ID`

### Browse More Voices

1. Visit: https://elevenlabs.io/app/voices
2. Listen to voice samples
3. Click on a voice to see its ID
4. Copy the ID and add to `.env`

### Popular Voice IDs

- `21m00Tcm4TlvDq8ikWAM` - Rachel (Default, English, Female)
- `AZnzlk1XvdvUeBnXmlld` - Domi (English, Female)
- `EXAVITQu4vr4xnSDxMaL` - Bella (English, Female)
- `ErXwobaYiN019PkySvjV` - Antoni (English, Male)
- `MF3mGyEYCl7XYWbV9V6O` - Elli (English, Female)

---

## How It Works

### Event Flow

1. **Power Failure Event**:
   ```
   Crisis Generator → Publishes event → Voice announcement triggered
   ```

2. **Autonomy Takeover**:
   ```
   Autonomy Router → Executes action → Voice announcement triggered
   ```

### Code Integration

The voice system is integrated into:
- `agents/crisis_generator.py` - Announces power failures
- `agents/autonomy_router.py` - Announces autonomy takeovers

### Fallback Behavior

If ElevenLabs API is unavailable:
- System automatically uses console output
- Color-coded formatting for different event types
- No errors - system continues working normally

---

## Example Configuration

### Complete `.env` Example

```bash
# ElevenLabs Voice API
ELEVENLABS_API_KEY=sk-abc123xyz789def456ghi012jkl345mno678
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Other APIs (optional)
GEMINI_API_KEY=your_gemini_key
SOLACE_HOST=xxx.messaging.solace.cloud
```

---

## Quick Reference

### URLs
- **Sign Up**: https://elevenlabs.io
- **API Keys**: https://elevenlabs.io/app/settings/api-keys
- **Voices**: https://elevenlabs.io/app/voices
- **Usage**: https://elevenlabs.io/app/settings/usage

### Environment Variables
```bash
ELEVENLABS_API_KEY=sk-your-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Optional
```

### Free Tier
- **10,000 characters/month**
- Resets monthly
- No credit card required

---

## Next Steps

After setting up ElevenLabs:

1. ✅ Test with crisis generator (press `f`)
2. ✅ Test with autonomy router (toggle to HIGH)
3. ✅ Check audio playback works
4. ✅ Monitor usage in ElevenLabs dashboard

---

## Need Help?

- **ElevenLabs Docs**: https://elevenlabs.io/docs
- **API Reference**: https://elevenlabs.io/docs/api-reference
- **Support**: Available in ElevenLabs dashboard

---

**You're all set! 🎤**

Your voice announcements will now play automatically when critical events occur!

