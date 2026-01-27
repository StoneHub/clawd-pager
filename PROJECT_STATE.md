# Clawd Pager - Project State

**Last Updated**: 2026-01-27

## Project Overview

ESPHome project for M5StickC Plus that displays status messages from Home Assistant with a cyberpunk-style UI, audio feedback, and OTA updates.

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

The display backlight is powered by the **AXP192 PMU**, not a direct GPIO pin.
You MUST use the `martydingo/esphome-axp192` external component to enable the backlight:

```yaml
external_components:
  - source: github://martydingo/esphome-axp192
    components: [axp192]

i2c:
  id: bus_a
  sda: 21
  scl: 22

sensor:
  - platform: axp192
    model: M5STICKC
    address: 0x34
    i2c_id: bus_a
```

**Do NOT use `backlight_pin: GPIO27`** - that's for TTGO TDisplay, not M5StickC Plus!

### Key Pin Mapping

```text
GPIO2  - Buzzer (PWM)
GPIO5  - Display CS (strapping pin)
GPIO13 - Display SPI CLK
GPIO15 - Display SPI MOSI (strapping pin)
GPIO18 - Display Reset
GPIO23 - Display DC
GPIO37 - Button A (inverted)
```

## Development Environment

### Option 1: Windows + WSL2 (Slow - 600+ seconds for CMake)

```powershell
# From PowerShell in project directory
.\compile.ps1   # Compile only
.\flash.ps1     # Compile + flash via USB
.\upload.ps1    # Upload pre-compiled firmware (WiFi or USB)
.\logs.ps1      # View USB serial logs
.\logs.ps1 wifi # View logs via WiFi
```

### Option 2: ARM Linux (Recommended - Much Faster)

```bash
# Setup (one-time)
python3 -m venv ~/esphome-venv
source ~/esphome-venv/bin/activate
pip install esphome

# Clone repo
git clone https://github.com/StoneHub/clawd-pager.git
cd clawd-pager

# Compile (should be <60 seconds vs 600+ on WSL)
esphome compile clawd-pager.yaml

# Upload via WiFi/OTA (device must be on network)
esphome upload clawd-pager.yaml --device clawd-pager.local

# View logs
esphome logs clawd-pager.yaml --device clawd-pager.local
```

## USB Connection (Windows/WSL)

The M5StickC Plus uses an FTDI USB chip. To flash via USB on Windows with WSL:

### First-Time Setup

```powershell
# Install usbipd-win (Admin PowerShell)
winget install usbipd

# In WSL (one-time)
sudo usermod -a -G dialout $USER
# Then restart WSL: wsl --shutdown
```

### Each Session

```powershell
# 1. List USB devices
usbipd list
# Look for: "M5stack" or "0403:6001"

# 2. Bind device (one-time per device)
usbipd bind --busid 2-1

# 3. Attach to WSL
usbipd attach --wsl --busid 2-1

# 4. Verify in WSL
wsl ls -la /dev/ttyUSB*
# Should show /dev/ttyUSB0 or /dev/ttyUSB1
```

**Note:** The device usually appears as `/dev/ttyUSB1` (not USB0) when attached.

## WiFi Configuration

- **SSID**: FlyingChanges
- **Password**: flyingchanges
- **Device Hostname**: clawd-pager.local
- **IP Address**: 192.168.50.85 (DHCP assigned)
- **Fallback AP**: Clawd-Pager-Fallback / clawd-recovery

## Home Assistant Integration

The device pulls status messages from:

```yaml
entity_id: input_text.clawd_status
```

Create this helper in Home Assistant:

1. Settings → Devices & Services → Helpers
2. Create Helper → Text
3. Name: "Clawd Status", Entity ID: `input_text.clawd_status`

## Current UI Features

- **Status Bar**: Time (SNTP synced) + WiFi signal bars
- **Main Content**: Displays HA status message
- **Animations**: Scanning line when waiting for HA connection
- **Colors**: Cyberpunk theme (cyan header, magenta accents, yellow warnings)
- **Audio**:
  - Startup chime
  - Notification sound on HA status change
  - Button press blip

## Workflow Scripts

| Script | Purpose |
|--------|---------|
| `compile.ps1` | Compile only (no upload) |
| `upload.ps1` | Upload pre-compiled firmware (WiFi/USB choice) |
| `flash.ps1` | Compile + upload via USB |
| `logs.ps1` | View serial logs via USB |
| `logs.ps1 wifi` | View logs via WiFi |

## Known Issues

### Screen Not Turning On

The display uses `backlight_pin: GPIO27` in the st7789v config. If the screen is dark:

1. Check logs for `B/L Pin: GPIO27` (not GPIO4)
2. Ensure no pin conflicts between display and light components
3. Power cycle: Hold power 6 seconds to turn off, press briefly to turn on

### Slow WSL Builds

CMake takes 600+ seconds on WSL due to:

- Windows filesystem access overhead
- x86 emulation on ARM Windows
- **Solution**: Build on native ARM Linux machine

## Version Info

- ESPHome: 2026.1.2
- Framework: Arduino + ESP-IDF 5.5.2
- PlatformIO: espressif32 @ 55.03.35
