# Pager Integration Architecture

**Current State**: Python Bridge + ESPHome API
**Question**: Bridge vs MCP Server vs Hybrid?

---

## What We Have Installed

### ✅ Skills
1. **`clawdbot-pager`** skill
   - Python bridge service (`bridge.py`)
   - ESPHome API integration (aioesphomeapi)
   - UDP audio streaming
   - Google STT / Whisper fallback
   - Event logging + dashboard

2. **`homeassistant`** skill
   - REST API for HA integration
   - Could add ESPHome devices to HA dashboard
   - Access via long-lived token

### ✅ Current Bridge Architecture (v4.0)

```
┌──────────────┐     ESPHome API      ┌──────────────┐
│  M5 Pager    │◄───────────────────►│    Bridge    │
│ (ESP32)      │      Port 6053       │  (Python)    │
│              │                      │              │
│              │─ UDP Audio ────────►│  UDP:12345   │
└──────────────┘      Port 12345      │              │
                                      │  API:8081    │◄─── Claude Code
                                      └──────────────┘
                                           │
                                           │ STT (Google/Whisper)
                                           ▼
                                      ┌──────────────┐
                                      │  Clawdbot    │
                                      │  Gateway     │
                                      └──────────────┘
                                           │
                                           ▼
                                      [ Telegram ]
```

**Files**:
- `~/clawd/scripts/bridge.py` (69KB) - Main service
- `/etc/systemd/system/clawdbot-pager.service` - systemd unit
- `~/clawd/work/clawd-pager/devtools/` - Event logging/dashboard

**What It Does**:
1. Connects to pager via ESPHome native API
2. Listens for button presses, state changes
3. Receives UDP audio stream when voice button held
4. Transcribes audio (Google STT or Whisper)
5. Sends to Clawdbot for processing
6. Returns response to pager display
7. Logs all events to SQLite dashboard

---

## Option Analysis: Bridge vs MCP

### **Option 1: Keep Python Bridge (RECOMMENDED)**

**Pros**:
- ✅ Already working for M5 pager
- ✅ Supports multiple pagers (M5 + ePaper simultaneously)
- ✅ Direct ESPHome API access (fast, reliable)
- ✅ Built-in audio streaming (UDP)
- ✅ Event logging + dashboard
- ✅ No external dependencies

**Cons**:
- ⚠️ Python-only (not language-agnostic like MCP)
- ⚠️ Custom protocol (not standardized)

**Best For**: Device control, real-time interaction, audio streaming

---

### **Option 2: MCP Server**

**What is MCP?**
- Model Context Protocol (Anthropic)
- Standardized interface for LLM tools
- JSON-RPC over stdio or HTTP
- Great for exposing tools to Claude Desktop/Code

**Example MCP Structure**:
```
mcp-pager-server/
├── index.js (or .py)
├── tools/
│   ├── send_alert.js
│   ├── show_question.js
│   └── get_status.js
└── package.json
```

**Pros**:
- ✅ Standardized protocol
- ✅ Works with Claude Desktop, Code, etc.
- ✅ Easy to expose as tools ("send pager alert", etc.)
- ✅ Language-agnostic (Node, Python, Go)

**Cons**:
- ❌ Doesn't handle real-time device events (button presses)
- ❌ No audio streaming support
- ❌ Overkill for single-device integration
- ❌ Requires bridge *underneath* for ESPHome connection

**Best For**: Exposing pager as a tool to LLMs (send alerts, ask questions)

---

### **Option 3: Hybrid (Bridge + MCP Wrapper)**

```
┌──────────────┐     ESPHome API      ┌──────────────┐
│  Pagers      │◄───────────────────►│    Bridge    │
│ M5 + ePaper  │      Port 6053       │  (Python)    │
└──────────────┘                      │              │
                                      │  API:8081    │
                                      └──────────────┘
                                           │
                            ┌──────────────┴──────────────┐
                            │                             │
                            ▼                             ▼
                      ┌──────────┐                  ┌──────────┐
                      │   MCP    │                  │ Clawdbot │
                      │  Server  │                  │ Gateway  │
                      └──────────┘                  └──────────┘
                            │
                            ▼
                      [ Claude Code ]
```

**MCP Server** exposes:
- `send_pager_alert(message, priority)`
- `ask_user_question(question, timeout)`
- `get_pager_status()`

**Bridge** handles:
- Device connections (ESPHome)
- Audio streaming
- Real-time events
- Response routing

**Pros**:
- ✅ Best of both worlds
- ✅ Bridge handles device complexity
- ✅ MCP exposes clean tool interface
- ✅ Works with any LLM client

**Cons**:
- ⚠️ More components to maintain
- ⚠️ Slight latency overhead

---

## Recommendation for ePaper Pager

### **Short Term: Extend Python Bridge**

**Why**:
1. ePaper pager = another ESPHome device (just like M5)
2. Bridge already supports multiple devices
3. No new infrastructure needed
4. Works today

**Changes Needed**:
```python
# In bridge.py, add second device connection
PAGER_M5_IP = "192.168.50.85"
PAGER_EPAPER_IP = "192.168.50.86"  # New ePaper device

# Connect to both
m5_client = await connect_pager(PAGER_M5_IP)
epaper_client = await connect_pager(PAGER_EPAPER_IP)

# Route messages based on priority/type
if message.priority == "LOW":
    await epaper_client.show_dashboard()
else:
    await m5_client.show_alert()
```

---

### **Long Term: Add MCP Wrapper (Optional)**

**When**: After ePaper is working, if you want Claude Code to easily interact

**Implementation** (~50 lines):
```javascript
// mcp-pager/index.js
import { McpServer } from "@anthropic/mcp-sdk";

const server = new McpServer({
  name: "pager",
  version: "1.0.0"
});

server.tool("send_alert", async ({ message, priority }) => {
  const res = await fetch("http://localhost:8081/api/alert", {
    method: "POST",
    body: JSON.stringify({ message, priority })
  });
  return { success: true };
});

server.tool("ask_question", async ({ question, timeout }) => {
  const res = await fetch("http://localhost:8081/api/question", {
    method: "POST",
    body: JSON.stringify({ question, timeout })
  });
  return await res.json(); // { answer: "yes" | "no" }
});
```

---

## Decision Matrix

| Use Case | Architecture |
|----------|--------------|
| **Get ePaper working** | Extend Python bridge |
| **Multi-device support** | Python bridge (already designed for it) |
| **Claude Code integration** | Bridge works via hooks (already done) |
| **Expose as LLM tools** | Add MCP wrapper later |
| **Home Assistant dashboard** | Use HA skill + ESPHome integration |

---

## Action Plan for ePaper

### Phase 1: Hardware (THIS WEEK)
1. ✅ Create `epaper` branch (done)
2. ✅ Initial YAML config (done)
3. ⏳ Identify Waveshare model number
4. ⏳ Update GPIO pins
5. ⏳ Compile and flash firmware

### Phase 2: Bridge Integration (NEXT WEEK)
1. Add ePaper device to `bridge.py`
2. Test button presses
3. Test display updates
4. Implement dashboard mode

### Phase 3: Multi-Device Logic (LATER)
1. Route alerts by priority (HIGH → M5 beep, LOW → ePaper silent)
2. Sync state between devices
3. Device preferences (which shows what)

### Phase 4: MCP Wrapper (OPTIONAL)
1. Create `mcp-pager` package
2. Expose 3-5 tools to Claude Code
3. Test with Claude Desktop

---

## Files to Update

### For ePaper Hardware
- `~/clawd/work/clawd-pager/clawd-pager-epaper.yaml` ← Waveshare model, pins

### For Bridge Integration
- `~/clawd/scripts/bridge.py` ← Add second device connection
- `~/clawd/skills/skills/clawdbot-pager/SKILL.md` ← Document ePaper

### For MCP (if/when)
- Create `~/clawd/mcp-servers/pager/` ← New MCP package
- Update Claude Code config to include MCP server

---

## Summary

**What to do RIGHT NOW**:
1. ✅ Use Python bridge (already working)
2. ⏳ Get ePaper firmware flashed
3. ⏳ Add ePaper to bridge.py (copy M5 connection code)
4. ⏳ Test dashboard display

**What to do LATER (optional)**:
- Add MCP wrapper if you want cleaner Claude Code integration
- Add Home Assistant dashboard for web UI

**Bottom Line**: You already have the right architecture. Just extend it for ePaper!
