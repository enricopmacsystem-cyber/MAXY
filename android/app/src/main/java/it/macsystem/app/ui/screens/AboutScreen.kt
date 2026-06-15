package it.macsystem.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import it.macsystem.app.AppInfo
import it.macsystem.app.BuildConfig
import it.macsystem.app.R
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacTextSecondary

@Composable
fun AboutScreen(
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    Scaffold(
        modifier = modifier,
        topBar = { MacSystemTopBar(title = "Info app", showLogo = false) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Image(
                painter = painterResource(R.drawable.logo_m),
                contentDescription = "Mac System",
                modifier = Modifier.size(width = 180.dp, height = 100.dp),
            )

            Text(
                text = "Mac System",
                style = MaterialTheme.typography.displaySmall,
                color = MacNavy,
            )

            Text(
                text = "Versione ${BuildConfig.VERSION_NAME} — ${AppInfo.BUILD_CODENAME}",
                style = MaterialTheme.typography.titleMedium,
                color = MacTextSecondary,
            )

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    InfoRow("Sviluppatore", AppInfo.DEVELOPER_NAME)
                    InfoRow("Azienda", AppInfo.ORGANIZATION_NAME)
                    InfoRow("Email", AppInfo.DEVELOPER_EMAIL)
                    InfoRow("Build", AppInfo.VERSION_LABEL)
                }
            }

            Text(
                text = "App ufficiale per catalogo, ordini, assistenza tecnica, punti vendita e ritiro merci H24.",
                style = MaterialTheme.typography.bodyMedium,
                color = MacTextSecondary,
                textAlign = TextAlign.Center,
            )

            TextButton(
                onClick = {
                    val intent = Intent(
                        Intent.ACTION_SENDTO,
                        Uri.parse("mailto:${AppInfo.DEVELOPER_EMAIL}"),
                    )
                    context.startActivity(Intent.createChooser(intent, "Contatta sviluppatore"))
                },
            ) {
                Text("Contatta lo sviluppatore")
            }

            Spacer(modifier = Modifier.height(8.dp))
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Column {
        Text(text = label, style = MaterialTheme.typography.labelLarge, color = MacTextSecondary)
        Text(text = value, style = MaterialTheme.typography.bodyLarge, color = MacNavy)
    }
}
