package com.stonehub.clawdpager

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.stonehub.clawdpager.data.PagerConfigRepository
import com.stonehub.clawdpager.service.PagerService
import com.stonehub.clawdpager.ui.screens.MainScreen
import com.stonehub.clawdpager.ui.theme.ClawdPagerTheme
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    
    private val configRepository by lazy { PagerConfigRepository(applicationContext) }
    private val connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    
    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startPagerService()
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            val config by configRepository.configFlow.collectAsState(initial = null)
            val state by connectionState.collectAsState()
            
            ClawdPagerTheme {
                MainScreen(
                    connectionState = state,
                    gatewayUrl = config?.gatewayUrl ?: BuildConfig.GATEWAY_URL,
                    onConnectClick = { startPagerService() },
                    onDisconnectClick = { stopPagerService() }
                )
            }
        }
        
        // Check notification permission for Android 13+
        checkNotificationPermission()
    }
    
    override fun onResume() {
        super.onResume()
        updateConnectionState()
    }
    
    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    startPagerService()
                }
                else -> {
                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        } else {
            startPagerService()
        }
    }
    
    private fun startPagerService() {
        val intent = Intent(this, PagerService::class.java)
        ContextCompat.startForegroundService(this, intent)
        connectionState.value = ConnectionState.Connecting
    }
    
    private fun stopPagerService() {
        val intent = Intent(this, PagerService::class.java)
        stopService(intent)
        connectionState.value = ConnectionState.Disconnected
    }
    
    private fun updateConnectionState() {
        // TODO: Query actual service state via binding or broadcast
        lifecycleScope.launch {
            // For now, assume connecting if service should be running
        }
    }
}

sealed class ConnectionState {
    data object Disconnected : ConnectionState()
    data object Connecting : ConnectionState()
    data object Connected : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}
