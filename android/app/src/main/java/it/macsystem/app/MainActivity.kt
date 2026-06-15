package it.macsystem.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.remember
import androidx.core.view.WindowCompat
import it.macsystem.app.ui.navigation.MacSystemAppRoot
import it.macsystem.app.ui.screens.WebViewMissingScreen
import it.macsystem.app.ui.theme.MacSystemTheme
import it.macsystem.app.web.WebViewInitializer

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = false

        setContent {
            MacSystemTheme {
                val webViewAvailable = remember {
                    WebViewInitializer.isWebViewAvailable(application)
                }
                if (webViewAvailable) {
                    MacSystemAppRoot()
                } else {
                    WebViewMissingScreen()
                }
            }
        }
    }
}
