package it.macsystem.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import it.macsystem.app.data.ChatMessage
import it.macsystem.app.data.UserPreferences
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.ui.theme.MacBackground
import it.macsystem.app.ui.theme.MacBlue
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacSurface
import it.macsystem.app.ui.theme.MacTextSecondary
import it.macsystem.app.web.MacSystemUrls
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun SupportChatScreen(
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val preferences = remember { UserPreferences(context) }

    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var company by rememberSaveable { mutableStateOf("") }
    var draft by rememberSaveable { mutableStateOf("") }
    val messages = remember { mutableStateListOf<ChatMessage>() }

    LaunchedEffect(Unit) {
        name = preferences.contactName.first()
        email = preferences.contactEmail.first()
        company = preferences.contactCompany.first()
        if (messages.isEmpty()) {
            messages.add(
                ChatMessage(
                    id = System.currentTimeMillis(),
                    text = "Ciao! Scrivi qui la tua richiesta tecnica. Invieremo la conversazione a ${MacSystemUrls.SUPPORT_EMAIL} e ti risponderemo via email.",
                    isUser = false,
                    timestamp = System.currentTimeMillis(),
                ),
            )
        }
    }

    fun sendEmail() {
        val trimmed = draft.trim()
        if (trimmed.isBlank()) return
        if (name.isBlank() || email.isBlank()) return

        scope.launch {
            preferences.saveContact(name, email, company)
        }

        val now = System.currentTimeMillis()
        messages.add(ChatMessage(id = now, text = trimmed, isUser = true, timestamp = now))

        val history = buildString {
            appendLine("Richiesta assistenza tecnica Mac System")
            appendLine("Nome: $name")
            appendLine("Email: $email")
            if (company.isNotBlank()) appendLine("Azienda: $company")
            appendLine()
            messages.filter { it.isUser }.forEach { message ->
                appendLine("- ${message.text}")
            }
        }

        val subject = Uri.encode("Assistenza tecnica Mac System — $name")
        val body = Uri.encode(history)
        val mailto = "mailto:${MacSystemUrls.SUPPORT_EMAIL}?subject=$subject&body=$body"
        val intent = Intent(Intent.ACTION_SENDTO, Uri.parse(mailto))
        context.startActivity(Intent.createChooser(intent, "Invia richiesta assistenza"))

        messages.add(
            ChatMessage(
                id = now + 1,
                text = "Richiesta inviata. Controlla la tua casella email: i tecnici risponderanno da ${MacSystemUrls.SUPPORT_EMAIL}.",
                isUser = false,
                timestamp = System.currentTimeMillis(),
            ),
        )
        draft = ""
    }

    Scaffold(
        modifier = modifier.imePadding(),
        topBar = { MacSystemTopBar(title = "Assistenza tecnica", showLogo = false) },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MacSurface)
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        modifier = Modifier.weight(1f),
                        label = { Text("Nome") },
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it },
                        modifier = Modifier.weight(1f),
                        label = { Text("Email") },
                        singleLine = true,
                    )
                }
                OutlinedTextField(
                    value = company,
                    onValueChange = { company = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Azienda (opzionale)") },
                    singleLine = true,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedTextField(
                        value = draft,
                        onValueChange = { draft = it },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Scrivi il messaggio...") },
                        minLines = 1,
                        maxLines = 4,
                    )
                    IconButton(
                        onClick = { sendEmail() },
                        enabled = draft.isNotBlank() && name.isNotBlank() && email.isNotBlank(),
                    ) {
                        Icon(
                            Icons.AutoMirrored.Filled.Send,
                            contentDescription = "Invia",
                            tint = MacBlue,
                        )
                    }
                }
                Button(
                    onClick = { sendEmail() },
                    enabled = draft.isNotBlank() && name.isNotBlank() && email.isNotBlank(),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Invia a ${MacSystemUrls.SUPPORT_EMAIL}")
                }
            }
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MacBackground)
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                Text(
                    text = "Orari assistenza telefonica: 8:00–12:00 e 14:00–18:00. Per richieste tecniche scritte usa la chat qui sotto.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MacTextSecondary,
                )
            }

            items(messages, key = { it.id }) { message ->
                ChatBubble(message = message)
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessage) {
    val alignment = if (message.isUser) Alignment.CenterEnd else Alignment.CenterStart
    val bg = if (message.isUser) MacBlue else MacSurface
    val textColor = if (message.isUser) MacSurface else MacNavy
    val time = remember(message.timestamp) {
        SimpleDateFormat("HH:mm", Locale.ITALY).format(Date(message.timestamp))
    }

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = alignment) {
        Card(
            colors = CardDefaults.cardColors(containerColor = bg),
            shape = RoundedCornerShape(
                topStart = 16.dp,
                topEnd = 16.dp,
                bottomStart = if (message.isUser) 16.dp else 4.dp,
                bottomEnd = if (message.isUser) 4.dp else 16.dp,
            ),
            modifier = Modifier.fillMaxWidth(0.88f),
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Text(text = message.text, color = textColor)
                Text(
                    text = time,
                    style = MaterialTheme.typography.labelLarge,
                    color = textColor.copy(alpha = 0.7f),
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}
