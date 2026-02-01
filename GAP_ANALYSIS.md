# Clawd Pager - Gap Analysis

## Current State vs Desired State

| Feature | Current | Desired | Gap |
|---------|---------|---------|-----|
| **Display Modes** | IDLE, LISTENING, PROCESSING, AWAITING, RESPONSE, ALERT, DOCKED, AGENT, QUESTION | Same + CONFIRM | Add CONFIRM mode |
| **Voice Capture** | Working (Whisper) | Same | None |
| **Voice Response** | Shows on pager | Same + routing | Add routing |
| **Claude Code Hooks** | PreToolUse, PostToolUse, Stop | Same + response routing | Add response callback |
| **Button A** | Briefing / Sleep | Status / Yes / Confirm | Change behavior |
| **Button B** | Voice / Home | No / Voice / Cancel | Add No response |
| **Request Queue** | None | Track pending questions | Implement queue |
| **Response Routing** | None | Route to source agent | Implement routing |
| **Clawdbot Integration** | None | Full two-way | Implement skill |
| **Wake from Sleep** | None | On urgent | Implement wake |
| **Claude API** | Error (connection) | Working | Fix API key |

---

## What's Working Now

### Firmware (clawd-pager.yaml)
- [x] All display modes render correctly
- [x] AGENT mode shows tool names (matrix animation)
- [x] QUESTION mode shows with flashing "Press A = YES"
- [x] Voice capture via PDM microphone
- [x] UDP audio streaming to bridge
- [x] Button detection and events
- [x] Buzzer/microphone conflict handled

### Bridge (bridge.py)
- [x] ESPHome API connection
- [x] Display update services
- [x] Alert service
- [x] UDP audio receiver
- [x] Whisper STT transcription
- [x] Dashboard event broadcasting
- [x] Agent event handler (TOOL_START, TOOL_END, WAITING)

### Hooks (claude_hook.py)
- [x] PreToolUse → TOOL_START → AGENT mode
- [x] PostToolUse → TOOL_END → idle timeout
- [x] Stop → WAITING → IDLE mode
- [x] Sends to bridge AND dashboard

### Dashboard
- [x] Real-time event stream
- [x] Session recording
- [x] Log export
- [ ] Button response visualization

---

## What's Broken/Missing

### Critical (Must Fix First)

1. **Claude API Connection Error**
   - Symptom: `[Error: Connection error.]` on voice response
   - Cause: ANTHROPIC_API_KEY not set when bridge starts
   - Fix: Export key before starting bridge

2. **`/pager` Skill Not Found**
   - Symptom: "Unknown skill: pager"
   - Cause: Plugin not installed in Claude Code
   - Fix: Create proper plugin structure

### Missing Features (Phase 2+)

3. **Request Queue**
   - Need: Track who asked what question
   - Why: Route responses to correct agent
   - Implementation: Dict in bridge with request_id

4. **Response Routing**
   - Need: Send button/voice responses back to source
   - Why: Claude Code needs to receive "yes" answer
   - Implementation: Callback URL or stdin injection

5. **CONFIRM Mode**
   - Need: Show transcription, let user confirm before sending
   - Why: Verify voice was transcribed correctly
   - Implementation: New display mode in firmware

6. **Button A = Status**
   - Need: Button A gets status from Clawdbot
   - Current: Button A shows calendar briefing
   - Change: Call Clawdbot status API

7. **Button B = No**
   - Need: Short press B = "No" in QUESTION mode
   - Current: Short press B = return home
   - Change: Context-aware button behavior

8. **Clawdbot Skill**
   - Need: Clawdbot can send questions to pager
   - Implementation: Node.js skill + bridge API

9. **Wake from Sleep**
   - Need: Urgent messages wake sleeping pager
   - Implementation: ESPHome deep sleep with wake pin

---

## Immediate Action Items

### Right Now (Fix Blockers)

1. **Fix Claude API**
   ```bash
   # In bridge terminal:
   export ANTHROPIC_API_KEY="sk-ant-..."
   python bridge.py
   ```

2. **Test Voice Response**
   - Hold B, say "what is 2+2", release
   - Should see answer on pager (not error)

3. **Create Plugin Properly**
   - Follow plugin-dev patterns
   - Install in Claude Code

### This Session

4. **Implement Request Queue**
   - Add to bridge.py
   - Track request_id with source

5. **Update Button Behavior**
   - A = Yes/Status (context-aware)
   - B = No/Cancel/Voice (context-aware)

6. **Add Response Routing**
   - Button response → bridge → source agent

---

## Technical Decisions Needed

| Question | Options | Recommendation |
|----------|---------|----------------|
| How does Claude Code receive responses? | A) Stdin injection B) File watcher C) API callback | B) File watcher - simplest |
| Where does request queue persist? | A) Memory B) SQLite C) Redis | A) Memory - simplest, restart clears |
| How to wake from deep sleep? | A) ESP-NOW B) UDP broadcast C) Don't sleep | C) Light sleep only for now |
| Voice confirm required? | A) Always B) Never C) Configurable | C) Configurable per source |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| WiFi out of range | Can't communicate | Show "No WiFi" on pager |
| Bridge crashes | All functionality lost | Systemd auto-restart |
| Wrong agent gets response | Confusion | Strict request_id tracking |
| Voice misheard | Wrong action taken | Always show CONFIRM mode |
| Battery dies | Pager unusable | Low battery alerts |
