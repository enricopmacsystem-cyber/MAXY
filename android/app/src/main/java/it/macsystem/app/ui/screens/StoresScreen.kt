package it.macsystem.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import it.macsystem.app.data.StoreLocation
import it.macsystem.app.data.StoreRepository
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.ui.theme.MacBlue
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacSuccess
import it.macsystem.app.ui.theme.MacTextSecondary

@Composable
fun StoresScreen(
    onOpenWebContacts: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    Scaffold(
        modifier = modifier,
        topBar = { MacSystemTopBar(title = "Punti vendita", showLogo = false) },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Text(
                    text = "Sette sedi nel Triveneto e in Emilia Romagna, sempre vicini ai nostri partner.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MacTextSecondary,
                    modifier = Modifier.padding(bottom = 4.dp),
                )
                AssistChip(
                    onClick = onOpenWebContacts,
                    label = { Text("Apri pagina contatti sul sito") },
                    leadingIcon = {
                        Icon(Icons.Default.OpenInNew, contentDescription = null)
                    },
                )
            }

            items(StoreRepository.stores) { store ->
                StoreCard(
                    store = store,
                    onOpenMap = {
                        val query = Uri.encode("${store.address}, ${store.city} (${store.province})")
                        val intent = Intent(
                            Intent.ACTION_VIEW,
                            Uri.parse("https://www.google.com/maps/search/?api=1&query=$query"),
                        )
                        context.startActivity(intent)
                    },
                    onCall = { phone ->
                        val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone"))
                        context.startActivity(intent)
                    },
                )
            }

            item {
                Text(
                    text = "Assistenza telefonica: 8:00–12:00 e 14:00–18:00. Per il PIN ritiro H24 invia il numero ordine tramite Assistenza o la pagina Ritiro merci.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MacTextSecondary,
                    modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
                )
            }
        }
    }
}

@Composable
private fun StoreCard(
    store: StoreLocation,
    onOpenMap: () -> Unit,
    onCall: (String) -> Unit,
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "${store.city} (${store.province})",
                    style = MaterialTheme.typography.titleMedium,
                    color = MacNavy,
                )
                store.badge?.let {
                    Text(
                        text = it,
                        style = MaterialTheme.typography.labelLarge,
                        color = MacSuccess,
                    )
                }
            }

            Text(text = store.address, style = MaterialTheme.typography.bodyLarge)
            Text(
                text = store.hours,
                style = MaterialTheme.typography.bodyMedium,
                color = MacTextSecondary,
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AssistChip(
                    onClick = onOpenMap,
                    label = { Text("Mappa") },
                    leadingIcon = { Icon(Icons.Default.Map, contentDescription = null) },
                )
                store.phone?.let { phone ->
                    AssistChip(
                        onClick = { onCall(phone.replace(" ", "")) },
                        label = { Text(phone) },
                        leadingIcon = { Icon(Icons.Default.Call, contentDescription = null) },
                    )
                }
            }
        }
    }
}
