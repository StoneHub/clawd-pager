# Clawd Pager - Project State

**Last Updated**: 2026-01-27

## Project Overview

ESPHome project for M5StickC Plus that displays status messages from Home Assistant with a cyberpunk-style UI, audio feedback, and OTA updates.

## Critical Issue & Path Forward

### 1. WiFi Disconnects (errno=128) - **Fix Pending Flash**

- **Symptoms**: Device connects, then drops with `errno=128` ("Socket not connected") after ~30s.
- **Root Cause**: ESP32 WiFi power saving sleeps the radio, killing the persistent HA connection.
- **Fix Applied in YAML**: `wifi: power_save_mode: none` (Line 38).
- **Current Status**: **STALE FIRMWARE**. The user cancelled the clean build. The device is likely running code from 14:04 *without* this fix active.
- **Action Required**: MUST run a **Clean Build** and Flash.

### 2. Slow Builds (15+ mins)

- **Cause**: Building on `/mnt/c/Users/...` forces WSL to use the majestic but slow 9P file bridge.
- **Action Required**: Move project to `~/clawd-pager` (Linux Native FS). Builds will drop to ~45 seconds.

## Hardware

### M5StickC Plus 1.1 Specifications

| Component | Details |
| --------- | ------- |
| **Board** | M5StickC Plus 1.1 (ESP32-PICO-D4) |
| **Display** | ST7789V2 1.14" TFT LCD (240x135, rotated 270°) |
| **Power Management** | AXP192 PMIC (I2C: SDA=21, SCL=22, Addr=0x34) |
| **Button A** | GPIO37 |
| **Buzzer** | GPIO2 (passive, RTTTL compatible) |
| **USB Chip** | FTDI FT230X (VID:PID = 0403:6001) |

### ⚠️ CRITICAL: Backlight Control

**The M5StickC Plus 1.1 does NOT control backlight via GPIO!**  
Backlight is powered by **AXP192 PMU**. Use `external_components: [axp192]`.

## Configuration

### WiFi

- **SSID**: FlyingChanges
- **Password**: flyingchanges
- **IP**: 192.168.50.85
- **Power Save**: `none` (CRITICAL)

### Home Assistant

- **Status Sensor**: `input_text.clawd_status`
- **Diagnostic**: `sun.sun` (used to verify API connection)

## Development Workflow (Recommended)

1. **Move to Linux**:

    ```bash
    mkdir -p ~/clawd-pager
    cp -r /mnt/c/Users/monro/Codex/clawd-pager/* ~/clawd-pager/
    cd ~/clawd-pager
    ```

2. **Clean Build**:

    ```bash
    esphome clean clawd-pager.yaml
    ```

3. **Flash**:

    ```bash
    esphome run clawd-pager.yaml --device /dev/ttyUSB0
    ```

## Resolved Issues

- **Screen Black**: Fixed via AXP192 component.
- **Upload Failures**: Fixed by using USB instead of flaky WiFi OTA.
- **WiFi Power Save**: Config updated, pending flash.

## Version Info

- ESPHome: 2026.1.2
- Framework: Arduino + ESP-IDF 5.5.2
