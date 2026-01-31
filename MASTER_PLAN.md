# Clawd Pager Master Development Plan

## Strategy: "The Direct Link" 🦞
Instead of relying on slow Home Assistant loops, we are building a low-latency direct connection between the Pi and the Pager.

### Milestone 1: Stabilization Foundation [DONE]
**Goal**: Establish a rock-solid base with buttons and reliable display.

### Milestone 2: The Direct Bridge [LIVE]
**Goal**: Low-latency communication and PTT hardware.
- **Hero UI**: Large clock, battery bar, and weather widget.
- **Hardware PTT**: Instant "LISTENING" feedback.
- **Live Data**: Real Gmail and Calendar integration.

---

## 🏗️ Phase 3: Visual Peek & Session Memory (Current)
**Goal**: Context-aware interactions and rich media.

### 1. Persistent AI Sessions
- **Implementation**: The bridge will maintain a local conversation history for 10-15 minutes.
- **Contextual A Button**: If you click Button A after a voice query, I'll provide an *update* on that topic instead of a generic briefing.
- **Technology**: Local state management in `bridge.py` linking to Clawdbot's core memory.

### 2. Direct Framebuffer Push (Visual Peek)
- **Technology**: Use the `display` API to push raw binary pixels from the Pi.
- **Feature: Snapshots**: When a Wyze camera detects motion, I can push a 135x135 "Peek" of the face directly to the pager.

---

## 🏗️ Phase 4: Full Audio Pipeline
**Goal**: Debug and polish the voice interaction.

### 1. Whisper/Gemini Audio Processing
- **Implementation**: Pipe the `/tmp/clawd_voice.wav` into Gemini 3 Flash's multimodal input.
- **Challenge**: Resolving the "0 bytes" capture issue on the native ESPHome voice assistant protocol.

---

## 🛠️ Build Registry
- **Build 3**: Stabilization & Removed Physics.
- **Build 4**: Direct Link, PTT Hardware, & Hero UI.
- **Build 5 (Planned)**: Framebuffer API & Session Context.
