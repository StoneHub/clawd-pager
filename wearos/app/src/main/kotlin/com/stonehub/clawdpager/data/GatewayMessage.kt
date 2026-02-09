package com.stonehub.clawdpager.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Message received from Clawdbot Gateway via WebSocket
 */
@Serializable
data class GatewayMessage(
    val type: String = "notification",
    val priority: String = "info",
    val title: String = "",
    val body: String = "",
    val timestamp: Long = System.currentTimeMillis(),
    val actions: List<String> = emptyList(),
    @SerialName("message_id")
    val messageId: String? = null
)

/**
 * Message types from gateway
 */
object MessageType {
    const val NOTIFICATION = "notification"
    const val COMMAND = "command"
    const val RESPONSE = "response"
    const val HEARTBEAT = "heartbeat"
    const val AUTH = "auth"
    const val AUTH_SUCCESS = "auth_success"
    const val AUTH_FAILURE = "auth_failure"
}

/**
 * Priority levels for notifications
 */
object Priority {
    const val INFO = "info"
    const val WARNING = "warning"
    const val CRITICAL = "critical"
}

/**
 * Command message sent to gateway
 */
@Serializable
data class GatewayCommand(
    val type: String = "command",
    val command: String,
    val args: Map<String, String> = emptyMap(),
    val timestamp: Long = System.currentTimeMillis()
)

/**
 * Authentication message
 */
@Serializable
data class AuthMessage(
    val type: String = "auth",
    val token: String,
    val client: String = "wearos",
    val version: String = "1.0.0"
)
