package it.macsystem.app.ui.screens

import android.webkit.WebView
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.web.MacSystemWebView

@Composable
fun WebScreen(
    title: String,
    url: String,
    showBack: Boolean,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var webView by remember { mutableStateOf<WebView?>(null) }
    var canGoBack by remember { mutableStateOf(false) }
    var pageTitle by remember(title) { mutableStateOf(title) }

    Scaffold(
        modifier = modifier,
        topBar = {
            MacSystemTopBar(
                title = pageTitle.ifBlank { title },
                showBack = showBack,
                onBack = {
                    if (canGoBack) {
                        webView?.goBack()
                    } else {
                        onBack()
                    }
                },
            )
        },
    ) { padding ->
        MacSystemWebView(
            url = url,
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            onTitleChanged = { pageTitle = it },
            onCanGoBackChanged = { canGoBack = it },
            webViewHolder = { webView = it },
        )
    }
}
