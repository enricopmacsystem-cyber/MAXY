package it.macsystem.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary = MacNavy,
    onPrimary = Color.White,
    primaryContainer = MacBlueLight.copy(alpha = 0.18f),
    onPrimaryContainer = MacNavy,
    secondary = MacBlue,
    onSecondary = Color.White,
    background = MacBackground,
    onBackground = MacTextPrimary,
    surface = MacSurface,
    onSurface = MacTextPrimary,
    surfaceVariant = MacBackground,
    onSurfaceVariant = MacTextSecondary,
    outline = MacBorder,
)

@Composable
fun MacSystemTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        typography = MacTypography,
        content = content,
    )
}
