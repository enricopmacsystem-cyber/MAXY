package it.macsystem.app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Store
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import it.macsystem.app.R
import it.macsystem.app.ui.theme.MacBlue
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacTextSecondary
import it.macsystem.app.ui.theme.MacSurface

private data class QuickAction(
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
    val route: String,
)

@Composable
fun HomeScreen(
    onNavigate: (String) -> Unit,
    onSearch: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var query by rememberSaveable { mutableStateOf("") }

    val actions = listOf(
        QuickAction("Catalogo", "Sfoglia e acquista", Icons.Default.Inventory2, "catalog"),
        QuickAction("Marchi", "Tutti i produttori", Icons.Default.Verified, "brands"),
        QuickAction("Ritiro H24", "Codici zona ritiro", Icons.Default.LocalShipping, "pickup"),
        QuickAction("Assistenza", "Chat tecnica", Icons.Default.SupportAgent, "support"),
        QuickAction("Punti vendita", "Sedi e contatti", Icons.Default.Store, "stores"),
    )

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Image(
            painter = painterResource(R.drawable.logo_m),
            contentDescription = "Mac System",
            modifier = Modifier.size(width = 180.dp, height = 100.dp),
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Il tuo partner per l'elettronica",
            style = MaterialTheme.typography.bodyMedium,
            color = MacTextSecondary,
        )

        Spacer(modifier = Modifier.height(20.dp))

        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Cerca prodotto per parola chiave") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            singleLine = true,
            shape = RoundedCornerShape(14.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MacBlue,
                unfocusedBorderColor = MacTextSecondary.copy(alpha = 0.35f),
            ),
        )

        Spacer(modifier = Modifier.height(12.dp))

        Card(
            onClick = {
                if (query.isNotBlank()) onSearch(query.trim())
            },
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MacNavy),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = "Cerca nel catalogo",
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 14.dp),
                style = MaterialTheme.typography.labelLarge.copy(
                    color = MacSurface,
                    fontWeight = FontWeight.SemiBold,
                ),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            contentPadding = PaddingValues(bottom = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxSize(),
        ) {
            items(actions) { action ->
                Card(
                    onClick = { onNavigate(action.route) },
                    colors = CardDefaults.cardColors(containerColor = MacSurface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                    shape = RoundedCornerShape(16.dp),
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Icon(
                            imageVector = action.icon,
                            contentDescription = null,
                            tint = MacBlue,
                        )
                        Text(
                            text = action.title,
                            style = MaterialTheme.typography.titleMedium,
                            color = MacNavy,
                        )
                        Text(
                            text = action.subtitle,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MacTextSecondary,
                        )
                    }
                }
            }
        }
    }
}
