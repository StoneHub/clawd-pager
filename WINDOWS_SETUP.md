# Clawd Pager ePaper - Windows Development Setup

## Prerequisites

1. **Docker Desktop for Windows** (with WSL2 backend)
   - Download: https://www.docker.com/products/docker-desktop
   - Enable WSL2 during installation

2. **USB Driver** (for ESP32-S3)
   - Download: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
   - Install CP210x or CH340 driver (depends on board variant)

3. **Git** (optional, for version control)
   - Download: https://git-scm.com/download/win

## Project Structure

```
clawd-pager/
├── clawd-pager-epaper.yaml    # Main ESPHome config
├── secrets.yaml               # WiFi credentials & API keys
├── EPAPER_DESIGN.md          # Design documentation
├── EPAPER_QUICKSTART.md      # Quick start guide
├── ARCHITECTURE.md           # Architecture decisions
└── WINDOWS_SETUP.md          # This file
```

## Setup Steps

### 1. Copy Project Files

Copy the entire `clawd-pager` folder to your Windows machine:
- Recommended location: `C:\Users\YourName\Documents\clawd-pager`

### 2. Configure Secrets

Edit `secrets.yaml` with your WiFi credentials:

```yaml
wifi_ssid: "YourWiFiName"
wifi_password: "YourWiFiPassword"
api_key: "your-32-char-api-key-here"
ota_password: "your-ota-password"
```

**Generate API key:**
```bash
# In PowerShell or WSL:
openssl rand -hex 32
```

### 3. Connect ESP32-S3 Device

1. Plug ESP32-S3 board into USB port
2. Check Device Manager for COM port (e.g., `COM3`)
3. Note the COM port number for next steps

## ESPHome Docker Commands (Windows)

### Compile Firmware

```powershell
# PowerShell (run in clawd-pager directory)
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome compile clawd-pager-epaper.yaml
```

### Flash via USB

```powershell
# Replace COM3 with your actual COM port
docker run --rm -v "${PWD}:/config" --device=COM3 ghcr.io/esphome/esphome run clawd-pager-epaper.yaml --device COM3
```

**Note**: Docker Desktop must have USB passthrough enabled. If this doesn't work, use the web flasher instead (see below).

### Flash via OTA (after first flash)

```powershell
# Find device IP first (check router or serial logs)
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome run clawd-pager-epaper.yaml --device 192.168.50.81
```

### View Logs

```powershell
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome logs clawd-pager-epaper.yaml
```

## Alternative: ESPHome Web Flasher

If Docker USB passthrough doesn't work:

1. **Compile firmware** via Docker (generates `.bin` file)
2. **Flash via browser**:
   - Go to: https://web.esphome.io
   - Click "Connect"
   - Select COM port
   - Upload the compiled `.bin` file from `.esphome/build/clawd-pager-epaper/.pioenvs/clawd-pager-epaper/firmware.bin`

## Troubleshooting

### Docker: "Error response from daemon: device not found"

**Solution**: Use ESPHome Web Flasher instead, or try WSL2 USB passthrough:
1. Install `usbipd-win`: https://github.com/dorssel/usbipd-win
2. Share USB device with WSL2
3. Run ESPHome in WSL2 instead of Windows Docker

### Device boots but display doesn't update

**Current Issue**: Display refresh may crash the device. Possible causes:
- Pin configuration mismatch
- SPI timing issues with this board variant
- ESPHome waveshare_epaper driver compatibility

**Debug steps**:
1. Check serial logs for crash messages
2. Try different `model:` values in YAML (1.54in-v2, 1.54in-m5stickc, etc.)
3. Consult Waveshare's official Arduino examples

### Compilation takes forever

**Expected**: First compile on x86 takes 5-10 minutes (downloading toolchains)
**Subsequent compiles**: 1-2 minutes (cached)

If Docker is slow on Windows:
1. Increase Docker Desktop memory allocation (Settings → Resources)
2. Use WSL2 backend (Settings → General → "Use WSL2 based engine")

## Current Status (as of 2026-02-10)

### ✅ Working
- ESPHome firmware compiles successfully
- Device boots and connects to WiFi
- ESPHome API responds on port 6053
- Services available: `show_message`, `refresh_display`

### ❌ Not Working
- **Display physical refresh** - screen still shows factory demo
- Possible issue: waveshare_epaper driver not fully compatible with ESP32-S3 variant
- Device may crash/reboot when display update is triggered

### Next Steps
1. Compile on x86 Windows (faster iteration)
2. Test with minimal lambda (just border, no text)
3. Try different SPI speeds / timings
4. Check Waveshare ESP32-S3 schematic for exact display controller model
5. Consider using Waveshare's Arduino library directly if ESPHome doesn't work

## Simplified Test Config

If you want to start with the absolute minimal test:

```yaml
# Minimal lambda - just a border
display:
  - platform: waveshare_epaper
    id: epaper_display
    model: 1.54in
    spi_id: epaper_spi
    cs_pin: GPIO12
    dc_pin: GPIO11
    reset_pin: GPIO10
    busy_pin: GPIO9
    update_interval: never  # Manual update only
    lambda: |-
      it.rectangle(0, 0, 200, 200);
```

Then trigger updates manually via API to test without crashes.

## Resources

- **ESPHome Docs**: https://esphome.io/components/display/waveshare_epaper.html
- **Waveshare Wiki**: https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board
- **Device Specs**: ESP32-S3-PICO-1, 200x200 ePaper (SSD1681 controller)
- **Current IP**: 192.168.50.81 (configure static DHCP reservation on router)

## Contact / Notes

- Original development on `fcfdev` (ARM, slow Docker)
- Device MAC: 98:88:E0:0F:6B:70
- Network: FlyingChangesIOT (2.4GHz only - ESP32-S3 doesn't support 5GHz)
