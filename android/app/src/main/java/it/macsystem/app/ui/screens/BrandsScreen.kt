package it.macsystem.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
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
import androidx.compose.ui.unit.dp
import it.macsystem.app.data.BrandItem
import it.macsystem.app.data.BrandRepository
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.ui.theme.MacBlue
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacTextSecondary

@Composable
fun BrandsScreen(
    onBrandSelected: (BrandItem) -> Unit,
    onOpenAllBrands: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        topBar = { MacSystemTopBar(title = "Marchi", showLogo = false) },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                Text(
                    text = "Tecnologie selezionate per installatori e professionisti della sicurezza.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MacTextSecondary,
                    modifier = Modifier.padding(bottom = 4.dp),
                )
                AssistChip(
                    onClick = onOpenAllBrands,
                    label = { Text("Vedi tutti i marchi sul sito") },
                    leadingIcon = { Icon(Icons.Default.OpenInNew, contentDescription = null) },
                )
            }

            items(BrandRepository.brands) { brand ->
                Card(
                    onClick = { onBrandSelected(brand) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        androidx.compose.foundation.layout.Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(
                                text = brand.name,
                                style = MaterialTheme.typography.titleMedium,
                                color = MacNavy,
                                modifier = Modifier.weight(1f),
                            )
                            Icon(
                                imageVector = Icons.Default.ChevronRight,
                                contentDescription = null,
                                tint = MacBlue,
                            )
                        }
                        Text(
                            text = brand.description,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MacTextSecondary,
                        )
                    }
                }
            }
        }
    }
}
