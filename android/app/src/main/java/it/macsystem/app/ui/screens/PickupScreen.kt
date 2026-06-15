package it.macsystem.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacTextSecondary
import it.macsystem.app.web.MacSystemUrls
import it.macsystem.app.web.MacSystemWebView

@Composable
fun PickupScreen(
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        topBar = { MacSystemTopBar(title = "Ritiro merci H24", showLogo = false) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(14.dp),
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = "Codici zona ritiro H24",
                        style = MaterialTheme.typography.titleMedium,
                        color = MacNavy,
                    )
                    Text(
                        text = "I codici per il ritiro merci nelle zone H24 vengono forniti da Mac System. " +
                            "Richiedi il PIN indicando il numero d'ordine tramite questa pagina o dall'assistenza in app.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MacTextSecondary,
                    )
                }
            }

            MacSystemWebView(
                url = MacSystemUrls.PICKUP_H24,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 8.dp),
            )
        }
    }
}
