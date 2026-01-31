# Clawd Pager - AI Assistant Context

This document provides essential context for AI assistants (including Clawdbot) working in this repository.

## Quick Reference

| Property | Value |
|----------|-------|
| **Device** | M5StickC Plus 1.1 (ESP32-PICO-D4) |
| **IP Address** | 192.168.50.85 |
| **API Port** | 6053 (ESPHome native API) |
| **ESPHome Version** | 2024.12.4 (**DO NOT UPGRADE** - HA compatibility) |
| **Bridge Host** | 192.168.50.50 (fcfdev/Raspberry Pi) |
| **Dashboard** | http://192.168.50.50:8080 |

## Critical Constraints

1. **ESPHome Version Lock**: Must use 2024.12.4. Newer versions use incompatible `aioesphomeapi` versions that break Home Assistant 2025.1.4 integration.

2. **WiFi Power Save**: Must be `none`. Any other setting causes random disconnects.

3. **Backlight Control**: Uses AXP192 PMIC, NOT GPIO. Requires the `martydingo/esphome-axp192` external component.

## Architecture

```
┌─────────────────────┐
│  Telegram / User    │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  Clawdbot Agent     │
└─────────┬───────────┘
          │
┌─────────▼───────────┐     ┌─────────────────────┐
│  bridge.py (Pi)     │────▶│  Dev Dashboard      │
│  192.168.50.50      │     │  :8080              │
└─────────┬───────────┘     └─────────────────────┘
          │ aioesphomeapi
          │ port 6053
┌─────────▼───────────┐
│  M5StickC Plus      │
│  192.168.50.85      │
│  (ESPHome firmware) │
└─────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `clawd-pager.yaml` | **Main ESPHome config** - Edit this for device behavior |
| `PROJECT_STATE.md` | Current status, troubleshooting history |
| `MASTER_PLAN.md` | Development roadmap and milestones |
| `/home/monroe/clawd/scripts/bridge.py` | Python bridge running on Pi |
| `devtools/` | Development tooling (event logger, dashboard) |

## Development Commands

```bash
# From Windows (PowerShell)
.\dev.ps1 compile      # Validate and compile firmware
.\dev.ps1 upload       # OTA upload to device
.\dev.ps1 watch        # Compile + Upload + Tail logs
.\dev.ps1 logs         # Stream device logs
.\dev.ps1 dashboard    # Open web dashboard

# From Linux/WSL
source /home/monroe/clawd/esphome-env/bin/activate
esphome compile clawd-pager.yaml
esphome upload clawd-pager.yaml --device 192.168.50.85
esphome logs clawd-pager.yaml --device 192.168.50.85
```

## ESPHome API Services

The device exposes these services via the ESPHome native API:

| Service | Parameters | Description |
|---------|------------|-------------|
| `set_display` | `my_text: string`, `my_mode: string` | Update display content and mode |
| `alert` | `my_text: string` | Show alert with distinct tone |
| `update_weather` | `my_weather: string` | Update weather widget |
| `set_dev_mode` | `enabled: bool` | Toggle verbose event logging |
| `get_state` | (none) | Log current device state |

## Display Modes

| Mode | Description |
|------|-------------|
| `IDLE` | Home screen with clock, weather, battery |
| `LISTENING` | Voice capture active (Button B held) |
| `PROCESSING` | Working on voice input |
| `AWAITING` | Waiting for AI response |
| `RESPONSE` | Displaying message |
| `ALERT` | Priority notification with distinct tone |

## Hardware Pinout

| Pin | Function |
|-----|----------|
| GPIO37 | Button A (inverted) |
| GPIO39 | Button B (inverted) |
| GPIO35 | Power Button (inverted) |
| GPIO2 | Buzzer (LEDC PWM, RTTTL) |
| GPIO13 | SPI CLK |
| GPIO15 | SPI MOSI |
| GPIO5 | Display CS |
| GPIO23 | Display DC |
| GPIO18 | Display Reset |
| GPIO21 | I2C SDA |
| GPIO22 | I2C SCL |

## Event Schema

Events are logged to `~/.clawd/pager_events.db` with this structure:

```json
{
  "timestamp": "2026-01-31T14:30:52.123",
  "session_id": "20260131_143000",
  "source": "device|bridge|user|dashboard",
  "event_type": "BUTTON_PRESS|MODE_CHANGE|DISPLAY_UPDATE|...",
  "data": { ... },
  "sequence": 42
}
```

### Event Types

| Type | Source | Data Fields |
|------|--------|-------------|
| `BUTTON_PRESS` | device | button, display_mode |
| `BUTTON_RELEASE` | device | button, duration_ms |
| `MODE_CHANGE` | device/bridge | from_mode, to_mode |
| `DISPLAY_UPDATE` | bridge | text, mode |
| `AUDIO_START` | device | sample_rate |
| `AUDIO_END` | device | bytes_captured, duration_ms |
| `STT_RESULT` | bridge | transcript, confidence |
| `ERROR` | both | error_type, message, stack |
| `BUILD_START` | user | yaml_file |
| `BUILD_END` | user | success, duration_s, firmware_size |
| `OTA_START` | user | target_ip |
| `OTA_END` | user | success, duration_s |

## Common Issues and Fixes

### Black Screen
- **Cause**: Wrong backlight control method
- **Fix**: Use AXP192 component, not GPIO

### WiFi Disconnects
- **Cause**: Power save mode enabled
- **Fix**: Set `power_save_mode: none` in WiFi config

### "Marker byte invalid: 0" Errors
- **Cause**: ESPHome/HA API version mismatch
- **Fix**: Downgrade to ESPHome 2024.12.4

### Build Fails with SIGKILL
- **Cause**: Parallel compilation uses too much memory
- **Fix**: Set `ESPHOME_COMPILE_PROCESSES=1`

### Device Unreachable for OTA
- **Cause**: Deep sleep or WiFi power save
- **Fix**: Ensure deep sleep is disabled, power_save_mode: none

## Version Compatibility

| Home Assistant | ESPHome | aioesphomeapi |
|----------------|---------|---------------|
| 2025.1.4 | 2024.12.4 | 24.6.2 |
| 2025.1.4 | 2025.12.7 | 43.2.1 (INCOMPATIBLE) |
| 2025.1.4 | 2026.1.2 | 43.13.0 (INCOMPATIBLE) |

## Development Workflow

### Typical Iteration Cycle

1. Edit `clawd-pager.yaml`
2. Run `.\dev.ps1 compile` to validate
3. Run `.\dev.ps1 upload` to OTA deploy
4. Open dashboard to monitor events
5. Interact with device
6. Review events in dashboard

### Recording a Debug Session

1. Open dashboard: `.\dev.ps1 dashboard`
2. Click "Start Recording" with notes
3. Reproduce the issue
4. Click "End Recording"
5. Export session JSON for analysis

### Querying Events

```python
from devtools import get_logger

logger = get_logger()

# Recent events
events = logger.get_recent_events(50)

# Events by type
button_events = logger.get_recent_events(50, "BUTTON_PRESS")

# Search in data
results = logger.search_events("LISTENING")

# Session summary
sessions = logger.list_sessions()
```

## Testing a Change

After making changes, verify:

1. Device boots with startup tone
2. Clock displays correctly
3. Button A shows briefing
4. Button B triggers LISTENING mode
5. OTA updates still work
6. Dashboard shows events

## Files NOT to Modify

- `secrets.yaml` - Contains WiFi credentials (gitignored)
- `.esphome/` - Build artifacts (regenerated)
- `~/.clawd/pager_events.db` - Persistent event storage

## Contact

- **User**: Monroe
- **Telegram ID**: 8019338216
- **Home Assistant**: http://192.168.50.50:8123
