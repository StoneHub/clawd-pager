# Clawd Pager - Universal AI Remote Control

## Vision

The M5StickC Plus pager serves as a **universal remote control** for all AI agents in Monroe's ecosystem. Whether at the desk working with Claude Code, or out on the farm within WiFi range, the pager provides:

- **Status at a glance** - What are my AI agents doing?
- **Quick responses** - Yes/No with buttons, voice for complex answers
- **Proactive alerts** - Agents can wake the pager to ask questions
- **Intelligent routing** - Responses go to the right agent automatically

---

## User Scenarios

### Scenario 1: Docked at Desk (Claude Code)

```
Monroe is coding with Claude Code. The pager sits on a charging dock.

1. Claude Code uses tools → Pager shows "AGENT ACTIVE: Edit"
2. Matrix animation plays, tool names cycle through
3. Claude asks "Deploy to production?" → Pager shows QUESTION mode
4. Monroe presses A (Yes) → Response routes back to Claude Code
5. Claude continues with deployment
```

### Scenario 2: Mobile on Farm (Clawdbot)

```
Monroe is feeding chickens. Pager is in pocket (sleeping to save battery).

1. Clawdbot (via Telegram) needs approval for something
2. Bridge sends WAKE signal → Pager vibrates/beeps, wakes from sleep
3. Pager shows: "Clawdbot asks: Schedule vet appointment for Thursday?"
4. Monroe presses A (Yes) → Response routes to Clawdbot
5. Clawdbot confirms: "Done! Appointment scheduled."
6. Pager shows confirmation briefly, returns to sleep
```

### Scenario 3: Voice Command to Clawdbot

```
Monroe pulls pager from pocket, wants to ask Clawdbot something.

1. Holds Button B → "LISTENING..." with waveform animation
2. Says: "What's on my calendar today?"
3. Releases B → "PROCESSING..." (Whisper transcription)
4. Pager shows: "Send to Clawdbot: 'What's on my calendar today?'"
5. Monroe presses A to confirm (or B to cancel/re-record)
6. Clawdbot responds with Haiku-formatted summary for tiny screen
7. Pager displays: "3 events today: 9am Standup, 2pm Vet, 6pm Dinner"
```

### Scenario 4: Status Check

```
Monroe wants a quick status update.

1. Presses Button A → "Getting status..."
2. Request goes to Clawdbot (it has the context)
3. Clawdbot checks: active Claude Code sessions, pending tasks, calendar, etc.
4. Returns smart summary: "Claude Code: idle. Next: Vet at 2pm. No pending tasks."
5. Pager displays summary for 10 seconds, returns to idle/sleep
```

### Scenario 5: Claude Code Question with Voice Response

```
Claude Code asks a complex question that needs more than Yes/No.

1. Claude: "Which authentication method: OAuth, JWT, or Session cookies?"
2. Pager shows question with "[A] = Yes | Hold [B] = Voice"
3. Monroe holds B: "Use JWT with refresh tokens"
4. Transcription shown, A to confirm
5. Response routes back to Claude Code with the voice answer
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER (Monroe)                                │
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │   M5StickC Pager  │                            │
│                    │   192.168.50.85   │                            │
│                    │                   │                            │
│                    │  [A] [B] [Voice]  │                            │
│                    └─────────┬─────────┘                            │
│                              │                                       │
│                    UDP Audio │ ESPHome API                          │
│                              │                                       │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Bridge (Pi)       │
                    │   192.168.50.50     │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ Request Queue │  │  ← Tracks who asked what
                    │  │               │  │
                    │  │ {source: CC,  │  │
                    │  │  question: ?} │  │
                    │  └───────────────┘  │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ Whisper STT   │  │  ← Voice transcription
                    │  └───────────────┘  │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ Claude Haiku  │  │  ← Quick answers
                    │  └───────────────┘  │
                    │                     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼─────┐  ┌───────▼───────┐  ┌────▼────┐
    │  Claude Code  │  │   Clawdbot    │  │ Future  │
    │   (fcfdev)    │  │  (Telegram)   │  │ Agents  │
    │               │  │               │  │         │
    │  PreToolUse   │  │  /pager cmd   │  │   ...   │
    │  PostToolUse  │  │  wake_pager() │  │         │
    │  AskQuestion  │  │               │  │         │
    └───────────────┘  └───────────────┘  └─────────┘
```

---

## Request Queue Design

The bridge maintains a queue of pending interactions:

```python
pending_requests = {
    "req_001": {
        "source": "claude_code",           # or "clawdbot"
        "type": "question",                # question, alert, status
        "question": "Deploy to prod?",
        "options": ["yes", "no"],          # or None for voice
        "callback_url": "http://...",      # how to respond
        "timestamp": "2026-01-31T20:00:00",
        "timeout": 300,                    # seconds before expiry
        "priority": "normal"               # or "urgent" (wakes device)
    }
}
```

### Response Routing

When user responds (button or voice):
1. Bridge looks up the pending request
2. Formats response appropriately for the source
3. Sends to callback:
   - Claude Code: POST to /agent/response endpoint
   - Clawdbot: Send Telegram message or call API

---

## Display Modes

| Mode | Trigger | Display | Actions |
|------|---------|---------|---------|
| **IDLE** | Default | Clock, weather, battery | A=Status, B=Voice |
| **DOCKED** | Charging | Ambient animation, clock | A=Status, B=Voice |
| **AGENT** | Claude Code working | Matrix effect, tool name | Watch only |
| **LISTENING** | B held | Waveform animation | Release to process |
| **PROCESSING** | After voice | Spinner | Wait |
| **QUESTION** | Agent asks | Question + options | A=Yes, B=No, Hold B=Voice |
| **CONFIRM** | After voice | Transcription | A=Send, B=Cancel |
| **RESPONSE** | Answer received | Formatted text | Auto-dismiss |
| **ALERT** | Urgent | Red flash, tone | A=Acknowledge |
| **SLEEP** | Timeout/mobile | Screen off | Wake on urgent |

---

## Button Behavior

### Button A (Left)
| Context | Short Press | Long Press (3s) |
|---------|-------------|-----------------|
| IDLE | Get status from Clawdbot | Enter sleep |
| QUESTION | Answer "Yes" | - |
| CONFIRM | Send message | - |
| RESPONSE | Dismiss | - |
| ALERT | Acknowledge | - |

### Button B (Right)
| Context | Short Press | Long Press (400ms+) |
|---------|-------------|---------------------|
| IDLE | Return home | Voice command |
| QUESTION | Answer "No" | Voice response |
| CONFIRM | Cancel/re-record | Re-record |
| RESPONSE | Dismiss | - |
| LISTENING | - | (Release to stop) |

---

## API Endpoints (Bridge)

### From Agents (Claude Code, Clawdbot)

```
POST /pager/question
{
    "source": "clawdbot",
    "question": "Schedule vet for Thursday?",
    "options": ["yes", "no"],
    "priority": "normal",       # or "urgent" to wake
    "callback_url": "http://clawdbot.local/response"
}

POST /pager/alert
{
    "source": "claude_code",
    "text": "Build failed!",
    "priority": "urgent"
}

POST /pager/status
{
    "source": "claude_code",
    "text": "Working on auth module",
    "tool": "Edit"
}
```

### From Pager (Button/Voice responses)

```
POST /bridge/response
{
    "request_id": "req_001",
    "response_type": "button",   # or "voice"
    "value": "yes"               # or transcribed text
}
```

### To Pager (ESPHome services)

```
set_display(text, mode)     # Update display
alert(text)                 # Alert with tone
wake()                      # Wake from sleep
set_question(question, options, request_id)  # Question mode
```

---

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] ESPHome firmware with display modes
- [x] Bridge with ESPHome API connection
- [x] Voice capture with Whisper STT
- [x] Claude Code hooks (AGENT mode)
- [x] Basic alert/display endpoints
- [ ] Fix Claude API for voice answers

### Phase 2: Request Queue
- [ ] Implement pending_requests queue in bridge
- [ ] Add request_id tracking
- [ ] Implement response routing
- [ ] Add timeout handling

### Phase 3: Question Flow
- [ ] Add QUESTION mode to pager with request_id
- [ ] Handle A/B button responses
- [ ] Route responses back to source
- [ ] Add CONFIRM mode for voice responses

### Phase 4: Clawdbot Integration
- [ ] Add /pager skill to Clawdbot
- [ ] Implement wake_pager() function
- [ ] Add status summary generation
- [ ] Test end-to-end flow

### Phase 5: Polish
- [ ] Deep sleep with wake-on-urgent
- [ ] Battery optimization
- [ ] Error handling and retries
- [ ] Dashboard improvements

---

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `bridge.py` | Add request queue, routing, new endpoints |
| `clawd-pager.yaml` | Add CONFIRM mode, wake service |
| `claude_hook.py` | Handle AskUserQuestion responses |
| `.claude/commands/pager.md` | Claude Code skill |
| `clawdbot/skills/pager.js` | Clawdbot skill |

---

## Success Criteria

1. **Desk Mode**: See Claude Code activity, answer questions with buttons
2. **Mobile Mode**: Clawdbot can wake pager, get responses
3. **Voice**: Speak command, confirm, send to correct agent
4. **Status**: One button press = smart summary
5. **Routing**: Responses go to the right place automatically
