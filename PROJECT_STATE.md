# Clawd Pager - Project State

**Last Updated**: 2026-01-31 21:30 EST
**Status**: READY TO TEST - Firmware needs compile/upload

---

## Vision

**Universal AI Remote Control** - The pager lets Monroe interact with Claude Code and Clawdbot without touching the keyboard. See Claude working, answer yes/no questions with buttons, voice commands for complex responses.

---

## Current State: Uncommitted Changes Ready

### What's Changed (Not Yet Deployed)

**Firmware (clawd-pager.yaml)**:
- Button A = Yes/Status (short), Voice (hold 400ms+)
- Button B = No/Back/Cancel
- CONFIRM mode display (shows transcription before sending)
- Rainbow waveform LISTENING animation
- Bouncy dots PROCESSING animation
- Fun sounds: Mario startup, Zelda "item get" for YES, sad trombone for NO

**Bridge (bridge.py)**:
- Connection stability: 5-second checks, ping keepalive, 3-strike disconnect rule
- Request queue with source tracking (Claude Code vs Clawdbot)
- Response routing to `~/.clawd/pager_response.json`
- `/response` and `/status` API endpoints
- Calendar PATH fix (`/home/linuxbrew/.linuxbrew/bin/gog`)
- Button handlers synced with new layout

**Hook (claude_hook.py)**:
- New `ask` command: `claude_hook.py ask "Question?" --timeout 30`
- Polls bridge for user response, returns "yes" or "no" to stdout

---

## Immediate Next Steps

### Step 1: Compile Firmware
```bash
cd /home/monroe/clawd/work/clawd-pager
source /home/monroe/clawd/esphome-env/bin/activate
ESPHOME_COMPILE_PROCESSES=1 esphome compile clawd-pager.yaml
```

### Step 2: Upload to Device
```bash
esphome upload clawd-pager.yaml --device 192.168.50.85
```

### Step 3: Restart Bridge
```bash
sudo systemctl restart clawd-bridge
```

### Step 4: Test Each Feature
1. **Startup**: Should play Mario jingle, show "LOBSTER READY!"
2. **Button A short**: Should show status/calendar
3. **Button A hold**: Should go to LISTENING with rainbow waveform
4. **Button B short**: Should go back/cancel
5. **Hook test**: `python3 devtools/claude_hook.py TOOL_START "Edit"` - should show on pager

---

## Button Layout (NEW)

| Button | Short Press | Long Hold (400ms+) |
|--------|-------------|-------------------|
| **A** | Yes (QUESTION), Send (CONFIRM), Status (IDLE) | Voice recording |
| **B** | No (QUESTION), Cancel (CONFIRM), Back (other) | - |

---

## Architecture

```
[Claude Code CLI]
       │
       │ Hooks (PreToolUse, PostToolUse, Stop)
       ▼
[claude_hook.py] ──POST──▶ [Bridge :8081] ◀──ESPHome API──▶ [M5 Pager]
                              │                                  │
                              │◀────────── UDP Audio ────────────┘
                              │
                              ▼
                         [Whisper STT]
                              │
                              ▼
                      [Clawdbot Gateway]
                              │
                              ▼
                    [Response on Pager]
```

---

## Key Files

| File | Purpose |
|------|---------|
| `clawd-pager.yaml` | ESPHome firmware config |
| `/home/monroe/clawd/scripts/bridge.py` | Python bridge on Pi |
| `devtools/claude_hook.py` | Claude Code hook script |
| `audio_streamer.h` | UDP audio streaming class |
| `VISION.md` | Full product vision |
| `AUDIT.md` | Code audit and analysis |

---

## Config

| Item | Value |
|------|-------|
| Device IP | 192.168.50.85 |
| Bridge IP | 192.168.50.50 |
| Dashboard | :8080 |
| Bridge API | :8081 |
| Audio UDP | :12345 |
| ESPHome | 2024.12.4 (DO NOT UPGRADE) |

---

## What Works (Verified)

- [x] Device boots, displays clock
- [x] WiFi connects reliably (power_save: none)
- [x] Bridge connects to device
- [x] Animations render correctly
- [x] Hooks reach bridge API

## What Needs Testing (After Deploy)

- [ ] New button layout (A=Voice, B=No)
- [ ] Voice capture with new buttons
- [ ] Calendar display (PATH fixed)
- [ ] Claude Code tool names on pager
- [ ] YES/NO responses routed back
- [ ] Fun sounds (Mario, Zelda, sad trombone)

---

## For Next Session / After Compact

**Goal**: Get Claude Code tool usage showing on pager, answer yes/no questions.

**Test sequence**:
1. Compile and upload firmware
2. Restart bridge
3. Have Claude do some tool calls (Edit, Read, Grep)
4. Watch pager - should show tool names in AGENT mode
5. Test `claude_hook.py ask "Test question?"`
6. Press A on pager - should return "yes"

**If it doesn't work**, check:
- Bridge logs: `sudo journalctl -u clawd-bridge -f`
- Is bridge connected? `curl http://192.168.50.50:8081/status`
- Did firmware upload? Check for Mario jingle on boot
