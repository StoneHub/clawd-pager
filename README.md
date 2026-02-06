# Clawd Pager

A wearable pager that displays messages from Claude Code and Home Assistant, with AI vision capabilities.

## Hardware Support

| Device | Status | Framework | Description |
|--------|--------|-----------|-------------|
| M5StickC Plus 1.1 | Working | ESPHome (YAML) | Original prototype. Displays HA status messages with cyberpunk UI. |
| SenseCap Watcher W1-A | In Progress | ESP-IDF (C) | ESP32-S3 + Himax AI chip. Button-driven interaction, MCP server integration. |

## Project Structure

```
clawd-pager/
├── m5stickc/              # M5StickC Plus ESPHome firmware
│   ├── clawd-pager.yaml   # Main working config
│   ├── original_working.yaml
│   └── minimal-test.yaml
├── watcher-firmware/      # SenseCAP Watcher SDK (submodule)
├── scripts/               # Build & deploy scripts (Windows)
├── docs/                  # Project documentation
│   ├── m5stickc-notes.md  # M5StickC hardware notes & troubleshooting
│   ├── build-optimization.md
│   └── watcher-w1a.md     # W1-A development guide
└── watcher-backups/       # Device flash backups (gitignored)
```

## W1-A Quick Start

```bash
# Activate ESP-IDF
source ~/esp/esp-idf/export.sh

# Build an example
cd watcher-firmware/examples/get_started
idf.py set-target esp32s3
idf.py build

# Flash (ESP32 is on ACM1, Himax on ACM0)
idf.py -p /dev/ttyACM1 flash monitor
```

## M5StickC Quick Start

```bash
source venv/bin/activate
esphome run m5stickc/clawd-pager.yaml
```

## Architecture

```
W1-A (button press) → MCP Server (localhost:8765) → Claude Code
                     ↘ Claude API (fallback)
                       ↘ Gemini API (fallback)
```

## Requirements

- WSL2 on Windows (tested on ARM64)
- ESP-IDF v5.2.1 (for W1-A)
- Python 3.12+ with venv (esptool, python-sscma)
- Node.js 20+ (for MCP server, future)
- usbipd-win (USB passthrough to WSL)
