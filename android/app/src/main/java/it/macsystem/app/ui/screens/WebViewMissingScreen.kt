package it.macsystem.app.ui.screens

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacTextSecondary

@Composable
fun WebViewMissingScreen(
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text(
            text = "Android System WebView richiesto",
            style = MaterialTheme.typography.titleLarge,
            color = MacNavy,
            textAlign = TextAlign.Center,
        )
        Text(
            text = "Per usare catalogo e login serve Android System WebView aggiornato. " +
                "Apri il Play Store, cerca \"Android System WebView\" e aggiornalo. " +
                "Non disinstallarlo: aggiornalo e riapri Mac System.",
            style = MaterialTheme.typography.bodyLarge,
            color = MacTextSecondary,
            textAlign = TextAlign.Center,
        )
        Button(
            onClick = {
                runCatching {
                    context.startActivity(
                        Intent(
                            Intent.ACTION_VIEW,
                            Uri.parse("market://details?id=com.google.android.webview"),
                        ),
                    )
                }.onFailure {
                    context.startActivity(
                        Intent(
                            Intent.ACTION_VIEW,
                            Uri.parse(
                                "https://play.google.com/store/apps/details?id=com.google.android.webview",
                            ),
                        ),
                    )
                }
            },
        ) {
            Text("Apri Play Store")
        }
        Button(
            onClick = {
                context.startActivity(Intent(Settings.ACTION_APPLICATION_SETTINGS))
            },
        ) {
            Text("Impostazioni app")
        }
    }
}
