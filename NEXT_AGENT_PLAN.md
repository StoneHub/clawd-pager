# Next Agent Plan: Local WiFi Pager for Claude Code

**Goal**: Boot the pager, it hooks into the current Claude Code session over local WiFi, provides remote control of all questions/authorizations, custom agent status, voice input.

**Constraint**: Laptop running WSL + pager on same WiFi. No Pi dependency.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAPTOP (WSL2)                            │
│                                                             │
│  ┌─────────────────┐     ┌──────────────────────────────┐  │
│  │  Claude Code     │     │  local_bridge.py             │  │
│  │                  │     │  (http://127.0.0.1:8081)     │  │
│  │  PostToolUse ────┼─────▶  /agent     → display mode   │  │
│  │  PreToolUse  ────┼─────▶  (validation)                │  │
│  │  PermissionReq ──┼─────▶  /permission → prompt+poll   │  │
│  │  Stop        ────┼─────▶  /agent     → idle           │  │
│  │                  │     │                              │  │
│  │  /pager command ─┼─────▶  /device/*  → alerts/display │  │
│  └─────────────────┘     └──────────┬───────────────────┘  │
│                                      │ aioesphomeapi       │
└──────────────────────────────────────┼─────────────────────┘
                                       │ WiFi (port 6053)
                          ┌────────────▼────────────────────┐
                          │    M5StickC Plus Pager           │
                          │    clawd-pager.local             │
                          │                                  │
                          │  - 135x240 TFT display           │
                          │  - 15 display modes              │
                          │  - Button A = YES / Voice hold   │
                          │  - Button B = NO / Back           │
                          │  - PDM microphone                │
                          │  - Buzzer for alerts             │
                          └──────────────────────────────────┘
```

---

## What's Already Done (This Session)

| Item | Status | File |
|------|--------|------|
| Local bridge skeleton | DONE | `devtools/local_bridge.py` |
| Hooks default to localhost | DONE | `devtools/claude_hook.py`, `permission_handler.py` |
| Hook→firmware mode names aligned | DONE | All 10 modes match: AGENT_EDIT, AGENT_BASH, etc. |
| /pager command → localhost | DONE | `.claude/commands/pager.md` |
| Example hooks config | DONE | `devtools/hooks_settings.json` |
| DisplayModeManager C++ routing | DONE | `display_modes/display_mode_manager.h` |
| LISTENING mode wired to C++ | DONE | `m5stickc/clawd-pager.yaml` |
| SessionStart hook (auto-bridge) | DONE | `devtools/session_start_hook.sh` |

---

## Implementation Steps (For Next Agent)

### Phase 1: Get the Bridge Running (WSL, no hardware needed)

**Step 1.1 — Install dependencies in WSL**
```bash
pip install aioesphomeapi aiohttp
```

**Step 1.2 — Start local bridge**
```bash
cd /path/to/clawd-pager/devtools
PAGER_IP=192.168.50.85 python local_bridge.py
# Or with mDNS: python local_bridge.py  (tries clawd-pager.local)
```

**Step 1.3 — Test bridge HTTP endpoints**
```bash
# Health check
curl http://127.0.0.1:8081/health

# Simulate a tool event
curl -X POST http://127.0.0.1:8081/agent \
  -H "Content-Type: application/json" \
  -d '{"event_type":"TOOL_START","tool":"Edit","display_mode":"AGENT_EDIT","display_text":"test.py","display_sub":"+5 -2"}'

# Simulate idle
curl -X POST http://127.0.0.1:8081/agent \
  -H "Content-Type: application/json" \
  -d '{"event_type":"WAITING","display_mode":"IDLE"}'
```

**Step 1.4 — Configure Claude Code hooks**

Copy the hooks section from `devtools/hooks_settings.json` into your project's `.claude/settings.local.json`, adjusting the paths:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /home/monroe/clawd/work/clawd-pager/devtools/claude_hook.py PostToolUse",
        "timeout": 5
      }]
    }],
    "PermissionRequest": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /home/monroe/clawd/work/clawd-pager/devtools/permission_handler.py",
        "timeout": 120
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /home/monroe/clawd/work/clawd-pager/devtools/claude_hook.py WAITING",
        "timeout": 5
      }]
    }]
  }
}
```

**Step 1.5 — Verify end-to-end**

With bridge running + hooks configured, start a Claude Code session and ask it to do something. The pager should show tool-specific displays.

### Phase 2: Firmware Compilation + OTA Flash

**Step 2.1 — Compile firmware**
```bash
# On the laptop (WSL) or Pi — wherever ESPHome is installed
source /path/to/esphome-env/bin/activate
cd /path/to/clawd-pager/m5stickc
esphome compile clawd-pager.yaml
```

This compiles the updated firmware with:
- `DisplayModeManager` C++ integration (LISTENING mode from C++)
- All existing display modes intact

**Step 2.2 — OTA upload**
```bash
# Pager must be powered on and on WiFi
esphome upload clawd-pager.yaml --device 192.168.50.85
# Or via mDNS:
esphome upload clawd-pager.yaml --device clawd-pager.local
```

**Step 2.3 — Verify pager boots**
```bash
esphome logs clawd-pager.yaml --device 192.168.50.85
```
Should see: Mario jingle, "LOBSTER READY!", IDLE mode.

### Phase 3: Improve the Bridge (Robustness)

**Step 3.1 — Auto-reconnect**

The bridge should reconnect to the pager if the connection drops (WiFi blip, pager reboot, etc). Add a background reconnect task to `local_bridge.py`:

```python
async def _reconnect_loop(self):
    while True:
        if not self.connected:
            try:
                await self.connect()
            except Exception:
                pass
        await asyncio.sleep(10)
```

**Step 3.2 — Service discovery**

Use aioesphomeapi's `list_entities_services` after connect to dynamically discover the `set_display` and `alert` service keys instead of hardcoding them. The current `_find_service` method uses hardcoded UserService objects — replace with dynamic lookup.

**Step 3.3 — Voice input pipeline**

The firmware already streams audio via UDP when Button A is held. The local bridge needs:
1. UDP listener on port 12345
2. Write received audio to `/tmp/clawd_voice.wav`
3. Run Whisper STT (local or API)
4. Send transcription back to pager as CONFIRM mode
5. Wait for A (send) or B (cancel)
6. If sent, return transcription to Claude Code

### Phase 4: Missing Display Mode — Question Response Routing

**Problem**: When Claude Code asks a question (not a permission, but an actual "which approach?" type question), the pager shows it but there's no way to route the answer back.

**Solution**: Use the `UserPromptSubmit` hook in reverse — when the pager user responds, inject the response into Claude Code's stdin. Or more practically:

1. Claude Code asks question → hook sends to bridge → pager shows QUESTION mode
2. User presses A (yes) or B (no) or holds A (voice response)
3. Bridge detects button → writes response to a file
4. The hook's stdout returns the response as `additionalContext` for Claude

This requires:
- A new hook on `Notification` (type `elicitation_dialog`) to capture questions
- A response injection mechanism (file watch or named pipe)

### Phase 5: UX Polish

**Step 5.1 — Briefing on Button A tap**

When in IDLE and user taps A, call the bridge's `/status` endpoint and format a summary of the current Claude Code session state (what tool was last used, how long idle, etc).

**Step 5.2 — Battery-aware bridge**

The bridge should monitor pager battery via ESPHome API and:
- Switch to simpler display modes below 20%
- Warn Claude Code when battery is critical

**Step 5.3 — Multiple session support**

If Claude Code runs multiple sessions (different terminals), the bridge should track which session's events to display. Use `session_id` from hook data to tag events. Pager shows the most recently active session.

---

## File Inventory

| File | Purpose | Status |
|------|---------|--------|
| `devtools/local_bridge.py` | Self-contained bridge for WSL | NEW — needs testing |
| `devtools/claude_hook.py` | PostToolUse hook, sends to bridge | UPDATED — localhost default |
| `devtools/permission_handler.py` | PermissionRequest hook | UPDATED — localhost default |
| `devtools/hooks_settings.json` | Example hooks config for Claude Code | UPDATED — includes SessionStart |
| `devtools/session_start_hook.sh` | SessionStart hook — auto-starts bridge, reports status | NEW |
| `.claude/commands/pager.md` | /pager slash command | UPDATED — localhost URLs |
| `m5stickc/clawd-pager.yaml` | Pager firmware | UPDATED — C++ display manager |
| `display_modes/display_mode_manager.h` | C++ display routing | UPDATED — routing implemented |

---

## Known Issues to Address

1. **Bridge service discovery** — `_find_service()` in local_bridge.py uses hardcoded `UserService` objects. Should dynamically discover services after connect. The service key (0) is a placeholder — real keys are assigned by ESPHome.

2. **Bridge reconnection** — No auto-reconnect yet. If pager reboots or WiFi drops, bridge stays disconnected until restarted.

3. **Voice audio** — UDP audio receiver not implemented in local_bridge.py yet. The firmware sends raw PCM audio to port 12345. Needs: UDP socket → WAV file → Whisper → CONFIRM mode.

4. **Question routing** — Only YES/NO permission responses work. Free-form question responses (voice transcription back to Claude) need the Notification hook + response injection mechanism.

5. **Bridge startup order** — ~~Bridge must start before Claude Code session.~~ **RESOLVED**: `session_start_hook.sh` auto-starts bridge on SessionStart. Still worth testing the detached process lifecycle across multiple sessions.

---

## Testing Checklist (For Next Session)

- [ ] Bridge starts and connects to pager over WiFi
- [ ] `curl /health` returns `{"status": "ok", "pager": true}`
- [ ] PostToolUse hook fires → pager shows correct AGENT_* mode
- [ ] Multiple tools in sequence → pager updates, then reverts to IDLE
- [ ] PermissionRequest → pager shows PERMISSION mode → button press → hook gets allow/deny
- [ ] `/pager alert Test!` → pager beeps and shows alert
- [ ] `/pager say Hello` → pager shows message
- [ ] Button A tap in IDLE → status display
- [ ] Button A hold → voice recording → bridge receives audio
- [ ] Pager reboot → bridge reconnects automatically
- [ ] Bridge restart → hooks gracefully timeout, no Claude Code hang
- [ ] SessionStart hook → auto-starts bridge if not running
- [ ] SessionStart hook → reports pager status with emoji indicators
- [ ] SessionStart hook → detached bridge survives session end

---

## Dependencies

```bash
# In WSL (Python 3.10+)
pip install aioesphomeapi aiohttp

# For voice transcription (optional, Phase 3)
pip install openai-whisper  # local Whisper
# OR
pip install openai          # OpenAI API for Whisper
```

---

## Quick Start (Copy-Paste)

```bash
# Terminal 1: Start bridge
cd /path/to/clawd-pager/devtools
pip install aioesphomeapi aiohttp
PAGER_IP=192.168.50.85 python local_bridge.py

# Terminal 2: Test connection
curl http://127.0.0.1:8081/health

# Then configure hooks in .claude/settings.local.json (see hooks_settings.json)
# Start Claude Code — pager should light up with tool activity!
```
