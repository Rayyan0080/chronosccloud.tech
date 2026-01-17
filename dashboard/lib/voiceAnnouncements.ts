/**
 * Voice announcement utility for dashboard events
 * Uses browser's Web Speech API to announce new events
 */

// Track announced events to avoid duplicates
const announcedEventIds = new Set<string>();

// Track pending timeouts so we can cancel them
const pendingTimeouts: number[] = [];

// Track active utterances so we can cancel them
const activeUtterances: SpeechSynthesisUtterance[] = [];

// Global enabled state
let voiceEnabled = true;

// Periodic check to ensure speech stops if voice is disabled
let periodicCheckInterval: number | null = null;

function startPeriodicCheck(): void {
  if (periodicCheckInterval !== null) {
    return; // Already running
  }
  
  periodicCheckInterval = window.setInterval(() => {
    if (!voiceEnabled && 'speechSynthesis' in window) {
      // If voice is disabled but speech is still speaking, cancel it aggressively
      if (speechSynthesis.speaking || speechSynthesis.pending) {
        console.log('[VOICE] Periodic check: Voice disabled but speech active, FORCE canceling');
        // Try multiple methods
        speechSynthesis.pause();
        speechSynthesis.cancel();
        
        // Try to interrupt with a silent utterance
        try {
          const silentUtterance = new SpeechSynthesisUtterance('');
          silentUtterance.volume = 0;
          speechSynthesis.speak(silentUtterance);
          speechSynthesis.cancel();
        } catch (e) {
          // Ignore errors
        }
      }
    }
  }, 50); // Check every 50ms (more frequent)
}

function stopPeriodicCheck(): void {
  if (periodicCheckInterval !== null) {
    clearInterval(periodicCheckInterval);
    periodicCheckInterval = null;
  }
}

/**
 * Generate announcement text for an event
 */
function generateAnnouncementText(event: any): string | null {
  const topic = event.topic || '';
  const payload = event.payload || {};
  const details = payload.details || {};

  // Power failure events
  if (topic.includes('power.failure')) {
    const sectorId = payload.sector_id || 'unknown sector';
    const severity = payload.severity || 'alert';
    const voltage = details.voltage || 0;
    const load = details.load || 0;
    
    const severityText = severity.toUpperCase();
    return `Power failure detected in ${sectorId}. Severity: ${severityText}. Voltage: ${voltage.toFixed(1)} volts. Load: ${load.toFixed(1)} percent.`;
  }

  // Recovery plan events
  if (topic.includes('recovery.plan')) {
    const planName = details.plan_name || payload.summary || 'Recovery plan';
    const sectorId = payload.sector_id || details.sector_id || 'affected sector';
    return `Recovery plan generated: ${planName} for ${sectorId}.`;
  }

  // Operator status events
  if (topic.includes('operator.status')) {
    const autonomyLevel = details.autonomy_level || payload.autonomy_level || 'NORMAL';
    if (autonomyLevel === 'HIGH') {
      return `High autonomy mode activated. System will automatically execute recovery plans.`;
    } else {
      return `Autonomy level set to ${autonomyLevel}. Manual approval required for actions.`;
    }
  }

  // Audit decision events
  if (topic.includes('audit.decision')) {
    const decision = details.decision || payload.decision || 'Decision made';
    return `Audit decision: ${decision}.`;
  }

  // System action events
  if (topic.includes('system.action')) {
    const action = details.action || payload.action || 'Action executed';
    return `System action: ${action}.`;
  }

  // Approval required events
  if (topic.includes('approval.required')) {
    const action = details.action || payload.action || 'Action';
    return `Approval required for: ${action}.`;
  }

  // Agent compare events
  if (topic.includes('agent.compare')) {
    const frameworks = details.frameworks || [];
    if (frameworks.length > 0) {
      return `Agent comparison completed. ${frameworks.length} frameworks evaluated.`;
    }
    return `Agent comparison initiated.`;
  }

  // Generic event announcement
  const summary = payload.summary || 'New event';
  return `${summary}.`;
}

/**
 * Set voice enabled state
 */
export function setVoiceEnabled(enabled: boolean): void {
  console.log('[VOICE] Setting voice enabled to:', enabled);
  
  // Update state FIRST
  voiceEnabled = enabled;
  
  if (!enabled) {
    // Cancel all pending and ongoing speech IMMEDIATELY
    console.log('[VOICE] Voice disabled - canceling all speech immediately');
    cancelAllSpeech();
    
    // Start periodic check to ensure speech stays stopped
    startPeriodicCheck();
    
    // Also clear the announced events set so they can be re-announced if voice is turned back on
    // (optional - remove this line if you want to keep track of what was announced)
    // announcedEventIds.clear();
  } else {
    // Stop periodic check when voice is enabled
    stopPeriodicCheck();
  }
}

/**
 * Cancel all pending and ongoing speech
 */
export function cancelAllSpeech(): void {
  console.log('[VOICE] ============================================');
  console.log('[VOICE] CANCELING ALL SPEECH');
  console.log('[VOICE] Pending timeouts:', pendingTimeouts.length);
  console.log('[VOICE] Active utterances:', activeUtterances.length);
  console.log('[VOICE] Speech speaking:', 'speechSynthesis' in window ? speechSynthesis.speaking : 'N/A');
  console.log('[VOICE] Speech pending:', 'speechSynthesis' in window ? speechSynthesis.pending : 'N/A');
  console.log('[VOICE] ============================================');
  
  // Cancel all pending timeouts
  pendingTimeouts.forEach(timeout => {
    clearTimeout(timeout);
  });
  pendingTimeouts.length = 0;

  // Cancel all speech synthesis - be VERY aggressive
  if ('speechSynthesis' in window) {
    try {
      // Method 1: Cancel immediately
      speechSynthesis.cancel();
      
      // Method 2: Pause then cancel (some browsers need this)
      speechSynthesis.pause();
      speechSynthesis.cancel();
      
      // Method 3: Cancel active utterances individually by muting them
      activeUtterances.forEach(utterance => {
        try {
          // Mute the utterance (set volume to 0)
          utterance.volume = 0;
          // Try to stop the utterance
          if (utterance.onend) {
            utterance.onend = null; // Remove callback
          }
          if (utterance.onerror) {
            utterance.onerror = null; // Remove callback
          }
          if (utterance.onstart) {
            utterance.onstart = null;
          }
          if (utterance.onboundary) {
            utterance.onboundary = null;
          }
        } catch (e) {
          console.error('[VOICE] Error canceling utterance:', e);
        }
      });
      
      // Clear active utterances list
      activeUtterances.length = 0;
      
      // Method 4: Multiple cancel attempts with delays and volume manipulation
      const cancelWithVolume = () => {
        // Try to mute any active utterances
        if (speechSynthesis.speaking || speechSynthesis.pending) {
          speechSynthesis.pause();
          speechSynthesis.cancel();
          
          // Try to interrupt with a silent utterance
          try {
            const interrupt = new SpeechSynthesisUtterance('');
            interrupt.volume = 0;
            speechSynthesis.speak(interrupt);
            speechSynthesis.cancel();
          } catch (e) {
            // Ignore
          }
        } else {
          speechSynthesis.cancel();
        }
      };
      
      // Immediate cancellation
      cancelWithVolume();
      
      // Delayed cancellations
      setTimeout(cancelWithVolume, 10);
      setTimeout(cancelWithVolume, 50);
      setTimeout(cancelWithVolume, 100);
      setTimeout(cancelWithVolume, 200);
      setTimeout(cancelWithVolume, 500);
      setTimeout(cancelWithVolume, 1000);
      
      console.log('[VOICE] All cancellation attempts completed');
    } catch (e) {
      console.error('[VOICE] Error canceling speech:', e);
    }
  }
}

/**
 * Announce an event using Web Speech API
 */
export function announceEvent(event: any): void {
  // CRITICAL: Check if voice is enabled FIRST - before ANY processing
  // Read directly from module variable (not a parameter or closure)
  const isEnabled = voiceEnabled;
  
  if (!isEnabled) {
    console.log('[VOICE] ============================================');
    console.log('[VOICE] BLOCKED: Voice disabled, skipping announcement');
    console.log('[VOICE] ============================================');
    return;
  }
  
  // Double-check (state might have changed)
  if (!voiceEnabled) {
    console.log('[VOICE] BLOCKED: Voice disabled (double check)');
    return;
  }
  
  // Triple check
  if (!voiceEnabled) {
    console.log('[VOICE] BLOCKED: Voice disabled (triple check)');
    return;
  }

  // Check if browser supports speech synthesis
  if (!('speechSynthesis' in window)) {
    console.warn('Browser does not support speech synthesis');
    return;
  }

  // Skip if already announced
  const eventId = event._id || event.event_id || JSON.stringify(event);
  if (announcedEventIds.has(eventId)) {
    return;
  }

  // Generate announcement text
  const text = generateAnnouncementText(event);
  if (!text) {
    return;
  }

  // Mark as announced
  announcedEventIds.add(eventId);

  // Create speech utterance
  const utterance = new SpeechSynthesisUtterance(text);
  
  // Configure voice settings
  utterance.rate = 1.0; // Normal speed
  utterance.pitch = 1.0; // Normal pitch
  utterance.volume = 0.8; // 80% volume

  // Try to use a more natural voice if available
  const voices = speechSynthesis.getVoices();
  const preferredVoice = voices.find(
    (voice) => voice.name.includes('Google') || voice.name.includes('Microsoft') || voice.name.includes('Samantha')
  );
  if (preferredVoice) {
    utterance.voice = preferredVoice;
  }

  // Double-check voice is still enabled before speaking
  if (!voiceEnabled) {
    console.log('[VOICE] Voice disabled just before speaking, canceling');
    return;
  }

  // Track this utterance
  activeUtterances.push(utterance);

  // Remove from active list when done
  utterance.onend = () => {
    // Check if voice was disabled during speech
    if (!voiceEnabled) {
      console.log('[VOICE] Utterance ended but voice was disabled');
    }
    const idx = activeUtterances.indexOf(utterance);
    if (idx > -1) {
      activeUtterances.splice(idx, 1);
    }
  };

  utterance.onerror = () => {
    const idx = activeUtterances.indexOf(utterance);
    if (idx > -1) {
      activeUtterances.splice(idx, 1);
    }
  };

  // Add a check in onstart to cancel if voice was disabled
  utterance.onstart = () => {
    if (!voiceEnabled) {
      console.log('[VOICE] Voice disabled during utterance start, canceling immediately');
      // Try multiple methods to stop
      utterance.volume = 0; // Set volume to 0
      speechSynthesis.pause();
      speechSynthesis.cancel();
      const idx = activeUtterances.indexOf(utterance);
      if (idx > -1) {
        activeUtterances.splice(idx, 1);
      }
    }
  };
  
  // Also check during speech (if possible)
  utterance.onboundary = () => {
    if (!voiceEnabled) {
      console.log('[VOICE] Voice disabled during speech, canceling');
      utterance.volume = 0; // Mute it
      speechSynthesis.pause();
      speechSynthesis.cancel();
    }
  };

  // Final check before speaking
  if (!voiceEnabled) {
    console.log('[VOICE] Voice disabled at final check, not speaking');
    const idx = activeUtterances.indexOf(utterance);
    if (idx > -1) {
      activeUtterances.splice(idx, 1);
    }
    return;
  }

  // Speak
  try {
    // CRITICAL: Check state MULTIPLE times right before speaking
    // Read directly from module-level variable (not closure)
    if (!voiceEnabled) {
      console.log('[VOICE] Voice disabled right before speak(), NOT speaking - ABORTING');
      const idx = activeUtterances.indexOf(utterance);
      if (idx > -1) {
        activeUtterances.splice(idx, 1);
      }
      return;
    }
    
    // Double check
    if (!voiceEnabled) {
      console.log('[VOICE] Voice disabled (double check), NOT speaking');
      const idx = activeUtterances.indexOf(utterance);
      if (idx > -1) {
        activeUtterances.splice(idx, 1);
      }
      return;
    }
    
    // Set volume to 0 if voice is disabled (extra safety)
    if (!voiceEnabled) {
      utterance.volume = 0;
      console.log('[VOICE] Voice disabled, setting volume to 0');
      return;
    }
    
    // Final check - if still disabled, don't speak
    if (!voiceEnabled) {
      console.log('[VOICE] Voice disabled at final check, NOT speaking');
      const idx = activeUtterances.indexOf(utterance);
      if (idx > -1) {
        activeUtterances.splice(idx, 1);
      }
      return;
    }
    
    // Only speak if voice is definitely enabled
    if (voiceEnabled) {
      speechSynthesis.speak(utterance);
      console.log('[VOICE] Announced:', text);
      
      // Immediately check again after speaking starts
      setTimeout(() => {
        if (!voiceEnabled) {
          console.log('[VOICE] Voice disabled immediately after speak(), canceling');
          speechSynthesis.cancel();
        }
      }, 10);
    } else {
      console.log('[VOICE] Voice disabled, NOT speaking');
      const idx = activeUtterances.indexOf(utterance);
      if (idx > -1) {
        activeUtterances.splice(idx, 1);
      }
    }
  } catch (e) {
    console.error('[VOICE] Error speaking:', e);
    const idx = activeUtterances.indexOf(utterance);
    if (idx > -1) {
      activeUtterances.splice(idx, 1);
    }
  }
}

/**
 * Get current voice enabled state
 */
export function isVoiceEnabled(): boolean {
  return voiceEnabled;
}

/**
 * Announce multiple events (only new ones)
 */
export function announceNewEvents(previousEvents: any[], currentEvents: any[], enabled?: boolean): void {
  // CRITICAL: Check state FIRST before doing ANY processing
  // If voice is disabled, do NOTHING - don't even process events
  if (!voiceEnabled) {
    console.log('[VOICE] Voice is disabled, skipping all announcements');
    return;
  }

  // Also respect the parameter if provided (for immediate updates)
  if (enabled !== undefined && !enabled) {
    console.log('[VOICE] Voice disabled via parameter, skipping all announcements');
    return;
  }

  // Double-check state again (in case it changed during processing)
  if (!voiceEnabled) {
    return;
  }

  // Create a set of previous event IDs
  const previousIds = new Set(
    previousEvents.map((e) => e._id || e.event_id || JSON.stringify(e))
  );

  // Find new events
  const newEvents = currentEvents.filter(
    (e) => {
      const id = e._id || e.event_id || JSON.stringify(e);
      return !previousIds.has(id);
    }
  );

  // Final check before queuing
  if (!voiceEnabled || newEvents.length === 0) {
    return;
  }

  console.log('[VOICE] Queuing', newEvents.length, 'new events for announcement');

  // Announce new events (in reverse order so latest is announced first)
  newEvents.reverse().forEach((event, index) => {
    // Check state before creating timeout - use a function to get current state
    const getCurrentState = () => {
      // Always read from the module-level variable, not a closure
      return voiceEnabled;
    };
    
    if (!getCurrentState()) {
      console.log('[VOICE] Voice disabled, not creating timeout for event');
      return;
    }

    // Small delay between announcements to avoid overlap
    const timeoutId = setTimeout(() => {
      // CRITICAL: Check state using the function that reads current module state
      // This ensures we get the CURRENT state, not the state when timeout was created
      const currentState = getCurrentState();
      
      if (!currentState) {
        console.log('[VOICE] Voice disabled in timeout callback, NOT announcing');
        // Remove from pending list
        const idx = pendingTimeouts.indexOf(timeoutId);
        if (idx > -1) {
          pendingTimeouts.splice(idx, 1);
        }
        return;
      }
      
      // Triple check - read directly from module
      if (!voiceEnabled) {
        console.log('[VOICE] Voice disabled (direct check), NOT announcing');
        const idx = pendingTimeouts.indexOf(timeoutId);
        if (idx > -1) {
          pendingTimeouts.splice(idx, 1);
        }
        return;
      }
      
      // Remove from pending list when executed
      const idx = pendingTimeouts.indexOf(timeoutId);
      if (idx > -1) {
        pendingTimeouts.splice(idx, 1);
      }
      
      // Final check before calling announceEvent - read current state
      if (voiceEnabled) {
        announceEvent(event);
      } else {
        console.log('[VOICE] Voice disabled at final check, NOT announcing');
      }
    }, index * 2000); // 2 second delay between announcements
    
    // Track the timeout so we can cancel it if needed
    pendingTimeouts.push(timeoutId);
  });
}

/**
 * Clear announced events (useful for testing or reset)
 */
export function clearAnnouncedEvents(): void {
  announcedEventIds.clear();
}

