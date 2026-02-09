package com.stonehub.clawdpager.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.wear.compose.material3.ColorScheme
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.Typography

// Clawdbot Pager color palette - dark theme optimized for OLED
val ClawdPrimary = Color(0xFF00BCD4)        // Cyan
val ClawdSecondary = Color(0xFF03DAC6)      // Teal
val ClawdBackground = Color(0xFF000000)      // Pure black for OLED
val ClawdSurface = Color(0xFF121212)         // Dark gray
val ClawdError = Color(0xFFCF6679)           // Error red
val ClawdOnPrimary = Color(0xFF000000)       // Black text on primary
val ClawdOnSurface = Color(0xFFE1E1E1)       // Light gray text
val ClawdOnBackground = Color(0xFFFFFFFF)    // White text

// Status colors
val StatusConnected = Color(0xFF4CAF50)      // Green
val StatusConnecting = Color(0xFFFFC107)     // Amber
val StatusDisconnected = Color(0xFF9E9E9E)   // Gray
val StatusError = Color(0xFFF44336)          // Red

private val ClawdColorScheme = ColorScheme(
    primary = ClawdPrimary,
    onPrimary = ClawdOnPrimary,
    secondary = ClawdSecondary,
    onSecondary = ClawdOnPrimary,
    background = ClawdBackground,
    onBackground = ClawdOnBackground,
    surface = ClawdSurface,
    onSurface = ClawdOnSurface,
    error = ClawdError,
    onError = Color.Black
)

@Composable
fun ClawdPagerTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = ClawdColorScheme,
        typography = Typography(),
        content = content
    )
}
