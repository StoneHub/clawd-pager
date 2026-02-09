package com.stonehub.clawdpager.service

import android.util.Log
import com.stonehub.clawdpager.data.GatewayMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class WebSocketClient(
    private val gatewayUrl: String,
    private val authToken: String
) {
    
    companion object {
        private const val TAG = "WebSocketClient"
        private const val RECONNECT_DELAY_MS = 5000L
        private const val HEARTBEAT_INTERVAL_MS = 30000L
    }
    
    sealed class State {
        data object CONNECTING : State()
        data object CONNECTED : State()
        data object DISCONNECTED : State()
        data object RECONNECTING : State()
        data class ERROR(val message: String) : State()
    }
    
    private val json = Json { 
        ignoreUnknownKeys = true 
        isLenient = true
    }
    
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // No timeout for WebSocket
        .connectTimeout(10, TimeUnit.SECONDS)
        .pingInterval(HEARTBEAT_INTERVAL_MS, TimeUnit.MILLISECONDS)
        .build()
    
    private var webSocket: WebSocket? = null
    private var shouldReconnect = true
    
    private val _connectionState = MutableStateFlow<State>(State.DISCONNECTED)
    val connectionState: StateFlow<State> = _connectionState
    
    private val _messages = MutableSharedFlow<GatewayMessage>()
    val messages: SharedFlow<GatewayMessage> = _messages
    
    private val scope = CoroutineScope(Dispatchers.IO)
    
    fun connect() {
        if (_connectionState.value == State.CONNECTED || 
            _connectionState.value == State.CONNECTING) {
            return
        }
        
        shouldReconnect = true
        _connectionState.value = State.CONNECTING
        
        val request = Request.Builder()
            .url(gatewayUrl)
            .apply {
                if (authToken.isNotEmpty()) {
                    addHeader("Authorization", "Bearer $authToken")
                }
            }
            .build()
        
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected")
                _connectionState.value = State.CONNECTED
                
                // Send authentication message
                val authMessage = """{"type":"auth","token":"$authToken","client":"wearos"}"""
                webSocket.send(authMessage)
            }
            
            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "Received: $text")
                try {
                    val message = json.decodeFromString<GatewayMessage>(text)
                    scope.launch {
                        _messages.emit(message)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse message: $text", e)
                }
            }
            
            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closing: $code $reason")
                webSocket.close(1000, null)
            }
            
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closed: $code $reason")
                _connectionState.value = State.DISCONNECTED
                scheduleReconnect()
            }
            
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket error: ${t.message}", t)
                _connectionState.value = State.ERROR(t.message ?: "Connection failed")
                scheduleReconnect()
            }
        })
    }
    
    fun disconnect() {
        shouldReconnect = false
        webSocket?.close(1000, "User requested disconnect")
        webSocket = null
        _connectionState.value = State.DISCONNECTED
    }
    
    fun send(message: String): Boolean {
        return webSocket?.send(message) ?: false
    }
    
    private fun scheduleReconnect() {
        if (!shouldReconnect) return
        
        _connectionState.value = State.RECONNECTING
        scope.launch {
            delay(RECONNECT_DELAY_MS)
            if (shouldReconnect) {
                connect()
            }
        }
    }
}
