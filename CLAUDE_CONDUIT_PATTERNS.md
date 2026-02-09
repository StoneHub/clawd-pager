# Claude Conduit - Remote CLI Access Patterns

**Source:** Claude Conduit by A-Somniatore  
**Repo:** https://github.com/A-Somniatore/claude-conduit  
**Use Case:** Remote iOS access to Claude Code CLI sessions  
**Reviewed:** 2026-02-09

## The Problem They Solved

> "I kick off long coding tasks, walk away, and have no way to check progress or respond when Claude is waiting for input."

**Their solution:** Self-hosted daemon + iOS app to monitor and interact with Claude Code sessions from phone.

## Architecture

```
┌──────────┐ WebSocket / HTTP ┌──────────────┐
│ iPhone   │ ◄─────────────────│ Mac (daemon) │
│ app      │   over network    │ port 7860    │
└──────────┘                   └───────┬──────┘
                                       │
                                  tmux + node-pty
                                       │
                               ┌───────▼────────┐
                               │ Claude Code    │
                               │ CLI sessions   │
                               └────────────────┘
```

## Key Patterns to Adopt for Clawd-Pager

### 1. **WebSocket Protocol Design**

**Their approach:**
- `/terminal/:sessionId` - WebSocket endpoint for terminal I/O
- Attach tokens (single-use, 60s TTL) prevent session hijacking
- Backpressure control on WebSocket writes
- Clean disconnect handling

**For Wear OS:**
```kotlin
// WebSocket message format (inspired by their protocol)
sealed class GatewayMessage {
    data class Notification(
        val id: String,
        val title: String,
        val body: String,
        val priority: Priority,
        val timestamp: Long,
        val actions: List<Action>
    )
    
    data class Command(
        val id: String,
        val type: CommandType,
        val payload: String,
        val timestamp: Long
    )
    
    data class Response(
        val requestId: String,
        val status: String,
        val data: String?
    )
    
    data class Heartbeat(
        val timestamp: Long,
        val batteryLevel: Int?
    )
}
```

### 2. **Authentication Pattern**

**Their method:**
- Pre-shared key (PSK) auto-generated on first run
- Stored in `~/.config/claude-conduit/config.yaml` with 0o600 permissions
- All endpoints require `Authorization: Bearer <psk>`
- Timing-safe comparison to prevent timing attacks

**For Wear OS:**
```kotlin
// Use same pattern for gateway token
class GatewayAuth {
    private val token: String by lazy {
        securePrefs.getString("gateway_token", "") ?: ""
    }
    
    fun getAuthHeaders(): Map<String, String> {
        return mapOf("Authorization" to "Bearer $token")
    }
    
    // During initial setup
    fun saveToken(token: String) {
        securePrefs.edit()
            .putString("gateway_token", token)
            .apply()
    }
}
```

**Gateway endpoint:**
```
wss://fcfdev.tail-scale.ts.net:18789/watch
or
ws://192.168.50.50:18789/watch (local)
```

### 3. **Session Discovery & Real-time Updates**

**Their implementation:**
- Watch `~/.claude/projects/` with `chokidar` for JSONL file changes
- SSE stream (`/api/sessions/stream`) pushes updates to clients
- Full session list sent on every change

**For Wear OS (simplified):**
```kotlin
// Gateway pushes updates via WebSocket (not SSE)
data class SessionUpdate(
    val type: UpdateType,  // CONNECTED, DISCONNECTED, STATUS_CHANGE
    val sessions: List<Session>,
    val timestamp: Long
)

enum class UpdateType {
    CONNECTED,           // Watch connected
    DISCONNECTED,        // Watch disconnected
    STATUS_CHANGE,       // System status changed
    NEW_NOTIFICATION     // New notification available
}
```

### 4. **tmux-style Session Persistence**

**Their approach:**
- Create tmux session per Claude Code session
- Sessions persist across daemon restarts
- Can detach/reattach without losing state

**For Wear OS:**
Not directly applicable (watch doesn't have "sessions"), but the **concept** applies:

```kotlin
// Persistent connection state
data class ConnectionState(
    val isConnected: Boolean,
    val lastHeartbeat: Long,
    val pendingCommands: List<PendingCommand>,
    val notificationHistory: List<Notification>
)

// Save state on disconnect, restore on reconnect
class StateManager {
    suspend fun saveState(state: ConnectionState) {
        dataStore.edit { prefs ->
            prefs[STATE_KEY] = Json.encodeToString(state)
        }
    }
    
    suspend fun restoreState(): ConnectionState? {
        return dataStore.data.first()[STATE_KEY]?.let {
            Json.decodeFromString(it)
        }
    }
}
```

### 5. **Terminal I/O Bridge Pattern**

**Their implementation:**
- `node-pty` spawns `tmux attach` process
- Bridges PTY I/O to WebSocket
- Handles backpressure (pause reading if WebSocket buffer full)

**For Wear OS (adapted):**
```kotlin
// Instead of terminal I/O, we bridge voice/action events
class EventBridge {
    private val websocket: WebSocket
    
    // Watch → Gateway
    fun sendVoiceCommand(transcript: String) {
        val command = GatewayMessage.Command(
            id = UUID.randomUUID().toString(),
            type = CommandType.VOICE,
            payload = transcript,
            timestamp = System.currentTimeMillis()
        )
        websocket.send(Json.encodeToString(command))
    }
    
    fun sendQuickAction(action: QuickAction) {
        val command = GatewayMessage.Command(
            id = UUID.randomUUID().toString(),
            type = CommandType.QUICK_ACTION,
            payload = action.toString(),
            timestamp = System.currentTimeMillis()
        )
        websocket.send(Json.encodeToString(command))
    }
    
    // Gateway → Watch
    fun onNotification(notification: GatewayMessage.Notification) {
        displayNotification(notification)
        vibrate(notification.priority.pattern)
    }
}
```

### 6. **React Native + xterm.js Pattern**

**Their mobile stack:**
- React Native for cross-platform (iOS, potential Android)
- xterm.js in WebView for terminal rendering
- Native modules for filesystem, auth

**For Wear OS:**
We're using **native Kotlin + Jetpack Compose** instead, but the **UI concept** is similar:

```kotlin
// Terminal-style scrolling notification list
@Composable
fun NotificationStream() {
    LazyColumn(
        reverseLayout = false,  // Newest at bottom (like terminal)
        modifier = Modifier.fillMaxSize()
    ) {
        items(notifications) { notification ->
            NotificationCard(notification)
        }
    }
}

// Similar to their terminal view, but for notifications
@Composable
fun NotificationCard(notification: Notification) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        Column {
            Text(notification.title, style = MaterialTheme.typography.titleMedium)
            Text(notification.body, style = MaterialTheme.typography.bodyMedium)
            Row {
                notification.actions.forEach { action ->
                    Button(onClick = { handleAction(action) }) {
                        Text(action.label)
                    }
                }
            }
        }
    }
}
```

### 7. **Tailscale Integration**

**Their recommendation:**
> "I run it over Tailscale so my sessions are only accessible on my private mesh network."

**For Wear OS:**
```yaml
# Gateway config (when Tailscale enabled)
gateway:
  url: wss://fcfdev.tail-scale.ts.net:18789/watch
  # or local: ws://192.168.50.50:18789/watch
```

**Benefits:**
- Secure remote access (encrypted WireGuard tunnel)
- Works anywhere (coffee shop, travel, etc.)
- No port forwarding needed
- Automatic HTTPS/WSS certificates

**Setup:**
1. Install Tailscale on fcfdev and Pixel Watch
2. Use Tailscale hostname instead of local IP
3. Watch can connect from anywhere

### 8. **Configuration Management**

**Their approach:**
- YAML config at `~/.config/claude-conduit/config.yaml`
- Auto-generated PSK on first run
- File permissions 0o600 (owner-only)

**For Wear OS:**
```kotlin
// DataStore for configuration
data class PagerConfig(
    val gatewayUrl: String = "ws://192.168.50.50:18789/watch",
    val authToken: String = "",  // PSK equivalent
    val userId: String = "monroe",
    val notificationsEnabled: Boolean = true,
    val vibrationEnabled: Boolean = true,
    val heartbeatIntervalMs: Long = 30_000,
    val reconnectDelayMs: Long = 5_000,
    val maxReconnectAttempts: Int = -1  // infinite
)

// First-run setup wizard
@Composable
fun SetupScreen() {
    var gatewayUrl by remember { mutableStateOf("") }
    var authToken by remember { mutableStateOf("") }
    
    Column {
        Text("Connect to Clawdbot Gateway")
        
        OutlinedTextField(
            value = gatewayUrl,
            onValueChange = { gatewayUrl = it },
            label = { Text("Gateway URL") },
            placeholder = { Text("ws://192.168.50.50:18789/watch") }
        )
        
        OutlinedTextField(
            value = authToken,
            onValueChange = { authToken = it },
            label = { Text("Auth Token") },
            visualTransformation = PasswordVisualTransformation()
        )
        
        Button(onClick = { saveConfig(gatewayUrl, authToken) }) {
            Text("Connect")
        }
    }
}
```

### 9. **Service Management**

**Their approach (macOS LaunchAgent):**
- Auto-start on login
- Auto-restart on crash (10s throttle)
- Logs to `~/Library/Logs/claude-conduit/`

**For Wear OS (Foreground Service):**
```kotlin
class PagerService : LifecycleService() {
    override fun onCreate() {
        super.onCreate()
        
        // Create notification channel
        createNotificationChannel()
        
        // Start as foreground service
        val notification = createServiceNotification()
        startForeground(NOTIFICATION_ID, notification)
        
        // Connect to gateway
        lifecycleScope.launch {
            connectToGateway()
        }
    }
    
    private suspend fun connectToGateway() {
        while (true) {
            try {
                websocketClient.connect()
                // Connection successful
                isConnected = true
                updateNotification("Connected")
            } catch (e: Exception) {
                // Auto-retry with exponential backoff
                delay(reconnectDelay)
                reconnectDelay = min(reconnectDelay * 2, MAX_DELAY)
            }
        }
    }
    
    override fun onDestroy() {
        websocketClient.disconnect()
        super.onDestroy()
    }
}
```

### 10. **API Design**

**Their REST API:**
```
GET  /api/status           - Health check (no auth)
GET  /api/sessions         - List all sessions
POST /api/sessions/:id/attach - Attach to session
WS   /terminal/:sessionId  - Terminal WebSocket
```

**For Clawdbot Gateway (new endpoints needed):**
```
GET  /api/status           - Health check (existing)
WS   /watch                - Watch WebSocket (new)
POST /watch/notifications  - Send notification to watch (new)
GET  /watch/status         - Watch connection status (new)
```

**Example WebSocket flow:**
```
Watch → Gateway:  {"type": "heartbeat", "batteryLevel": 75}
Gateway → Watch:  {"type": "heartbeat_ack", "timestamp": 1234567890}

Gateway → Watch:  {"type": "notification", "title": "Motion detected", ...}
Watch → Gateway:  {"type": "notification_ack", "notificationId": "abc123"}

Watch → Gateway:  {"type": "command", "payload": "toggle lights"}
Gateway → Watch:  {"type": "response", "status": "ok", "data": "Lights toggled"}
```

## Implementation Checklist for Wear OS

### Phase 1: WebSocket Foundation
- [ ] Add `/watch` WebSocket endpoint to gateway
- [ ] Implement PSK auth (use gateway token)
- [ ] WebSocket client in Wear OS app (OkHttp)
- [ ] Heartbeat protocol (30s interval)
- [ ] Auto-reconnect with exponential backoff

### Phase 2: Notification System
- [ ] Push notifications from gateway to watch
- [ ] Priority-based routing (info/warning/critical)
- [ ] Action buttons on notifications
- [ ] Notification history (Room database)
- [ ] Acknowledge/dismiss flow

### Phase 3: Voice Commands
- [ ] Voice input → transcript → gateway
- [ ] Gateway → response → TTS playback
- [ ] Push-to-talk UI
- [ ] Voice wakeword (optional)

### Phase 4: Configuration
- [ ] Setup wizard (gateway URL + token)
- [ ] DataStore persistence
- [ ] Tailscale support (hostname input)
- [ ] Connection test before saving

### Phase 5: Production
- [ ] Foreground service with auto-start
- [ ] Battery optimization
- [ ] Error logging + crash reporting
- [ ] Secure storage (EncryptedSharedPreferences)

## Code Snippets for Gateway

### Add WebSocket endpoint (Node.js/Fastify example)
```javascript
// In Clawdbot gateway
fastify.get('/watch', { websocket: true }, (connection, req) => {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!validateToken(token)) {
        connection.socket.close(1008, 'Unauthorized');
        return;
    }
    
    // Track connected watch
    connectedWatches.add(connection);
    
    connection.socket.on('message', (message) => {
        const msg = JSON.parse(message);
        
        switch (msg.type) {
            case 'heartbeat':
                connection.socket.send(JSON.stringify({
                    type: 'heartbeat_ack',
                    timestamp: Date.now()
                }));
                break;
                
            case 'command':
                // Route to main Clawdbot session
                handleWatchCommand(msg.payload);
                break;
                
            case 'notification_ack':
                // Mark notification as read
                markNotificationRead(msg.notificationId);
                break;
        }
    });
    
    connection.socket.on('close', () => {
        connectedWatches.delete(connection);
    });
});

// Function to send notification to all connected watches
function notifyWatches(notification) {
    const message = JSON.stringify({
        type: 'notification',
        ...notification
    });
    
    connectedWatches.forEach(watch => {
        watch.socket.send(message);
    });
}
```

## Security Notes (from Claude Conduit)

1. **PSK Authentication**: Use timing-safe comparison
2. **Attach Tokens**: Single-use, short TTL (60s)
3. **Config Permissions**: 0o600 (owner-only read/write)
4. **Network Binding**: 
   - Development: `host: "127.0.0.1"` (localhost only)
   - Production: `host: "0.0.0.0"` + Tailscale VPN
5. **TLS/WSS**: Use for production (Tailscale provides this)

## Lessons Learned

1. **Keep it simple**: PSK auth is sufficient for personal use
2. **VPN > Port Forwarding**: Tailscale is easier and more secure
3. **Logs are critical**: Good logging saved them during debugging
4. **Auto-restart**: Service should recover from crashes automatically
5. **Config first-run**: Auto-generate secrets, don't make user create them
6. **Native mobile > Web**: Better battery life, faster, works offline

## References

- **Claude Conduit Repo**: https://github.com/A-Somniatore/claude-conduit
- **Reddit Discussion**: https://www.reddit.com/r/ClaudeAI/comments/1ifdv3s/
- **tmux**: https://github.com/tmux/tmux
- **node-pty**: https://github.com/microsoft/node-pty
- **xterm.js**: https://xtermjs.org/
- **Tailscale**: https://tailscale.com/

---

**Last Updated:** 2026-02-09  
**Status:** Ideas captured for gateway integration  
**Branch:** `wearos`
