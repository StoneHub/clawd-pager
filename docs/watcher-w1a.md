# SenseCap Watcher W1-A Development Guide

## Device Specs

| Component | Details |
|-----------|---------|
| MCU | ESP32-S3 (QFN56, rev v0.2) |
| AI Chip | Himax HX6538-A |
| RAM | 8MB PSRAM |
| Flash | 32MB |
| Display | 1.45" touch LCD (240x412) |
| Connectivity | Wi-Fi, BT 5 (LE) |
| USB | CH9102 dual serial (VID:PID 1a86:55d2) |
| MAC | f0:9e:9e:21:ca:18 |

## Serial Ports

When connected via USB, the W1-A presents two serial ports:

| Port | Chip | Use |
|------|------|-----|
| /dev/ttyACM0 | Himax AI | AI model management (python-sscma) |
| /dev/ttyACM1 | ESP32-S3 | Firmware flash & serial monitor |

## USB Passthrough (WSL)

From an **elevated PowerShell** on Windows:

```powershell
usbipd bind --busid 2-1
usbipd attach --wsl --busid 2-1
```

## Partition Table

| Partition | Offset | Size | Type |
|-----------|--------|------|------|
| nvsfactory | 0x9000 | 200K | NVS |
| nvs | 0x3B000 | 840K | NVS |
| otadata | 0x10D000 | 8K | Data |
| phy_init | 0x10F000 | 4K | Data |
| model | 0x110000 | 960K | Custom (0x82) |
| ota_0 | 0x200000 | 12MB | App |
| ota_1 | 0xE00000 | 12MB | App |

## Backups

**Critical:** Back up nvsfactory before any custom flashing. It contains device credentials for SenseCraft cloud.

```bash
source venv/bin/activate
esptool --chip esp32s3 --port /dev/ttyACM1 --baud 460800 \
  read-flash 0x9000 0x32000 watcher-backups/nvsfactory_backup.bin
```

Backups stored in `watcher-backups/` (gitignored).

## Building Firmware

```bash
# Activate ESP-IDF
source ~/esp/esp-idf/export.sh

# Build any example
cd watcher-firmware/examples/get_started
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM1 flash monitor
```

## Known Issues

- **2Mbaud over WSL causes corrupt data.** Use 460800 or lower for flash reads.
- **`idf.py set-target` resets the device.** Don't run concurrent serial operations.
- **python-sscma requires paho-mqtt v2** which conflicts with esphome's v1.6.1. Use separate venvs if needed.

## Firmware Source

Submodule: `watcher-firmware/` (SenseCAP-Watcher-Firmware)

Key examples:
- `get_started` - Touch-draw demo (verified working)
- `factory_firmware` - Full stock firmware
- `speech_recognize` - Speech recognition
- `sscma_client_monitor` - AI model monitoring

## External Resources

- [Getting Started Wiki](https://wiki.seeedstudio.com/getting_started_with_watcher/)
- [Flash Guide](https://wiki.seeedstudio.com/flash_watcher_agent_firmware/)
- [Build Environment](https://wiki.seeedstudio.com/build_watcher_development_environment/)
- [Pre-built Firmware](https://github.com/Seeed-Studio/OSHW-SenseCAP-Watcher)
