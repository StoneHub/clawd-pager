# Clawdbot Pager - Wear OS (Pixel Watch 3)

## Overview

Port the Clawdbot Pager concept to Wear OS for the Pixel Watch 3 with LTE. This provides a wrist-based interface for Clawdbot notifications, voice commands, and quick actions.

## Goals

- **Standalone Operation**: Full functionality via LTE without phone dependency
- **Voice-First Interface**: Google Assistant integration for commands
- **Real-time Notifications**: Push alerts from Clawdbot Gateway
- **Quick Actions**: Common tasks accessible via watch tiles
- **Battery Efficient**: Minimize battery drain while maintaining connectivity

## Architecture

```
┌─────────────────────────────────────────┐
│   Pixel Watch 3 (Wear OS 4)             │
│                                          │
│   ┌──────────────────────────────────┐  │
│   │  Clawdbot Pager App              │  │
│   │  - Foreground Service            │  │
│   │  - Notification Listener         │  │
│   │  - Voice Command Processor       │  │
│   │  - WebSocket Client              │  │
│   └──────────────────────────────────┘  │
│              ↕ HTTPS/WSS                 │
└──────────────┼──────────────────────────┘
               │ LTE Connection
               ↓
┌─────────────────────────────────────────┐
│   Clawdbot Gateway                       │
│   http://192.168.50.50:18789            │
│   (or Tailscale URL for remote access)  │
│                                          │
│   - WebSocket endpoint for watch        │
│   - REST API for commands                │
│   - Push notification system             │
└─────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   Main Clawdbot Session                  │
│   - Telegram integration                 │
│   - Task execution                       │
│   - Response routing                     │
└─────────────────────────────────────────┘
```

## Features

### Phase 1: Core Connectivity
- [ ] WebSocket connection to Clawdbot Gateway over LTE
- [ ] Authentication via gateway token
- [ ] Heartbeat/keep-alive mechanism
- [ ] Connection status indicator
- [ ] Basic notification display

### Phase 2: Notifications & Alerts
- [ ] Push notifications from Clawdbot
- [ ] Priority levels (info, warning, critical)
- [ ] Vibration patterns for different alert types
- [ ] Notification history view
- [ ] Quick dismiss/acknowledge

### Phase 3: Voice Commands
- [ ] Voice input via Google Assistant
- [ ] Speech-to-text transcription
- [ ] Send text commands to Clawdbot
- [ ] Voice response playback (TTS)
- [ ] Wake word integration ("Hey Clawdbot")

### Phase 4: Quick Actions
- [ ] Complication for watch face (status indicator)
- [ ] Tiles for common commands:
  - "Status" - System health check
  - "Home" - Smart home controls
  - "Tasks" - View/complete todos
  - "Emergency" - Critical alerts
- [ ] Custom action shortcuts

### Phase 5: Dashboard
- [ ] Mini dashboard view on watch:
  - Active tasks count
  - Last command timestamp
  - System status
  - Battery level (watch + host)
- [ ] Scrollable info cards
- [ ] Pull-to-refresh

## Tech Stack

### Development
- **Language**: Kotlin (official Wear OS)
- **IDE**: Android Studio
- **Min SDK**: API 30 (Wear OS 3.0)
- **Target SDK**: API 34 (Wear OS 4.0)

### Libraries
- **Networking**: 
  - `OkHttp` + `WebSocket` for gateway connection
  - `Retrofit` for REST API calls
- **UI**: 
  - Jetpack Compose for Wear OS
  - Material Design 3 for Wear
- **Voice**:
  - Google Speech Recognition API
  - Android Text-to-Speech
- **Background**:
  - Foreground Service for persistent connection
  - WorkManager for scheduled tasks
- **Data**:
  - DataStore for preferences
  - Room for local notification cache

### Gateway Integration
- **Endpoint**: `ws://192.168.50.50:18789/watch` (or WSS for remote)
- **Auth**: Bearer token from gateway config
- **Message Format**: JSON
  ```json
  {
    "type": "notification|command|response",
    "priority": "info|warning|critical",
    "title": "Alert Title",
    "body": "Message content",
    "timestamp": 1234567890,
    "actions": ["dismiss", "acknowledge", "reply"]
  }
  ```

## Implementation Phases

### Phase 1: Foundation (Week 1)
1. Set up Wear OS project structure
2. Implement WebSocket client
3. Basic UI with connection status
4. Test LTE connectivity
5. **Deliverable**: App connects to gateway and shows "Connected" status

### Phase 2: Notifications (Week 2)
1. Implement notification receiver
2. Build notification UI (cards)
3. Add vibration patterns
4. History/archive system
5. **Deliverable**: Watch receives and displays alerts from Clawdbot

### Phase 3: Voice Input (Week 3)
1. Integrate Google Speech Recognition
2. Build voice command UI
3. Send transcribed commands to gateway
4. Display command acknowledgment
5. **Deliverable**: Voice commands work end-to-end

### Phase 4: Polish & Features (Week 4)
1. Add complications
2. Build tiles for quick actions
3. Implement dashboard view
4. Battery optimization
5. Error handling & recovery
6. **Deliverable**: Production-ready v1.0

## Configuration

### Watch App Config
Store in DataStore:
```kotlin
data class PagerConfig(
    val gatewayUrl: String = "ws://192.168.50.50:18789/watch",
    val authToken: String = "",
    val userId: String = "monroe",
    val notificationEnabled: Boolean = true,
    val vibrationEnabled: Boolean = true,
    val voiceWakeWord: Boolean = false,
    val autoReconnect: Boolean = true
)
```

### Gateway Changes Needed
1. Add WebSocket endpoint `/watch` for Wear OS clients
2. Implement push notification routing
3. Add watch-specific command handlers
4. Create watch authentication method

## Development Workflow

### Local Testing
1. **Watch Emulator**: Android Studio Wear OS emulator
2. **Debug Bridge**: `adb connect <watch-ip>:5555`
3. **Gateway**: Local fcfdev gateway (192.168.50.50)

### Remote Testing
1. **Tailscale**: Connect watch to Tailscale network
2. **Gateway URL**: Use Tailscale HTTPS endpoint
3. **Production**: Test over actual T-Mobile LTE

### Build & Deploy
```bash
# Debug build
./gradlew assembleDebug

# Install to watch
adb -s <watch-device> install app/build/outputs/apk/debug/app-debug.apk

# Release build
./gradlew assembleRelease
# Sign with release keystore
```

## Security Considerations

1. **Authentication**: Use gateway token (same as dashboard)
2. **Transport**: HTTPS/WSS for all connections
3. **Storage**: Encrypt credentials in DataStore
4. **Network**: Certificate pinning for gateway
5. **Permissions**: Request only necessary (INTERNET, VIBRATE, RECORD_AUDIO)

## Battery Optimization

1. **Connection**: WebSocket keep-alive with adaptive intervals
2. **Background**: Use WorkManager for periodic tasks
3. **Wake**: Only wake for critical notifications
4. **Display**: Minimize always-on display usage
5. **Voice**: On-demand speech recognition (not always listening)

## Testing Strategy

### Unit Tests
- WebSocket message parsing
- Command formatting
- Authentication logic
- Notification priority handling

### Integration Tests
- Gateway connection lifecycle
- Voice command end-to-end
- Notification delivery
- Tile interactions

### Manual Testing
- LTE connectivity in various conditions
- Battery life over 24 hours
- Voice recognition accuracy
- Notification latency

## Future Enhancements

### v1.1
- [ ] Offline queue for commands (sync when connected)
- [ ] Customizable notification filters
- [ ] Multi-gateway support (home/away)

### v1.2
- [ ] Watch face integration (custom complications)
- [ ] Gesture controls (shake to clear, twist to activate)
- [ ] Haptic feedback patterns for different events

### v1.3
- [ ] Local voice processing (on-device wake word)
- [ ] Smart reply suggestions
- [ ] Integration with Wear OS health data

## Repository Structure

```
clawd-pager/
├── wearos/                    # Wear OS app (this branch)
│   ├── app/
│   │   ├── src/
│   │   │   ├── main/
│   │   │   │   ├── kotlin/com/stonehub/clawdpager/
│   │   │   │   │   ├── MainActivity.kt
│   │   │   │   │   ├── service/
│   │   │   │   │   │   ├── PagerService.kt
│   │   │   │   │   │   └── WebSocketClient.kt
│   │   │   │   │   ├── ui/
│   │   │   │   │   │   ├── theme/
│   │   │   │   │   │   ├── screens/
│   │   │   │   │   │   └── components/
│   │   │   │   │   ├── data/
│   │   │   │   │   └── util/
│   │   │   │   ├── res/
│   │   │   │   └── AndroidManifest.xml
│   │   │   └── test/
│   │   └── build.gradle.kts
│   ├── gradle/
│   ├── build.gradle.kts
│   └── settings.gradle.kts
├── m5stickc/                  # M5StickC Plus (master)
├── docs/
│   └── WEAROS_PLAN.md        # This file
└── README.md
```

## Getting Started

### Prerequisites
1. Android Studio (latest stable)
2. Pixel Watch 3 with LTE activated
3. Clawdbot Gateway accessible (local or Tailscale)
4. T-Mobile prepaid data plan active

### Initial Setup
```bash
# Clone the repo and switch to wearos branch
git clone https://github.com/StoneHub/clawd-pager.git
cd clawd-pager
git checkout wearos

# Open in Android Studio
# Tools → Device Manager → Create Wear OS Virtual Device
# Or connect physical Pixel Watch via adb

# Configure gateway URL in local.properties
echo "GATEWAY_URL=ws://192.168.50.50:18789/watch" >> local.properties
echo "AUTH_TOKEN=your-gateway-token-here" >> local.properties

# Build and run
./gradlew installDebug
```

## Success Criteria

**v1.0 is complete when:**
- [ ] Watch connects to gateway over LTE
- [ ] Receives and displays Clawdbot notifications
- [ ] Voice commands work and execute successfully
- [ ] Battery lasts >12 hours with normal use
- [ ] Connection auto-recovers from network drops
- [ ] App works independently (no phone needed)

## Notes

- **Gateway Token**: Use the same token as the dashboard (`~/.clawdbot/clawdbot.json`)
- **Tailscale**: For remote access, add watch to Tailscale network
- **Phone Independence**: This is a standalone app - phone can be off/dead
- **Network**: T-Mobile LTE only (no WiFi fallback by design)

---

**Status**: 🚧 In Planning  
**Branch**: `wearos`  
**Target Platform**: Pixel Watch 3 (Wear OS 4)  
**Primary Developer**: Monroe + Clawdbot  
**Timeline**: 4 weeks to v1.0
