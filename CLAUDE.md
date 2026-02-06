# Clawd Pager - AI Assistant Context

This document provides essential context for AI assistants (including Clawdbot and Claude Code) working on this project.

## What Is This?

A multi-device hardware project for physical AI interaction. Two devices:

1. **M5StickC Plus** (original) — ESPHome pager showing Claude Code session status
2. **SenseCap Watcher W1-A** (active development) — ESP-IDF firmware with AI camera, 412x412 display, knob input

---

## SenseCap Watcher W1-A (Active)

### Hardware
- **SoC**: ESP32-S3 (QFN56, rev v0.2) with 8MB PSRAM
- **AI**: Himax WiseEye2 co-processor (YOLO object detection)
- **Display**: 412x412 round LCD (SPD2010) with touch
- **Input**: Rotary encoder knob (GPIO41/42) + push button (IO expander pin 3)
- **RGB LED**: WS2812 on GPIO40
- **Audio**: ES8311 codec, I2S mic/speaker
- **USB**: Two ports — ACM0 = Himax, ACM1 = ESP32-S3

### ESP-IDF Build
```bash
source ~/esp/esp-idf/export.sh   # ESP-IDF v5.2.1
cd watcher-firmware/examples/<example>
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM1 flash     # ESP32 is ACM1
```

### USB Passthrough (WSL2)
From **elevated PowerShell**: `usbipd attach --wsl --busid 2-1`

### BSP Key APIs (`sensecap-watcher.h`)
```c
bsp_io_expander_init();                     // Always first
bsp_exp_io_set_level(BSP_PWR_AI_CHIP, 1);  // Power on AI
bsp_rgb_init(); bsp_rgb_set(r, g, b);      // RGB LED
lv_disp_t *disp = bsp_lvgl_init();         // Display + touch + knob encoder
sscma_client_handle_t c = bsp_sscma_client_init(); // AI camera
bsp_exp_io_get_level(BSP_KNOB_BTN);        // Read knob button (0=pressed)
bsp_system_shutdown();                       // Cuts battery power (no-op on USB!)
bsp_system_deep_sleep(seconds);             // Real power off (works on USB too)
```

### Power Off Gotchas
- `bsp_system_shutdown()` only works on battery — USB bypasses the power rail
- Use `bsp_system_deep_sleep(0)` for USB-compatible power off
- Physical pinhole reset button on bottom of device
- Knob long-press to power on (3s hold, shows Seeed logo)
- `bsp_set_btn_long_press_cb()` must be called AFTER `bsp_lvgl_init()` (needs encoder)

### SSCMA AI Camera Pattern
```c
sscma_client_register_callback(client, &cb, NULL);  // cb.on_event for detections
sscma_client_init(client);
sscma_client_set_model(client, 1);                   // Model 1 = YOLO
sscma_client_set_sensor(client, 1, 0, true);         // Sensor 1, opt 0 = 240x240
sscma_client_invoke(client, -1, false, false);        // Continuous, no image
// In on_event callback:
sscma_utils_fetch_boxes_from_reply(reply, &boxes, &count);  // Get detections
```

### Component Dependencies
Each example needs `main/idf_component.yml`:
```yaml
dependencies:
  idf:
    version: ">=5.0"
  sensecap-watcher:
    override_path: "../../../components/sensecap-watcher"
```

### Current Examples
| Example | Description |
|---------|-------------|
| `pocket_tamagotchi` | AI-aware virtual pet — camera detects presence, touch to pet, knob to feed, RGB mood LED, NVS persistence |
| `get_started` | Touch screen drawing demo |
| `knob_rgb` | RGB LED + knob rotation |
| `sscma_client_monitor` | Camera AI with LVGL image display |

### LVGL Notes (v8.x in this SDK)
- Only `lv_font_montserrat_14` available by default (enable others in sdkconfig)
- Wrap all LVGL calls in `lvgl_port_lock(0)` / `lvgl_port_unlock()`
- `lv_anim_exec_xcb_t` expects `void (*)(void*, int32_t)` — don't cast `lv_obj_set_y` directly, use a wrapper
- Display is 412x412, use `DRV_LCD_H_RES` / `DRV_LCD_V_RES` constants

---

## M5StickC Plus (Original Pager)

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLAUDE CODE SESSION                          │
│                      (running on user's machine)                     │
└───────────────┬─────────────────────────────────────┬───────────────┘
                │                                     │
    ┌───────────▼───────────┐           ┌─────────────▼─────────────┐
    │   claude_hook.py      │           │   safety-guard.py         │
    │   (PostToolUse)       │           │   (PreToolUse)            │
    │   Sends tool status   │           │   Permission requests     │
    └───────────┬───────────┘           └─────────────┬─────────────┘
                │ HTTP POST                           │ HTTP POST + Poll
                │ /agent                              │ /permission
                └───────────────────┬─────────────────┘
                                    │
                      ┌─────────────▼─────────────┐
                      │      bridge.py            │
                      │   fcfdev:8081             │
                      │   (192.168.50.50)         │
                      │                           │
                      │  - Receives hook events   │
                      │  - Manages pager state    │
                      │  - Haiku briefings        │
                      │  - Voice transcription    │
                      │  - Permission tracking    │
                      └─────────────┬─────────────┘
                                    │ aioesphomeapi
                                    │ port 6053
                      ┌─────────────▼─────────────┐
                      │    M5StickC Plus          │
                      │    192.168.50.85          │
                      │    (ESPHome firmware)     │
                      │                           │
                      │  - 135x240 TFT display    │
                      │  - Button A (top) = YES   │
                      │  - Button B (front) = NO  │
                      │  - Buzzer for alerts      │
                      │  - PDM microphone         │
                      └───────────────────────────┘
```

## Quick Reference

| Property | Value |
|----------|-------|
| **Device** | M5StickC Plus 1.1 (ESP32-PICO-D4) |
| **Pager IP** | 192.168.50.85 |
| **Bridge Host** | fcfdev (192.168.50.50, port 8081) |
| **ESPHome Version** | 2024.12.4 (**DO NOT UPGRADE**) |

**Note:** fcfdev is the hostname of the Raspberry Pi at 192.168.50.50. User is typically SSH'd into fcfdev when working on this project.

## All File Locations

### In This Repo (`/home/monroe/clawd/work/clawd-pager/`)
| File | Purpose |
|------|---------|
| `clawd-pager.yaml` | **Main ESPHome firmware** - display modes, buttons, sounds |
| `CLAUDE.md` | This file - AI assistant context |
| `devtools/claude_hook.py` | Hook that sends tool events to bridge |
| `audio_streamer.h` | UDP audio streaming for voice input |

### On fcfdev (`/home/monroe/clawd/scripts/`)
| File | Purpose |
|------|---------|
| `bridge.py` | **Main bridge** - connects hooks to pager, manages state |
| `.env` | Environment variables (ANTHROPIC_API_KEY, etc.) |

### Claude Code Hooks (`~/.claude/hooks/`)
| File | Purpose |
|------|---------|
| `safety-guard.py` | PreToolUse hook - blocks dangerous commands, requests permission via pager |

### Systemd Service
```bash
# Bridge runs as systemd service
sudo systemctl status clawd-bridge
sudo systemctl restart clawd-bridge
journalctl -u clawd-bridge -f  # View logs
```

## Display Modes

| Mode | Trigger | Description |
|------|---------|-------------|
| `IDLE` | Default | Static clock, battery, date. Tap A for briefing |
| `AGENT` | Tool use | Generic "working" indicator |
| `AGENT_EDIT` | Edit tool | Shows filename, +lines/-lines, code preview |
| `AGENT_BASH` | Bash tool | Terminal style with command preview |
| `AGENT_READ` | Read tool | Blue header, scrolling page animation |
| `AGENT_SEARCH` | Grep/Glob | Purple, magnifying glass animation |
| `AGENT_WEB` | WebFetch | Cyan globe animation |
| `AGENT_PLAN` | TodoWrite | Amber, shows actual todo items |
| `AGENT_SUB` | Task tool | Pink, shows sub-agent type |
| `PERMISSION` | PreToolUse hook | Red/orange, A=YES B=NO buttons |
| `BRIEFING` | Button A tap | Shows Haiku summary of session |
| `LOADING` | Fetching data | Minimal dots animation |
| `LISTENING` | Button A hold | Rainbow waveform, recording voice |
| `PROCESSING` | After voice | Bouncing dots while thinking |
| `DOCKED` | Charging | Ambient display with particles |

## Button Behavior

### Button A (Top, GPIO37)
- **Short tap in IDLE**: Fetch Haiku briefing (shows recent activity summary)
- **Short tap in BRIEFING**: Show more detail
- **Short tap in PERMISSION**: Approve (YES)
- **Long hold (400ms+)**: Voice recording

### Button B (Front, GPIO39)
- **Tap in BRIEFING**: Dismiss, return to IDLE
- **Tap in PERMISSION**: Deny (NO)
- **Tap elsewhere**: Back to IDLE

### Power Button (Left side)
- Handled by AXP192 hardware (not GPIO addressable)
- Short press: Wake from off
- Long press (6s): Power off

## Power Management

- **Activity timeout**: 30s → 40% brightness, 60s → 10%, 180s → auto power off
- **Charging exception**: Won't dim or power off when battery ≥95% or in DOCKED mode
- **Auto power off**: Uses I2C write to AXP192 register 0x32

## Permission System Flow

1. Claude Code tries to run a command matching `safety-guard.py` patterns
2. Hook POSTs to bridge `/permission` endpoint
3. Bridge shows PERMISSION mode on pager
4. User presses A (approve) or B (deny)
5. Firmware sets mode to `PERM_APPROVED` or `PERM_DENIED`
6. Bridge detects mode change, updates permission status
7. Hook polls `/permission/{id}` and gets result
8. Hook returns `allow` or `deny` to Claude Code

## Briefing Feature

- Tap A on IDLE → shows "Fetching update..." loading screen
- Calls `ask_claude()` via Clawdbot (uses Claude Code subscription)
- Displays brief summary of recent session activity
- Tap A again for more detail, B to dismiss

## Development Commands

```bash
# Compile firmware
source /home/monroe/clawd/esphome-env/bin/activate
esphome compile clawd-pager.yaml

# Upload to pager
esphome upload clawd-pager.yaml --device 192.168.50.85

# View pager logs
esphome logs clawd-pager.yaml --device 192.168.50.85

# Restart bridge (after editing bridge.py)
sudo systemctl restart clawd-bridge

# View bridge logs
journalctl -u clawd-bridge -f
```

## Common Issues

### Pager shows wrong mode for tools
- **Cause**: Bridge sending `SILENT` instead of actual mode
- **Fix**: Check bridge.py `_handle_tool_event` - should send `SILENT_AGENT_READ` etc.

### Permission prompt shows 1/2/3 in terminal
- **Cause**: safety-guard.py not polling for pager response
- **Fix**: Ensure `request_pager_permission()` is called, not just returning "ask"

### Screen dims while charging
- **Cause**: activity_watcher not checking battery level
- **Fix**: Check `has_power` logic includes `battery_level >= 95.0`

### Briefing shows "Error: 400"
- **Cause**: Direct Anthropic API call with no credits
- **Fix**: Use `ask_claude()` which routes through Clawdbot (Claude Code subscription)

### Power button doesn't work
- **Cause**: GPIO35 is not connected to power button on M5StickC Plus
- **Note**: Power button is handled by AXP192 at hardware level, not addressable via GPIO

## Critical Constraints

1. **ESPHome 2024.12.4** - Don't upgrade, breaks Home Assistant compatibility
2. **WiFi power_save_mode: none** - Required to prevent disconnects
3. **AXP192 for backlight** - Not GPIO controllable
4. **Don't SSH into fcfdev** - User is typically already logged into fcfdev when working on this project

## Testing Checklist

After changes, verify:
1. Device boots with Mario jingle
2. IDLE shows static clock/battery (no animations)
3. Button A tap shows briefing
4. Button A hold records voice
5. Button B dismisses screens
6. Tool use shows correct mode (AGENT_EDIT, AGENT_BASH, etc.)
7. Permission requests show on pager, buttons work
8. Auto power off after 3 min idle (if not charging)
