# Quick Start: ePaper Development on Windows

## 1. Prerequisites (5 minutes)

- [ ] Install **Docker Desktop** → https://www.docker.com/products/docker-desktop
- [ ] Install **USB driver** → https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- [ ] Plug in ESP32-S3 device, note COM port (e.g., `COM3`)

## 2. Setup (2 minutes)

1. Copy this folder to: `C:\Users\YourName\Documents\clawd-pager`
2. Rename `secrets.yaml.template` → `secrets.yaml`
3. Edit `secrets.yaml`:
   - Add your WiFi SSID/password
   - Generate API key: `openssl rand -hex 32` (or use any 64-char hex string)

## 3. First Build (10 minutes)

Open PowerShell in the `clawd-pager` folder:

```powershell
# Compile firmware (first time = slow, downloads toolchain)
.\build.ps1 compile

# Flash via USB (replace COM3 with your port)
.\build.ps1 flash-usb -ComPort COM3
```

## 4. After First Flash

Once the device is on WiFi, use OTA (much faster):

```powershell
# Edit YAML, then flash wirelessly
.\build.ps1 flash-ota -DeviceIP 192.168.50.81

# View live logs
.\build.ps1 logs -DeviceIP 192.168.50.81
```

## 5. If USB Flash Fails

Use the **ESPHome Web Flasher** instead:

1. Compile: `.\build.ps1 compile`
2. Go to: https://web.esphome.io
3. Connect → Select COM port
4. Upload: `.esphome\build\clawd-pager-epaper\.pioenvs\clawd-pager-epaper\firmware.bin`

## Current Issue to Debug

- ✅ Firmware compiles and flashes successfully
- ✅ Device boots, connects to WiFi, ESPHome API works
- ❌ **Display doesn't physically update** (still shows factory demo)

**Suspected cause**: `waveshare_epaper` driver may not fully support this ESP32-S3 board variant.

**Next debugging steps**:
1. Try minimal lambda (just border, no text) - see `WINDOWS_SETUP.md`
2. Test different SPI speeds
3. Check Waveshare Arduino examples to verify hardware works
4. Compare schematic vs pin config

## Files to Edit

- **clawd-pager-epaper.yaml** - Main config (display settings, pins, lambda)
- **secrets.yaml** - WiFi credentials (gitignored)

## Helpful Commands

```powershell
# View current config without compiling
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome config clawd-pager-epaper.yaml

# Clean build cache (if weird errors)
Remove-Item -Recurse -Force .esphome

# Check device is online
Test-NetConnection 192.168.50.81 -Port 6053
```

## Get Help

- ESPHome Docs: https://esphome.io
- Waveshare Wiki: https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board
- Read: `WINDOWS_SETUP.md` for detailed troubleshooting
