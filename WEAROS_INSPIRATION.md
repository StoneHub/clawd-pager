# Wear OS Development - Ideas & Patterns

**Source:** Telegram Concierge for macOS  
**Repo:** https://github.com/permaevidence/ConciergeforTelegram  
**Reviewed:** 2026-02-09

## Key Patterns to Adopt

### 1. **Voice Input Architecture**
From Concierge's WhisperKit integration:

**Their Pattern:**
- On-device transcription (CoreML/WhisperKit)
- Send voice → transcribe locally → forward text to LLM
- Battery-efficient, fast response

**For Pixel Watch:**
```kotlin
// Use Android Speech Recognition or on-device ML Kit
class VoiceCommandHandler {
    fun recordAndTranscribe() {
        // Record audio from watch mic
        // Transcribe locally with ML Kit Speech
        // Send text to gateway via WebSocket
        // Display acknowledgment on watch
    }
}
```

**Why it's better:** Faster than sending audio over LTE, uses less battery

### 2. **Persistent Connection Pattern**

**Their Architecture:**
```
TelegramBotService (long-polling)
    ↓
ConversationManager (state + dispatch)
    ↓
ToolExecutor (30+ actions)
```

**For Wear OS:**
```
WebSocketClient (persistent connection)
    ↓
NotificationDispatcher (priority routing)
    ↓
QuickActionHandler (tiles, complications, buttons)
```

**Implementation Ideas:**
- Heartbeat every 30s to keep connection alive
- Auto-reconnect with exponential backoff (5s, 10s, 30s, 60s)
- Queue messages offline, sync when reconnected
- State machine: Disconnected → Connecting → Connected → Reconnecting

### 3. **Reminder System + Self-Orchestration**

**Their Feature:**
- AI sets reminders for itself
- Recurring patterns (daily, weekly, monthly)
- Natural language parsing ("remind me in 15 minutes")

**For Watch:**
```kotlin
data class WatchReminder(
    val id: String,
    val title: String,
    val triggerTime: Long,
    val recurrence: Recurrence? = null,  // daily, weekly, etc.
    val notificationPattern: VibrationPattern,
    val actions: List<QuickAction>  // buttons on notification
)

enum class VibrationPattern {
    INFO,      // gentle buzz
    WARNING,   // double buzz
    CRITICAL   // persistent strong vibration
}
```

**Use Cases:**
- "Check on security camera in 10 min" → watch schedules local reminder
- Daily morning briefing at 7 AM
- Recurring "standup time" notifications

### 4. **Multimodal Notification System**

**Their Capabilities:**
- Text alerts
- Voice message playback
- Image analysis results
- Document summaries
- Rich action buttons

**For Watch (scaled down):**
```kotlin
sealed class WatchNotification {
    data class Text(val title: String, val body: String, val priority: Priority)
    data class Image(val title: String, val imageUrl: String, val thumbnail: ByteArray)
    data class VoiceResponse(val title: String, val audioData: ByteArray)
    data class QuickPoll(val question: String, val options: List<String>)
}

data class NotificationAction(
    val label: String,
    val actionId: String,
    val icon: Int  // Material icon resource
)
```

**Examples:**
- Security camera motion → show thumbnail + "View Full" / "Dismiss"
- Task reminder → "Complete" / "Snooze 15m" / "Delegate"
- System alert → "Acknowledge" / "Call Support"

### 5. **Keychain/Secure Storage Pattern**

**Their Approach:**
- Store API keys in macOS Keychain
- Never write secrets to disk
- Runtime-only credential loading

**For Android:**
```kotlin
// Use EncryptedSharedPreferences
private val securePrefs = EncryptedSharedPreferences.create(
    context,
    "clawd_pager_secure",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)

fun saveGatewayToken(token: String) {
    securePrefs.edit().putString("gateway_token", token).apply()
}
```

**Never store:**
- Gateway auth token in plaintext
- User credentials
- Session cookies

### 6. **Tool/Action Dispatcher Pattern**

**Their System:**
- 30+ tools (email, calendar, web search, shortcuts)
- Parallel execution where possible
- Structured tool definitions (OpenAI function calling format)
- Result caching

**For Watch (simplified):**
```kotlin
sealed class QuickAction {
    object CheckStatus : QuickAction()
    data class ToggleDevice(val deviceId: String) : QuickAction()
    data class CompleteTask(val taskId: String) : QuickAction()
    data class SnoozeAlert(val alertId: String, val minutes: Int) : QuickAction()
    data class SendVoiceCommand(val transcript: String) : QuickAction()
}

class ActionDispatcher {
    suspend fun execute(action: QuickAction): Result<String> {
        return when (action) {
            is QuickAction.CheckStatus -> getSystemStatus()
            is QuickAction.ToggleDevice -> toggleHomeDevice(action.deviceId)
            is QuickAction.CompleteTask -> markTaskComplete(action.taskId)
            // etc.
        }
    }
}
```

**Wear OS Tiles:**
- Status Tile → CheckStatus action
- Home Control Tile → ToggleDevice shortcuts
- Tasks Tile → View/complete tasks
- Emergency Tile → Critical actions (call Monroe, trigger alarm)

### 7. **Offline Queue + Sync Pattern**

**Their Approach:**
- Cache pending operations
- Retry on reconnect
- Conflict resolution

**For Watch:**
```kotlin
data class PendingCommand(
    val id: String,
    val timestamp: Long,
    val action: QuickAction,
    val retryCount: Int = 0,
    val maxRetries: Int = 3
)

class OfflineQueue {
    private val queue = mutableListOf<PendingCommand>()
    
    fun enqueue(action: QuickAction) {
        queue.add(PendingCommand(
            id = UUID.randomUUID().toString(),
            timestamp = System.currentTimeMillis(),
            action = action
        ))
        saveToStorage()
    }
    
    suspend fun syncWhenOnline() {
        queue.forEach { command ->
            try {
                execute(command.action)
                queue.remove(command)
            } catch (e: Exception) {
                // Retry logic
            }
        }
    }
}
```

**Use Case:** Voice command while offline → queued → executes when LTE reconnects

### 8. **Battery Optimization Strategies**

**From their design:**
- Aggressive connection throttling
- Lazy-load resources
- Minimize wake-ups
- Efficient data structures

**For Wear OS:**
```kotlin
class BatteryOptimizer {
    // Adaptive heartbeat based on battery level
    fun getHeartbeatInterval(): Long {
        return when (batteryLevel) {
            in 0..15 -> 120_000L   // 2 min when low
            in 16..50 -> 60_000L   // 1 min normal
            else -> 30_000L        // 30s when charging/full
        }
    }
    
    // Reduce notification vibration when battery low
    fun getVibrationPattern(priority: Priority): VibrationPattern {
        if (batteryLevel < 15 && priority != Priority.CRITICAL) {
            return VibrationPattern.MINIMAL
        }
        return priority.defaultPattern
    }
}
```

### 9. **Complication (Watch Face) Integration**

**Concept:** Show live data on watch face

**Ideas:**
```kotlin
// Complication that shows Clawdbot status
class ClawdPagerComplication : ComplicationProviderService() {
    override fun onComplicationUpdate(
        complicationId: Int,
        dataType: Int,
        callback: ComplicationUpdateCallback
    ) {
        val status = getConnectionStatus()
        val data = when (dataType) {
            SHORT_TEXT -> ShortTextComplicationData.Builder(
                text = PlainComplicationText.Builder(status).build(),
                contentDescription = PlainComplicationText.Builder("Clawdbot Status").build()
            ).build()
            // etc.
        }
        callback.onUpdateComplication(data)
    }
}
```

**Display Options:**
- 🟢 "Online" / 🔴 "Offline"
- Pending task count
- Last notification time
- Battery level of host system

### 10. **Gesture Controls**

**Ideas (not in Concierge, but inspired):**
- Shake watch → clear all notifications
- Twist wrist → open dashboard
- Double-tap crown → trigger emergency action
- Swipe from edge → quick action menu

```kotlin
class GestureHandler {
    fun onShake() {
        clearAllNotifications()
        showConfirmation("All cleared")
    }
    
    fun onTwist() {
        launchDashboard()
    }
    
    fun onDoubleTapCrown() {
        triggerEmergencyAction()
    }
}
```

## Architecture Diagram (Inspired by Concierge)

```
┌─────────────────────────────────────────┐
│  Pixel Watch 3 (Wear OS App)            │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  UI Layer                           │ │
│  │  - MainScreen (connection status)   │ │
│  │  - NotificationCards                │ │
│  │  - VoiceInputScreen                 │ │
│  │  - DashboardView                    │ │
│  │  - Tiles (Status, Home, Tasks)      │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Service Layer                      │ │
│  │  - PagerService (foreground)        │ │
│  │  - WebSocketClient (connection)     │ │
│  │  - NotificationDispatcher           │ │
│  │  - VoiceCommandHandler              │ │
│  │  - OfflineQueue                     │ │
│  │  - ReminderScheduler                │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Data Layer                         │ │
│  │  - PagerConfig (DataStore)          │ │
│  │  - SecurePreferences (tokens)       │ │
│  │  - NotificationHistory (Room)       │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │ WSS over LTE
               ↓
┌─────────────────────────────────────────┐
│  Clawdbot Gateway                        │
│  /watch WebSocket endpoint               │
│                                          │
│  Message Router:                         │
│  - Notifications → Watch                 │
│  - Voice commands → Main session         │
│  - Quick actions → Home Assistant / etc. │
└─────────────────────────────────────────┘
```

## Development Phases (Refined)

### Phase 1: Core (Week 1)
- [x] Project structure initialized
- [ ] WebSocket client with reconnect logic
- [ ] Basic notification display
- [ ] Connection status UI
- [ ] Secure token storage

**Test:** Watch connects, shows "Connected" status, receives test notification

### Phase 2: Voice (Week 2)
- [ ] Voice recording permission
- [ ] ML Kit Speech integration
- [ ] Voice command UI (push-to-talk button)
- [ ] Transcript display + send to gateway
- [ ] Voice response playback (TTS)

**Test:** Say "What's my schedule today" → watch sends command → receives response

### Phase 3: Notifications (Week 2-3)
- [ ] Priority-based vibration patterns
- [ ] Rich notification cards (text, image thumbnail, actions)
- [ ] Notification history view
- [ ] Quick reply buttons
- [ ] Dismiss/snooze functionality

**Test:** Receive security camera alert with thumbnail and "View Full" / "Dismiss" buttons

### Phase 4: Quick Actions (Week 3)
- [ ] Tiles implementation (Status, Home, Tasks)
- [ ] Complication for watch face
- [ ] Offline queue + sync
- [ ] Reminder system

**Test:** Offline → tap "Toggle lights" → reconnects → action executes

### Phase 5: Polish (Week 4)
- [ ] Battery optimization (adaptive heartbeat)
- [ ] Gesture controls
- [ ] Dashboard view (scrollable stats)
- [ ] Error recovery + logging
- [ ] Onboarding flow (gateway setup)

**Test:** Use watch all day, battery lasts 12+ hours, all features work reliably

## Success Metrics

**v1.0 is production-ready when:**
- [ ] Maintains connection for 24 hours without manual intervention
- [ ] Receives and displays notifications < 5 seconds from gateway send
- [ ] Voice commands transcribe accurately 90%+ of the time
- [ ] Battery life > 12 hours with normal use
- [ ] Works completely standalone (phone can be off)
- [ ] Survives network drops and auto-recovers
- [ ] All quick actions execute successfully
- [ ] No crashes after 48 hours continuous use

## Next Steps When Development Starts

1. **Set up dev environment:**
   - Android Studio + Wear OS emulator
   - Physical Pixel Watch 3 for testing
   - Clawdbot gateway WebSocket endpoint

2. **Gateway Changes:**
   - Add `/watch` WebSocket route
   - Implement push notification system
   - Add watch authentication
   - Create watch-specific message format

3. **First Milestone:**
   - Get watch to connect and show "Connected" status
   - Send test notification from gateway
   - Display notification on watch
   - Reply with "Acknowledged" button

4. **Iterate from there:**
   - Add voice input
   - Add more notification types
   - Build out quick actions
   - Optimize battery usage

## References

- **Concierge Repo:** https://github.com/permaevidence/ConciergeforTelegram
- **Android Speech Recognition:** https://developer.android.com/reference/android/speech/SpeechRecognizer
- **ML Kit Speech:** https://developers.google.com/ml-kit/vision/text-recognition
- **Wear OS Tiles:** https://developer.android.com/training/wearables/tiles
- **Wear OS Complications:** https://developer.android.com/training/wearables/components/complications
- **WebSocket (OkHttp):** https://square.github.io/okhttp/4.x/okhttp/okhttp3/-web-socket/
- **DataStore:** https://developer.android.com/topic/libraries/architecture/datastore
- **EncryptedSharedPreferences:** https://developer.android.com/reference/androidx/security/crypto/EncryptedSharedPreferences

---

**Last Updated:** 2026-02-09  
**Status:** Ideas captured for future development  
**Branch:** `wearos`
