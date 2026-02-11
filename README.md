# Clawd Pager 🦞📟

Remote control Claude Code sessions from M5StickC Plus and ePaper pagers. Monitor AI activity, answer questions, and keep coding sessions moving while away from your desk.

## Quick Start (New Machine)

### 1. Prerequisites

**Windows:**
- Docker Desktop (with WSL2)
- USB drivers (CP210x or CH340)
- Python 3.9+ (for bridge/dashboard server)

**Linux:**
- Docker or ESPHome CLI
- Python 3.9+

### 2. Clone & Setup

```bash
# Clone the repo
git clone https://github.com/StoneHub/clawd-pager.git
cd clawd-pager

# Copy secrets template
cp secrets.yaml.template secrets.yaml

# Edit secrets with your WiFi credentials
nano secrets.yaml
```

### 3. Install Python Dependencies

```bash
pip install aioesphomeapi websockets flask
```

### 4. Choose Your Path

**Path A: Just want to monitor Claude Code on this machine?**
→ See [Claude Code Integration](#claude-code-integration)

**Path B: Want to flash pager hardware?**
→ See platform-specific guides:
- Windows: [WINDOWS_SETUP.md](WINDOWS_SETUP.md)
- Linux/ARM: [EPAPER_QUICKSTART.md](EPAPER_QUICKSTART.md)

---

## Claude Code Integration

**Goal:** Hook Claude Code (Antigravity/OpenClaw) to send activity to pagers.

### Architecture

```
Claude Code (your machine)
    │
    ├─► bridge.py (port 8081)  ← Receives tool events
    │       │
    │       ├─► dashboard_server.py (port 8080)  ← Logs & broadcasts
    │       │       │
    │       │       └─► WebSocket feed (ws://localhost:8080/ws)
    │       │
    │       └─► Pagers (ESPHome API on :6053)
    │               ├─► M5StickC Plus (192.168.50.85)
    │               └─► ePaper (192.168.50.81)
    │
    └─► (Optional) Screensaver Dashboard ← Subscribes to WebSocket
```

### Setup Steps

#### 1. Start the Bridge Server

```bash
# Terminal 1: Start dashboard server (event logger & WebSocket)
cd clawd-pager/devtools
python dashboard_server.py

# Terminal 2: Start bridge (connects to pagers)
cd clawd-pager
python ~/clawd/scripts/bridge.py  # Or wherever your bridge.py lives
```

**Verify services:**
```bash
# Check dashboard server
curl http://localhost:8080/api/state

# Check bridge
curl http://localhost:8081/status
```

#### 2. Hook Claude Code

**Option A: OpenClaw Hook (Recommended)**

Add to your OpenClaw config (`~/.clawdbot/config.json` or similar):

```json
{
  "hooks": {
    "tool_use": "http://localhost:8081/agent"
  }
}
```

**Option B: Manual Hook Script**

Create `~/.config/claude-code/hooks/tool_use.sh`:

```bash
#!/bin/bash
# Hook script to send Claude Code events to pager bridge

EVENT_TYPE="$1"
TOOL="$2"
DETAILS="$3"

curl -s -X POST http://localhost:8081/agent \
  -H "Content-Type: application/json" \
  -d "{\"event_type\":\"$EVENT_TYPE\",\"tool\":\"$TOOL\",\"display_text\":\"$DETAILS\"}"
```

Make it executable:
```bash
chmod +x ~/.config/claude-code/hooks/tool_use.sh
```

#### 3. Test the Integration

```bash
# Terminal 3: Test sending an event
curl -X POST http://localhost:8081/agent \
  -H "Content-Type: application/json" \
  -d '{"event_type":"TOOL_START","tool":"Edit","display_text":"test.py","display_sub":"+5 -2"}'

# You should see:
# - Log entry in dashboard_server.py terminal
# - Update on connected pagers (if any)
# - Event in WebSocket feed (check with test-pager-feed.py)
```

#### 4. Monitor the Feed

```bash
# Watch events in real-time
cd clawd-pager
./test-pager-feed.py

# Or integrate into your screensaver dashboard
# See: IMPLEMENTATION-QUICKSTART.md
```

---

## Pager Configuration (Device-Specific)

### Network Setup

**Important:** Pagers use **static IPs** on your local network. Update these in your router's DHCP settings:

| Device | MAC Address | IP Address | Port |
|--------|-------------|------------|------|
| M5StickC Plus | (varies) | 192.168.50.85 | 6053 |
| ePaper | 98:88:E0:0F:6B:70 | 192.168.50.81 | 6053 |
| Bridge (this machine) | (local) | localhost | 8081 |
| Dashboard Server | (local) | localhost | 8080 |

**To change IPs:**
1. Edit `clawd-pager.yaml` or `clawd-pager-epaper.yaml`
2. Find `manual_ip:` section
3. Update `static_ip: 192.168.50.XX`
4. Recompile and flash firmware

**To update bridge.py for new IPs:**
Edit `~/clawd/scripts/bridge.py` and update the pager addresses in the config section.

---

## Documentation Map

| File | Purpose |
|------|---------|
| **README.md** | You are here - Quick start & integration guide |
| [WINDOWS_SETUP.md](WINDOWS_SETUP.md) | Windows development setup (Docker, USB drivers) |
| [EPAPER_QUICKSTART.md](EPAPER_QUICKSTART.md) | ePaper pager firmware setup |
| [IMPLEMENTATION-QUICKSTART.md](IMPLEMENTATION-QUICKSTART.md) | Add feed to screensaver dashboard (30 min) |
| [PAGER-FEED-INTEGRATION.md](PAGER-FEED-INTEGRATION.md) | Full architecture & API reference (25KB) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design decisions & rationale |
| [PROJECT_STATE.md](PROJECT_STATE.md) | Current status & known issues |

---

## Common Tasks

### Flash Pager Firmware (First Time)

**Windows:**
```powershell
# Compile firmware
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome compile clawd-pager-epaper.yaml

# Flash via web tool (if Docker USB doesn't work)
# 1. Go to: https://web.esphome.io
# 2. Upload: .esphome/build/clawd-pager-epaper/.pioenvs/clawd-pager-epaper/firmware.bin
```

**Linux:**
```bash
esphome compile clawd-pager.yaml
esphome run clawd-pager.yaml
```

### Update Firmware (OTA)

```bash
# After first flash, use OTA updates
esphome run clawd-pager.yaml --device 192.168.50.85

# Or via Docker
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome run clawd-pager.yaml --device 192.168.50.85
```

### Send Test Alert to Pager

```bash
# Via bridge API
curl -X POST http://localhost:8081/device/alert \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from gaming PC!"}'

# Via ESPHome API (direct)
curl -X POST http://192.168.50.85:6053/text_sensor/pager_display/set \
  -H "Content-Type: application/json" \
  -d '{"value":"Direct message"}'
```

### View Pager Logs

```bash
esphome logs clawd-pager.yaml --device 192.168.50.85

# Or via Docker
docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome logs clawd-pager.yaml --device 192.168.50.85
```

---

## Troubleshooting

### "Connection refused" when testing

**Cause:** Dashboard server or bridge not running  
**Fix:**
```bash
# Check what's running
netstat -tln | grep -E "(8080|8081)"

# Should see:
# 0.0.0.0:8080 (dashboard server)
# 0.0.0.0:8081 (bridge)

# If missing, start them (see Setup Steps above)
```

### Pagers not receiving events

**Cause:** Pager offline or wrong IP  
**Fix:**
```bash
# Ping pager
ping 192.168.50.85

# Check ESPHome API
curl http://192.168.50.85:6053/

# Check bridge config
grep "PAGER_.*_IP" ~/clawd/scripts/bridge.py
```

### Claude Code events not appearing

**Cause:** Hook not configured  
**Fix:**
```bash
# Test manually first
curl -X POST http://localhost:8081/agent \
  -H "Content-Type: application/json" \
  -d '{"event_type":"TOOL_START","tool":"Edit","display_text":"test.py"}'

# If that works, hook is misconfigured
# Check OpenClaw config or hook script permissions
```

---

## Project Status

### ✅ Working
- Bridge server (tool events → pagers)
- Dashboard server (event logging & WebSocket feed)
- M5StickC Plus firmware (audio, display, buttons)
- WebSocket feed integration
- Voice command capture

### ⚠️ In Progress
- ePaper display refresh (compiles, but screen not updating)
- Android Wear app (planned)
- Bi-directional session control

### 🎯 Next Steps
1. Fix ePaper SPI timing (display refresh crashes device)
2. Add inline buttons for Claude Code questions
3. Build Android Wear companion app
4. Voice-to-text for remote coding

---

## Contributing

This is Monroe's personal project for remote farm coding. If you're working on it:

1. **Always branch:** `git checkout -b feature/your-feature`
2. **Test before commit:** Verify on real hardware if changing firmware
3. **Document changes:** Update relevant .md files
4. **Use secrets.yaml:** Never commit WiFi credentials or API keys

---

## License

Private project - Not for public distribution.

---

**Questions?** Check the [full documentation](#documentation-map) or ask Monroe directly.

**Happy remote coding!** 🦞✨
