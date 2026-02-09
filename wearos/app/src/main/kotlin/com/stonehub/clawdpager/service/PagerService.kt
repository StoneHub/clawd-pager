package com.stonehub.clawdpager.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.stonehub.clawdpager.BuildConfig
import com.stonehub.clawdpager.ClawdPagerApplication
import com.stonehub.clawdpager.MainActivity
import com.stonehub.clawdpager.R
import com.stonehub.clawdpager.data.GatewayMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class PagerService : Service() {
    
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var webSocketClient: WebSocketClient
    private var notificationId = 100
    
    override fun onCreate() {
        super.onCreate()
        
        webSocketClient = WebSocketClient(
            gatewayUrl = BuildConfig.GATEWAY_URL,
            authToken = BuildConfig.AUTH_TOKEN
        )
        
        // Collect messages from WebSocket
        serviceScope.launch {
            webSocketClient.messages.collectLatest { message ->
                handleMessage(message)
            }
        }
        
        // Collect connection state
        serviceScope.launch {
            webSocketClient.connectionState.collectLatest { state ->
                updateServiceNotification(state)
            }
        }
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, createServiceNotification("Connecting..."))
        
        serviceScope.launch {
            webSocketClient.connect()
        }
        
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        webSocketClient.disconnect()
        serviceScope.cancel()
    }
    
    private fun createServiceNotification(status: String): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        return NotificationCompat.Builder(this, ClawdPagerApplication.CHANNEL_SERVICE)
            .setContentTitle("Clawdbot Pager")
            .setContentText(status)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }
    
    private fun updateServiceNotification(state: WebSocketClient.State) {
        val status = when (state) {
            WebSocketClient.State.CONNECTING -> "Connecting..."
            WebSocketClient.State.CONNECTED -> "Connected to Gateway"
            WebSocketClient.State.DISCONNECTED -> "Disconnected"
            WebSocketClient.State.RECONNECTING -> "Reconnecting..."
            is WebSocketClient.State.ERROR -> "Error: ${state.message}"
        }
        
        val notification = createServiceNotification(status)
        val manager = NotificationManagerCompat.from(this)
        try {
            manager.notify(1, notification)
        } catch (e: SecurityException) {
            // Permission not granted
        }
    }
    
    private fun handleMessage(message: GatewayMessage) {
        // Vibrate for new messages
        vibrateForPriority(message.priority)
        
        // Post notification
        postAlertNotification(message)
    }
    
    private fun vibrateForPriority(priority: String) {
        val vibrator = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            val manager = getSystemService(VibratorManager::class.java)
            manager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as Vibrator
        }
        
        val pattern = when (priority) {
            "critical" -> longArrayOf(0, 500, 100, 500, 100, 500)
            "warning" -> longArrayOf(0, 300, 100, 300)
            else -> longArrayOf(0, 200)
        }
        
        vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1))
    }
    
    private fun postAlertNotification(message: GatewayMessage) {
        val notification = NotificationCompat.Builder(this, ClawdPagerApplication.CHANNEL_ALERTS)
            .setContentTitle(message.title)
            .setContentText(message.body)
            .setSmallIcon(R.drawable.ic_notification)
            .setPriority(
                when (message.priority) {
                    "critical" -> NotificationCompat.PRIORITY_MAX
                    "warning" -> NotificationCompat.PRIORITY_HIGH
                    else -> NotificationCompat.PRIORITY_DEFAULT
                }
            )
            .setAutoCancel(true)
            .build()
        
        val manager = NotificationManagerCompat.from(this)
        try {
            manager.notify(++notificationId, notification)
        } catch (e: SecurityException) {
            // Permission not granted
        }
    }
}
