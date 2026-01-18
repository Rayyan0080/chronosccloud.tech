# Voice Announcements Troubleshooting Guide

## Current Architecture

**Important**: The dashboard uses **Browser Web Speech API**, not ElevenLabs, for voice announcements in the browser.

- **Dashboard (Browser)**: Uses Browser Web Speech API (native browser TTS)
- **Python Agents**: Use ElevenLabs API (but don't play audio - only generate and log)

## Troubleshooting Steps

### 1. Check if Voice is Enabled

**In the Dashboard:**
- Look for the "Voice Announcements" toggle button
- Make sure it's **ON** (should be highlighted/checked)
- Check browser console for: `[VOICE] Setting voice enabled to: true`

**Check Browser Console:**
```javascript
// Open browser console (F12) and run:
console.log('Voice enabled:', window.speechSynthesis ? 'Supported' : 'Not supported');
```

### 2. Check Browser Permissions

**Chrome/Edge:**
1. Click the lock icon in the address bar
2. Check "Sound" permission is allowed
3. Check "Automatic downloads" is allowed (if needed)

**Firefox:**
1. Go to `about:preferences#privacy`
2. Check "Autoplay" settings
3. Allow audio autoplay for the site

### 3. Check Browser Console for Errors

**Open Browser Console (F12) and look for:**
- `[VOICE] Announced: ...` - Should appear when events are announced
- `[VOICE] Error speaking: ...` - Indicates an error
- `Browser does not support speech synthesis` - Browser doesn't support TTS

**Common Errors:**
- `speechSynthesis is not defined` - Browser doesn't support Web Speech API
- `NotAllowedError` - Browser blocked audio (check permissions)
- `NetworkError` - Network issue (unlikely for local TTS)

### 4. Test Browser Speech Synthesis

**Run this in browser console:**
```javascript
if ('speechSynthesis' in window) {
  const utterance = new SpeechSynthesisUtterance('Test announcement');
  utterance.volume = 0.8;
  speechSynthesis.speak(utterance);
  console.log('Speech synthesis test: Should hear "Test announcement"');
} else {
  console.error('Browser does not support speech synthesis');
}
```

**If you don't hear anything:**
- Check system volume
- Check browser tab is not muted (look for mute icon in tab)
- Check browser audio settings

### 5. Check if Events are Being Announced

**In Browser Console, look for:**
```
[VOICE] Queuing X new events for announcement
[VOICE] Announced: <text>
```

**If you see "Queuing" but no "Announced":**
- Voice might be disabled
- Browser might be blocking speech
- Check for errors in console

### 6. Check Voice Toggle State

**The voice toggle might be off. Check:**
1. Look at the toggle button in the dashboard
2. Click it to turn it ON
3. Check console for: `[VOICE] Setting voice enabled to: true`

**If toggle doesn't work:**
- Refresh the page
- Check browser console for JavaScript errors
- Try a different browser

### 7. Browser-Specific Issues

**Chrome/Edge:**
- Make sure you're not in "Do Not Disturb" mode
- Check Windows sound settings
- Try disabling browser extensions

**Firefox:**
- Check `about:preferences#privacy` for autoplay settings
- Make sure "Block websites from automatically playing sound" is not blocking the site

**Safari:**
- Check Safari preferences → Websites → Auto-Play
- Allow auto-play for the site

### 8. System-Level Checks

**Windows:**
- Check system volume
- Check if browser is muted in Windows volume mixer
- Check Windows sound settings

**Mac:**
- Check system volume
- Check if browser is muted in Sound settings
- Check Do Not Disturb mode

**Linux:**
- Check ALSA/PulseAudio settings
- Check system volume

### 9. Check for Multiple Tabs

**If you have multiple dashboard tabs open:**
- Only one tab should have voice enabled
- Close other tabs or disable voice in them
- Multiple tabs can interfere with each other

### 10. Verify Events are Being Received

**Check if events are actually coming in:**
1. Look at the Event Feed in the dashboard
2. Check browser console for: `[VOICE] Queuing X new events`
3. If no events are queued, events might not be arriving

**To trigger test events:**
- In the crisis generator terminal, press `f` to trigger a power failure
- Check if the event appears in the dashboard
- Check if `[VOICE] Queuing` appears in console

## Using ElevenLabs Instead of Browser TTS

**Current Status**: ElevenLabs is only used by Python agents and doesn't play audio in the browser.

**To use ElevenLabs in the browser, you would need:**
1. A backend API endpoint that calls ElevenLabs
2. The browser to fetch audio from that endpoint
3. The browser to play the audio

**This is not currently implemented.** The dashboard uses Browser Web Speech API for simplicity and reliability.

## Quick Fixes

### Fix 1: Enable Voice Toggle
1. Find the voice toggle button in the dashboard
2. Click it to turn it ON
3. Refresh the page if needed

### Fix 2: Check Browser Console
1. Open browser console (F12)
2. Look for `[VOICE]` messages
3. Check for errors
4. Try the test command above

### Fix 3: Check System Volume
1. Make sure system volume is up
2. Make sure browser tab is not muted
3. Check Windows/Mac volume mixer

### Fix 4: Try Different Browser
1. Try Chrome/Edge
2. Try Firefox
3. Check if it works in a different browser

## Still Not Working?

If none of the above fixes work:

1. **Check browser console** for specific error messages
2. **Check if events are arriving** (look at Event Feed)
3. **Try the test command** in browser console
4. **Check system/browser audio settings**
5. **Try a different browser**

## Expected Behavior

**When working correctly, you should:**
- See `[VOICE] Queuing X new events` in console when events arrive
- See `[VOICE] Announced: <text>` in console when speech starts
- Hear the browser's text-to-speech voice reading the announcements
- See the voice toggle button is ON/highlighted

**The voice will announce:**
- Power failure events
- Recovery plan events
- Operator status changes
- System actions
- Transit events
- Airspace events
- Traffic events
- And more...

---

**Last Updated**: 2026-01-17

