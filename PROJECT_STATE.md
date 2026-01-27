# Clawd Pager - Project State

**Last Updated**: 2026-01-27 17:50 EST

## ✅ WORKING - Integration Successful!

**Status**: Device successfully connected to Home Assistant with 1 device and 4 entities showing!

## Root Cause - VERSION MISMATCH (SOLVED)

### The Real Problem

**ESPHome version incompatibility with Home Assistant!**

- **Home Assistant**: 2025.1.4 with `aioesphomeapi==28.0.0`
- **ESPHome (initial)**: 2026.1.2 with `aioesphomeapi==43.13.0`
- **Problem**: Protocol mismatch caused "Marker byte invalid: 0" errors and handshake timeouts

### The Solution

**Downgraded ESPHome to 2024.12.4** to match Home Assistant's API protocol version:

```bash
source /home/monroe/clawd/esphome-env/bin/activate
pip install esphome==2024.12.4  # Uses aioesphomeapi==24.6.2
esphome clean clawd-pager.yaml
esphome compile clawd-pager.yaml
esphome upload clawd-pager.yaml --device 192.168.50.85
```

Then in Home Assistant:
1. Delete ESPHome integration
2. Re-add: Settings → Devices & Services → + Add Integration → ESPHome
3. Host: `192.168.50.85`, Port: `6053`, No encryption key
4. **SUCCESS**: 1 device, 4 entities appear!

## Current Configuration

### Versions (WORKING)
- **ESPHome**: 2024.12.4
- **aioesphomeapi**: 24.6.2
- **Home Assistant**: 2025.1.4
- **Framework**: Arduino + ESP-IDF
- **Build**: 2026-01-27 17:45 EST

### API Configuration
```yaml
api:
  # Encryption disabled for compatibility testing
  # key: "fyJkdxgmn1RZ9UqRQQWw++0Wks2mK+nMQ7RybTuwK+U="
```

### WiFi
- **SSID**: FlyingChanges
- **Password**: flyingchanges
- **IP**: 192.168.50.85
- **Power Save**: `none` (CRITICAL - prevents disconnects)

### Home Assistant Entities
- **Status Input**: `input_text.clawd_status` (main message display)
- **Diagnostic**: `sun.sun` (API connection test)
- **Entities Exposed**: WiFi Signal, Battery Level, Button A, Button B

## Hardware Specs

| Component | Details |
| --------- | ------- |
| **Board** | M5StickC Plus 1.1 (ESP32-PICO-D4) |
| **Display** | ST7789V2 1.14" TFT LCD (240x135, rotated 270°) |
| **Power Management** | AXP192 PMIC (I2C: SDA=21, SCL=22, Addr=0x34) |
| **Button A** | GPIO37 |
| **Button B** | GPIO39 |
| **Buzzer** | GPIO2 (passive, RTTTL compatible) |
| **USB Chip** | FTDI FT230X (VID:PID = 0403:6001) |

**CRITICAL**: M5StickC Plus 1.1 uses AXP192 for backlight control (not GPIO)!

## Testing Message Flow

Send test message from Home Assistant:
```yaml
# Developer Tools → Actions
service: input_text.set_value
data:
  entity_id: input_text.clawd_status
  value: "Test Message!"
```

Expected behavior:
- M5StickC beeps (RTTTL tone)
- Screen shows "SYNCED" (green) at top
- Message displays in center
- Battery % and WiFi signal shown

## Development Workflow

```bash
# Activate environment
source /home/monroe/clawd/esphome-env/bin/activate

# Compile
esphome compile clawd-pager.yaml

# Upload via OTA
esphome upload clawd-pager.yaml --device 192.168.50.85

# View logs
esphome logs clawd-pager.yaml --device 192.168.50.85
```

## Troubleshooting History

### Issues Encountered & Resolved

1. **Black Screen** → Fixed with AXP192 component for backlight
2. **WiFi Disconnects** → Fixed with `power_save_mode: none`
3. **Encryption Key Mismatch** → Initially suspected, but was red herring
4. **"Marker byte invalid: 0" errors** → **ROOT CAUSE: Version mismatch**
5. **"No devices or entities"** → Fixed by downgrading ESPHome to 2024.12.4

### What Didn't Work

- Disabling encryption (wasn't the real issue)
- Rebuilding firmware from scratch with same version
- Restarting Home Assistant
- USB flashing (didn't fix version mismatch)
- Trying ESPHome 2025.12.7 (still too new, uses aioesphomeapi 43.2.1)

### What Actually Fixed It

**ESPHome 2024.12.4** - The key was matching the API protocol version to Home Assistant's expectations.

## Version Compatibility Reference

| Home Assistant | Compatible ESPHome | aioesphomeapi |
|----------------|-------------------|---------------|
| 2025.1.4       | 2024.12.4         | 24.6.2        |
| 2025.1.4       | ❌ 2025.12.7      | 43.2.1 (too new) |
| 2025.1.4       | ❌ 2026.1.2       | 43.13.0 (too new) |

## Next Steps (Optional)

1. **Test message flow** - Confirm messages display on M5StickC
2. **Re-enable encryption** (if needed):
   - Generate new key in YAML
   - Compile and flash
   - Delete and re-add HA integration with new key
3. **Update Home Assistant** to 2026.1.x to use latest ESPHome features

## HA Access

- **URL**: http://192.168.50.50:8123
- **Token**: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI1ODU3YjI5MDkyMDE0N2IwYjQzYjMzOTFmZGJlMjliOSIsImlhdCI6MTc2OTU0Njk0MiwiZXhwIjoyMDg0OTA2OTQyfQ.NIznc36woc6J0_L1HQFiwuvvdLVbjN3A3oBOzTDJfhU

## Lesson Learned

**Always check ESPHome/Home Assistant version compatibility!** The ESPHome API protocol (`aioesphomeapi`) must be compatible between the device firmware and Home Assistant's integration. Newer ESPHome versions may not work with older Home Assistant installations.
