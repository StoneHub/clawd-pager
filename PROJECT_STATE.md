# Clawd Pager - Project State

**Last Updated**: 2026-01-26

## Project Overview

ESPHome project for M5Stick-C board that displays status messages from Home Assistant.

## Hardware

- Board: M5Stick-C (ESP32)
- Display: ST7789V (240x135, rotated 270°)
- Button: GPIO37 (Button A)

## Current Setup

### Environment

- WSL2 (Ubuntu) on Windows
- ESPHome venv: `~/esphome-venv`
- Project path: `/mnt/c/Users/monro/Codex/clawd-pager`
- Device port: `/dev/ttyUSB0`

### USB Device Connection

- Using usbipd to share USB from Windows to WSL
- Command to attach: `usbipd attach --wsl --busid 2-1`
- Device appears as: `/dev/ttyUSB0`

## Recent Changes

- Added user to `dialout` group for serial port access: `sudo usermod -a -G dialout $USER`
- **NEEDS WSL RESTART** for group change to take effect

## Workflow Scripts

- `compile.ps1` - Compile only (no flash)
- `flash.ps1` - Compile and flash to device
- `logs.ps1` - View device logs
- Run from PowerShell in project directory

## Configuration Highlights

- **Board**: M5StickC Plus (ESP32)
- **WiFi**: "FlyingChanges" / "flyingchanges"
- **Features**:
  - **Cyberpunk UI**: Color status bar, time display, animations.
  - **Audio**: Startup chime and notification sounds (RTTTL).
  - **Monitoring**: USB logging via WSL (`logs.ps1`), WiFi Signal sensor.
- **Integration**:
  - Pulls status from: `input_text.clawd_status` in Home Assistant.
  - updates on: HA status change OR "Button A" press.

## Current Status

**COMPLETED:**

- [x] Flashed with "Wow" firmware (Buzzer, Colors, Time).
- [x] Verified WiFi connection and Time Sync.
- [x] Verified Startup Sound.

**NEXT STEPS:**

1. Test Home Assistant integration (`input_text.clawd_status`).
2. Create GitHub repository.

## Known Warnings (Normal)

- GPIO15 and GPIO5 are strapping pins (expected for M5Stick-C pinout)
- WiFi AP without captive portal (normal for fallback)
