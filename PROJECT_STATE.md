# Clawd Pager - Project State

**Last Updated**: 2026-01-31 16:30 EST

## [V4.0] Observable Development & Colorful UI (LIVE)

**Status**: Major iteration loop improvements + colorful animated display

### What's New Today (2026-01-31):

1. **Development Dashboard** - Web UI at `http://192.168.50.50:8080`
   - Real-time event stream (button presses, mode changes)
   - Session recording with notes
   - Build/Upload buttons for OTA deployment
   - Device state monitoring

2. **Event Logging System** - SQLite-based persistence
   - All events timestamped and stored in `~/.clawd/pager_events.db`
   - Queryable history for debugging
   - Session replay capability

3. **Colorful Animated Display** - Steve Jobs approved
   - **LISTENING**: Teal header + cyan bouncing waveform bars
   - **PROCESSING**: Amber spinning dots animation
   - **AWAITING**: Purple pulsing concentric circles
   - **ALERT**: Flashing red/orange header
   - **IDLE**: Clean with cyan accents, colored battery indicator
   - **RESPONSE**: Coral accent header bar

4. **Button Behavior Improved**
   - **Button B tap** (< 400ms) = Go home/cancel (lower tone)
   - **Button B hold** (> 400ms) = Voice recording (ascending tone)
   - **Button A tap** = Briefing (stays on screen 5 seconds now!)
   - **Button A hold** = Sleep countdown

5. **Bridge v4.0** - Event logging integration
   - All button/display/audio events logged
   - Integrated with dashboard for real-time monitoring
   - Removed Telegram dependency for voice (TODO: local processing)

### Files Created:
- `devtools/` - Development tooling directory
  - `event_logger.py` - SQLite event persistence
  - `session_manager.py` - Recording/replay
  - `dashboard_server.py` - WebSocket server
  - `dashboard_ui/index.html` - Web dashboard
- `dev.ps1` - Unified build commands (compile/upload/watch/dashboard)
- `CLAUDE.md` - AI assistant context documentation

### Known Issues:
- Voice recognition accuracy needs improvement (Whisper base model)
- Session recording export needs testing
- Agent activity animations not yet implemented

---

## Quick Start

```bash
# Start dashboard (on Pi)
cd /home/monroe/clawd/work/clawd-pager
source /home/monroe/clawd/esphome-env/bin/activate
python -m devtools.dashboard_server

# Start bridge (separate terminal)
cd /home/monroe/clawd/scripts
python bridge.py

# Deploy new firmware
esphome compile clawd-pager.yaml
esphome upload clawd-pager.yaml --device 192.168.50.85
```

Or use the dashboard's Build & Deploy buttons!

---

## Previous Versions

### [V3.0] Hero UI & Direct Link
- Large digital clock, battery bar, weather widget
- Direct API control via aioesphomeapi
- Voice pipeline with Whisper fallback

### [V2.0] Stabilization
- Removed CPU-heavy "floaty text" physics
- Fixed AXP192 backlight control
- WiFi power save disabled

### [V1.0] Initial
- Basic ESPHome firmware
- Home Assistant integration

---

## Configuration

| Setting | Value |
|---------|-------|
| **Device IP** | 192.168.50.85 |
| **ESPHome** | 2024.12.4 (DO NOT UPGRADE) |
| **Dashboard** | http://192.168.50.50:8080 |
| **WiFi** | FlyingChanges / flyingchanges |
| **Power Save** | none (CRITICAL) |

## Hardware

| Component | Pin/Address |
|-----------|-------------|
| Button A | GPIO37 |
| Button B | GPIO39 |
| Power Button | GPIO35 |
| Buzzer | GPIO2 |
| Display | ST7789V SPI |
| AXP192 | I2C 0x34 |

---

## Next Steps

1. **Local voice processing** - Show response on pager, not Telegram
2. **Agent activity display** - Show Claude Code activity on idle screen
3. **Session summaries** - Aggregate interaction stats
4. **Improve voice accuracy** - Larger Whisper model or better mic positioning
