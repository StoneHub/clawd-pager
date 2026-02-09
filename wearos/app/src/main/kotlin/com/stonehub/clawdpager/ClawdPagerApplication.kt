package com.stonehub.clawdpager

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class ClawdPagerApplication : Application() {
    
    companion object {
        const val CHANNEL_SERVICE = "pager_service"
        const val CHANNEL_ALERTS = "pager_alerts"
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }
    
    private fun createNotificationChannels() {
        val serviceChannel = NotificationChannel(
            CHANNEL_SERVICE,
            "Pager Service",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Maintains connection to Clawdbot Gateway"
            setShowBadge(false)
        }
        
        val alertsChannel = NotificationChannel(
            CHANNEL_ALERTS,
            "Clawdbot Alerts",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Notifications from Clawdbot"
            enableVibration(true)
            vibrationPattern = longArrayOf(0, 250, 100, 250)
        }
        
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(serviceChannel)
        notificationManager.createNotificationChannel(alertsChannel)
    }
}
