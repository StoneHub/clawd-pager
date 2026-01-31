# Clawd Pager Overhaul Plan: The Direct Link 🦞

## 🛑 Current Issues (Detected 2026-01-27)
1.  **CPU Overhead**: The "floaty text" logic was too heavy for the ESP32-PICO-D4, causing lag and unresponsive buttons.
2.  **State Stiction**: Home Assistant `input_text` persists old messages, making the pager feel like it's repeating itself.
3.  **Communication Latency**: The HA API loop (Pager -> HA -> AI -> HA -> Pager) is too slow for real-time interaction.
4.  **Connectivity/Sleep Loop**: Deep sleep made the device unreachable for updates, creating a "dead zone" during development.

---

## 🏗️ The Overhaul Strategy: "The Direct Link"

### Phase 1: Clean Foundation (Build 3 - Deploying Now)
*   **Remove all physics/slosh logic** to reclaim CPU cycles.
*   **Temporarily disable Deep Sleep** to allow for rapid OTA updates without manual wake-ups.
*   **Implement "Direct Link Ready" mode**: Switch from polling HA to exposing native ESPHome services.
*   **Startup Ritual**: Device clears HA state on boot to prevent ghost messages.

### Phase 2: Direct AI Control (Build 4 - Next)
*   **Bypass HA for Media**: I will talk directly to the Pager's API using `aioesphomeapi`.
*   **Raw Image Support**: Push binary snapshots (Wyze snippets, Memes) directly to the display buffer.
*   **Push-to-Talk (PTT)**: Button B becomes a hardware trigger to stream audio directly to the ClawdBridge script.

### Phase 3: The "Steve Jobs" Interface
*   **Contextual Buttons**: No more general "YES/NO" unless explicitly asked. Buttons perform actions based on the current "Direct" message.
*   **Haptic Signature**: Each type of alert (Security, Finance, Personal) gets a unique buzzer rhythm.

---

## 🛠️ Build Status
- **Build 3 (Overhaul Foundation)**: [DONE - 2026-01-27 18:05]
- **Build 4 (Direct Link & Mic)**: [UPLOADING...]
- **Pager Bridge Script**: [DRAFTED - pager_bridge.py]
- **Hardware Integration**: PDM Mic and Display Buffer established.

---

### Implementation Detail: The Direct Link Bridge
To achieve the "Steve Jobs" speed, I am launching a background bridge on the Pi.

**Bridge Logic (`pager_bridge.py`):**
1.  Connects to Pager via native `aioesphomeapi` (Low latency).
2.  Monitors **Button B** as a hardware interrupt.
3.  **PTT Trigger**: On Button B press, Clawdbot prepares to receive audio.
4.  **Instant Media**: Clawdbot pushes images directly to the Pager's display buffer.
