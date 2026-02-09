# Clawdbot Pager - Wear OS

Wear OS companion app for Clawdbot, designed for Pixel Watch 3 with LTE.

## Features

- **WebSocket Connection**: Real-time connection to Clawdbot Gateway
- **Push Notifications**: Receive alerts with priority-based vibration patterns
- **Standalone Operation**: Works independently over LTE (no phone required)
- **Background Service**: Maintains connection even when app is not in foreground

## Requirements

- Pixel Watch 3 (or Wear OS 4+ device)
- Android SDK 34+
- JDK 17+
- Clawdbot Gateway running and accessible

## Setup

1. **Clone and configure:**
   ```bash
   cd wearos
   cp local.properties.template local.properties
   # Edit local.properties with your gateway URL and auth token
   ```

2. **Build:**
   ```bash
   ./gradlew assembleDebug
   ```

3. **Install to watch:**
   ```bash
   # Enable ADB on watch: Settings > Developer options > ADB debugging
   # Connect via WiFi or USB
   adb connect <watch-ip>:5555
   adb -s <watch-device> install app/build/outputs/apk/debug/app-debug.apk
   ```

## Configuration

Edit `local.properties`:
```properties
GATEWAY_URL=ws://192.168.50.50:18789/watch
AUTH_TOKEN=your-gateway-token-here
```

## Project Structure

```
wearos/
├── app/
│   ├── src/main/
│   │   ├── kotlin/com/stonehub/clawdpager/
│   │   │   ├── MainActivity.kt          # Main UI activity
│   │   │   ├── ClawdPagerApplication.kt # App initialization
│   │   │   ├── service/
│   │   │   │   ├── PagerService.kt      # Foreground service
│   │   │   │   └── WebSocketClient.kt   # Gateway connection
│   │   │   ├── data/
│   │   │   │   ├── PagerConfig.kt       # Configuration storage
│   │   │   │   └── GatewayMessage.kt    # Message models
│   │   │   └── ui/
│   │   │       ├── theme/Theme.kt       # Material 3 theme
│   │   │       └── screens/MainScreen.kt
│   │   ├── res/                         # Resources
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts                     # Root build config
├── settings.gradle.kts
├── gradle.properties
└── local.properties.template
```

## Gateway Protocol

The app connects to `ws://<gateway>/watch` and exchanges JSON messages:

### Authentication
```json
{"type": "auth", "token": "...", "client": "wearos", "version": "1.0.0"}
```

### Notifications (from gateway)
```json
{
  "type": "notification",
  "priority": "info|warning|critical",
  "title": "Alert Title",
  "body": "Message content",
  "timestamp": 1234567890,
  "actions": ["dismiss", "acknowledge"]
}
```

## Development

### Run on emulator
```bash
# Create Wear OS emulator in Android Studio
# Tools > Device Manager > Create Virtual Device > Wear OS
./gradlew installDebug
```

### Debug logs
```bash
adb logcat -s WebSocketClient PagerService
```

## License

Private - StoneHub
