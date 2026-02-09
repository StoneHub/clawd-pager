package com.stonehub.clawdpager.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.stonehub.clawdpager.BuildConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

// Extension for DataStore
private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "pager_config")

/**
 * Pager configuration data class
 */
data class PagerConfig(
    val gatewayUrl: String = BuildConfig.GATEWAY_URL,
    val authToken: String = BuildConfig.AUTH_TOKEN,
    val userId: String = "default",
    val notificationsEnabled: Boolean = true,
    val vibrationEnabled: Boolean = true,
    val autoReconnect: Boolean = true
)

/**
 * Repository for managing pager configuration
 */
class PagerConfigRepository(private val context: Context) {
    
    companion object {
        private val KEY_GATEWAY_URL = stringPreferencesKey("gateway_url")
        private val KEY_AUTH_TOKEN = stringPreferencesKey("auth_token")
        private val KEY_USER_ID = stringPreferencesKey("user_id")
        private val KEY_NOTIFICATIONS_ENABLED = booleanPreferencesKey("notifications_enabled")
        private val KEY_VIBRATION_ENABLED = booleanPreferencesKey("vibration_enabled")
        private val KEY_AUTO_RECONNECT = booleanPreferencesKey("auto_reconnect")
    }
    
    val configFlow: Flow<PagerConfig> = context.dataStore.data.map { prefs ->
        PagerConfig(
            gatewayUrl = prefs[KEY_GATEWAY_URL] ?: BuildConfig.GATEWAY_URL,
            authToken = prefs[KEY_AUTH_TOKEN] ?: BuildConfig.AUTH_TOKEN,
            userId = prefs[KEY_USER_ID] ?: "default",
            notificationsEnabled = prefs[KEY_NOTIFICATIONS_ENABLED] ?: true,
            vibrationEnabled = prefs[KEY_VIBRATION_ENABLED] ?: true,
            autoReconnect = prefs[KEY_AUTO_RECONNECT] ?: true
        )
    }
    
    suspend fun updateGatewayUrl(url: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_GATEWAY_URL] = url
        }
    }
    
    suspend fun updateAuthToken(token: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_AUTH_TOKEN] = token
        }
    }
    
    suspend fun updateUserId(userId: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_USER_ID] = userId
        }
    }
    
    suspend fun updateNotificationsEnabled(enabled: Boolean) {
        context.dataStore.edit { prefs ->
            prefs[KEY_NOTIFICATIONS_ENABLED] = enabled
        }
    }
    
    suspend fun updateVibrationEnabled(enabled: Boolean) {
        context.dataStore.edit { prefs ->
            prefs[KEY_VIBRATION_ENABLED] = enabled
        }
    }
    
    suspend fun updateAutoReconnect(enabled: Boolean) {
        context.dataStore.edit { prefs ->
            prefs[KEY_AUTO_RECONNECT] = enabled
        }
    }
}
