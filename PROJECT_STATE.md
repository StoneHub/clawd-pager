# Clawd Pager - Project State

**Last Updated**: 2026-01-31 20:15 EST

## Vision

**Universal AI Remote Control** - See [VISION.md](VISION.md) for full details.

The pager connects to BOTH Claude Code AND Clawdbot:
- Desk mode: See Claude working, answer yes/no questions
- Mobile mode: Clawdbot can wake pager, get voice responses
- Intelligent routing: Responses go to the right agent

## Current Status: V4.2 → V5.0

### What Works
- [x] AGENT mode shows Claude Code tool usage
- [x] Voice capture with Whisper STT
- [x] Hooks fire on PreToolUse/PostToolUse
- [x] QUESTION mode display (flashing button hint)
- [x] Dashboard real-time events
- [x] Brightness stays high when docked

### What's Broken
- [ ] **Claude API error** - Need `ANTHROPIC_API_KEY` in bridge
- [ ] **`/pager` skill** - Plugin not properly installed

### What's Missing (V5.0)
- [ ] Request queue with routing
- [ ] Button responses back to Claude Code
- [ ] Clawdbot integration
- [ ] CONFIRM mode for voice
- [ ] Wake from sleep

---

## [V4.2] Voice Capture + UDP Streaming (COMPLETE)

### New Features:
- **Voice capture** - PDM microphone (SPM1423) now configured
- **UDP audio streaming** - Streams to bridge on port 12345
- **Whisper STT** - Bridge transcribes audio locally
- **DOCKED mode** - Ambient animation when charging
- **AGENT mode** - Matrix animation when Claude Code is working
- **Claude Code hooks** - PreToolUse/PostToolUse emit events to pager

### Critical Learnings (M5StickC Plus 1.1):

| Issue | Solution |
|-------|----------|
| **Buzzer blocks microphone** | MUST turn off buzzer before recording! They share GPIO resources |
| **Microphone pins** | GPIO0 = LRCLK (clock), GPIO34 = DIN (data) |
| **Channel** | Use `channel: left` not `right` |
| **PDM mode** | `pdm: true` required |
| **GPIO0 warning** | Add `ignore_strapping_warning: true` |
| **Hook URL** | Must point to Pi (192.168.50.50), not localhost |
| **Dashboard alerts** | Must call bridge API (/device/alert), not just log events |

### Microphone Config (working):
```yaml
i2s_audio:
  - id: mic_i2s_bus
    i2s_lrclk_pin:
      number: GPIO0
      ignore_strapping_warning: true

microphone:
  - platform: i2s_audio
    id: mic_i2s
    i2s_audio_id: mic_i2s_bus
    i2s_din_pin: GPIO34
    adc_type: external
    pdm: true
    channel: left
```

### Files Created/Modified:
- `audio_streamer.h` - WiFiUDP audio streaming class
- `devtools/claude_hook.py` - Hook script (fixed URL to Pi)
- `devtools/dashboard_server.py` - Added /api/export/logs endpoint
- `devtools/session_manager.py` - Fixed path.stem bug for .json.gz files
- `/home/monroe/clawd/scripts/bridge.py` - Added /device/alert and /device/display endpoints

### To Install Services:
```bash
sudo cp devtools/clawd-*.service /etc/systemd/system/
sudo cp devtools/clawd-sudoers /etc/sudoers.d/clawd
sudo chmod 440 /etc/sudoers.d/clawd
sudo systemctl daemon-reload
sudo systemctl enable --now clawd-dashboard clawd-bridge
```

### Quick Tests:
```bash
# Test agent hook
python3 devtools/claude_hook.py TOOL_START "Edit"

# Test alert via bridge API
curl -X POST http://192.168.50.50:8081/device/alert \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!"}'

# Monitor UDP audio (on bridge)
nc -u -l 12345 | xxd | head
```

## Config
- Device: 192.168.50.85
- Dashboard: :8080
- Bridge API: :8081
- Audio UDP: :12345
- ESPHome: 2024.12.4 (DO NOT UPGRADE)

## Architecture
```
[M5StickC Plus] --UDP:12345--> [Bridge] --Whisper--> [Clawdbot] --> [Telegram]
       |                          |
       +--ESPHome API:6053--------+
                                  |
                           [Dashboard :8080]
```

## Sources
- [M5StickC Plus voice config](https://community.home-assistant.io/t/m5stickc-plus-as-voice-remote/577621/14)
- [ESPHome I2S Audio docs](https://esphome.io/components/i2s_audio/)
- [ESPHome Microphone docs](https://esphome.io/components/microphone/i2s_audio/)
