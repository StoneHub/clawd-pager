package com.stonehub.clawdpager.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.wear.compose.material3.Button
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.Text
import com.stonehub.clawdpager.ConnectionState
import com.stonehub.clawdpager.ui.theme.StatusConnected
import com.stonehub.clawdpager.ui.theme.StatusConnecting
import com.stonehub.clawdpager.ui.theme.StatusDisconnected
import com.stonehub.clawdpager.ui.theme.StatusError

@Composable
fun MainScreen(
    connectionState: ConnectionState,
    gatewayUrl: String,
    onConnectClick: () -> Unit,
    onDisconnectClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(16.dp)
        ) {
            // Status indicator
            StatusIndicator(state = connectionState)
            
            Spacer(modifier = Modifier.height(8.dp))
            
            // Status text
            Text(
                text = when (connectionState) {
                    ConnectionState.Connected -> "Connected"
                    ConnectionState.Connecting -> "Connecting..."
                    ConnectionState.Disconnected -> "Disconnected"
                    is ConnectionState.Error -> "Error"
                },
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onBackground,
                textAlign = TextAlign.Center
            )
            
            Spacer(modifier = Modifier.height(4.dp))
            
            // Gateway URL (truncated)
            Text(
                text = gatewayUrl.removePrefix("ws://").removePrefix("wss://").take(20),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                textAlign = TextAlign.Center
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Connect/Disconnect button
            Button(
                onClick = {
                    when (connectionState) {
                        ConnectionState.Connected -> onDisconnectClick()
                        ConnectionState.Disconnected, is ConnectionState.Error -> onConnectClick()
                        ConnectionState.Connecting -> { /* Do nothing while connecting */ }
                    }
                },
                modifier = Modifier.fillMaxWidth(0.8f),
                enabled = connectionState !is ConnectionState.Connecting
            ) {
                Text(
                    text = when (connectionState) {
                        ConnectionState.Connected -> "Disconnect"
                        ConnectionState.Connecting -> "Connecting..."
                        else -> "Connect"
                    }
                )
            }
        }
    }
}

@Composable
private fun StatusIndicator(state: ConnectionState) {
    val color = when (state) {
        ConnectionState.Connected -> StatusConnected
        ConnectionState.Connecting -> StatusConnecting
        ConnectionState.Disconnected -> StatusDisconnected
        is ConnectionState.Error -> StatusError
    }
    
    Box(
        modifier = Modifier
            .size(24.dp)
            .clip(CircleShape)
            .background(color)
    )
}
