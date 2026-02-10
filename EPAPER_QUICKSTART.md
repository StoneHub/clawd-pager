# ePaper Pager - Quick Start Guide

**Hardware**: Waveshare ESP32-S3-ePaper-1.54 (200x200)
**Branch**: `epaper`
**Goal**: Get high-density dashboard working

---

## Pre-Flight Checklist

### 1. Identify Your Waveshare Model

Look at the ePaper display controller chip (back of display or board silkscreen):
- **SSD1681** → Use model: `1.54in` (black/white)
- **IL0373** → Use model: `1.54in-m5stickc-b` (black/white/red)
- **SSD1680** → Use model: `1.54in` (older version)

**Currently configured**: `1.54in` (standard black/white)

### 2. Verify GPIO Pins

Check your board's schematic or silkscreen markings. Update if different:

```yaml
# Display SPI
clk_pin: GPIO18
mosi_pin: GPIO23
cs_pin: GPIO10
dc_pin: GPIO11
reset_pin: GPIO12
busy_pin: GPIO13

# I2C (RTC/PMIC)
sda: GPIO20
scl: GPIO19
```

### 3. Create secrets.yaml

```bash
cd ~/clawd/work/clawd-pager
cat > secrets.yaml <<EOF
wifi_ssid: "YourWiFiName"
wifi_password: "YourWiFiPassword"
api_key: "$(openssl rand -base64 32)"
ota_password: "lobster2024"
EOF
```

---

## Flash Firmware

### Step 1: Compile
```bash
cd ~/clawd/work/clawd-pager
git checkout epaper
source ~/clawd/esphome-env/bin/activate
esphome compile clawd-pager-epaper.yaml
```

**Expected**: Clean compile with no errors
**If errors**: Check Waveshare model matches your hardware

### Step 2: Connect USB
Plug ESP32-S3 into your computer via USB-C

### Step 3: Upload
```bash
esphome upload clawd-pager-epaper.yaml
```

ESPHome will auto-detect USB serial port.

**First boot**: Device will compile and flash (~5 minutes)

### Step 4: Verify Boot
```bash
esphome logs clawd-pager-epaper.yaml --device 192.168.50.XX
```

Look for:
- WiFi connection
- ePaper initialization
- "🦞 Clawd Pager ePaper booting..."

---

## Test Display

### Via ESPHome Dashboard

1. Open: http://localhost:8080 (if dashboard running)
2. Click "Logs" on pager device
3. Send test via API:

```bash
curl -X POST http://192.168.50.XX:6053/text_sensor/pager_display/set \
  -d '{"state": "TEST MESSAGE"}'
```

### Via Bridge (After Setup)

```python
# Add to bridge.py
PAGER_EPAPER_IP = "192.168.50.XX"

# Test command
python3 -c "
import asyncio
from aioesphomeapi import APIClient

async def test():
    client = APIClient('192.168.50.XX', 6053, '')
    await client.connect()
    await client.text_sensor_command('pager_display', 'Hello ePaper!')
    
asyncio.run(test())
"
```

---

## Troubleshooting

### Display is blank
- Check `busy_pin` - ePaper uses BUSY to signal ready
- Try full refresh: disconnect power for 10 seconds
- Verify SPI pins match your board

### WiFi won't connect
- Check `secrets.yaml` credentials
- Try hotspot fallback: connect to `Clawd-Pager-ePaper` AP
- Check router logs for device MAC

### Compilation errors
**Error**: `unknown board esp32-s3-devkitc-1`
**Fix**: Update board to match your hardware:
```yaml
esp32:
  board: esp32-s3-box-3  # Or your actual board variant
```

**Error**: `waveshare model not found`
**Fix**: Check ESPHome docs for supported models:
https://esphome.io/components/display/waveshare_epaper.html

### Ghosting on display
- Add `full_update_every: 30` to force periodic full refresh
- Increase `update_interval` to reduce partial refresh artifacts

---

## Next Steps

### 1. Static IP Assignment
Add to YAML for reliable bridge connection:
```yaml
wifi:
  manual_ip:
    static_ip: 192.168.50.86
    gateway: 192.168.50.1
    subnet: 255.255.255.0
```

### 2. Add to Bridge
Edit `~/clawd/scripts/bridge.py`:
```python
PAGER_EPAPER_IP = "192.168.50.86"

# In main():
epaper_client = await connect_pager(PAGER_EPAPER_IP)
```

### 3. Test Dashboard Mode
```bash
# Send dashboard update
curl http://localhost:8081/api/update \
  -d '{"device": "epaper", "mode": "DASHBOARD", "message": "AGENT: Idle"}'
```

### 4. Refine Layout
Edit dashboard lambda in YAML:
- Adjust font sizes
- Add more data sections
- Test information density

---

## Reference

| Item | Value |
|------|-------|
| **Firmware** | `clawd-pager-epaper.yaml` |
| **Branch** | `epaper` |
| **IP** | 192.168.50.86 (to be assigned) |
| **ESPHome Port** | 6053 |
| **OTA Password** | lobster2024 |
| **Fallback AP** | Clawd-Pager-ePaper |

---

## Files Created

- ✅ `clawd-pager-epaper.yaml` - Firmware config
- ✅ `EPAPER_DESIGN.md` - Layout mockups
- ✅ `ARCHITECTURE.md` - Bridge vs MCP analysis
- ✅ `EPAPER_QUICKSTART.md` - This guide

**Ready to flash!** 🦞
