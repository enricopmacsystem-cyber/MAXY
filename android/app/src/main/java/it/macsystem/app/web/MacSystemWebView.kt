package it.macsystem.app.web

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import it.macsystem.app.ui.theme.MacBlue
import it.macsystem.app.ui.theme.MacTextSecondary

private const val COOKIE_ACCEPT_SCRIPT = """
(function() {
  function clickAccept() {
    var buttons = document.querySelectorAll('button, a, input[type="button"], input[type="submit"]');
    for (var i = 0; i < buttons.length; i++) {
      var text = (buttons[i].innerText || buttons[i].value || '').trim().toLowerCase();
      if (text.indexOf('accetta tutto') >= 0 || text.indexOf('accetta') === 0) {
        buttons[i].click();
        return true;
      }
    }
    return false;
  }
  if (!clickAccept()) {
    setTimeout(clickAccept, 800);
  }
})();
"""

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun MacSystemWebView(
    url: String,
    modifier: Modifier = Modifier,
    onTitleChanged: (String) -> Unit = {},
    onCanGoBackChanged: (Boolean) -> Unit = {},
    webViewHolder: (WebView?) -> Unit = {},
) {
    var isLoading by remember(url) { mutableStateOf(true) }
    var loadError by remember(url) { mutableStateOf<String?>(null) }

    Box(modifier = modifier.fillMaxSize()) {
        if (loadError != null) {
            Text(
                text = loadError.orEmpty(),
                modifier = Modifier
                    .align(Alignment.Center)
                    .padding(24.dp),
                style = MaterialTheme.typography.bodyLarge,
                color = MacTextSecondary,
                textAlign = TextAlign.Center,
            )
        } else {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { context ->
                    try {
                        WebView(context).apply {
                            layoutParams = ViewGroup.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT,
                            )
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            settings.loadsImagesAutomatically = true
                            settings.useWideViewPort = true
                            settings.loadWithOverviewMode = true
                            settings.setSupportZoom(true)
                            settings.builtInZoomControls = true
                            settings.displayZoomControls = false
                            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE

                            CookieManager.getInstance().setAcceptCookie(true)
                            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)

                            webChromeClient = WebChromeClient()
                            webViewClient = object : WebViewClient() {
                                override fun onPageStarted(view: WebView?, pageUrl: String?, favicon: Bitmap?) {
                                    isLoading = true
                                }

                                override fun onPageFinished(view: WebView?, finishedUrl: String?) {
                                    isLoading = false
                                    view?.evaluateJavascript(COOKIE_ACCEPT_SCRIPT, null)
                                    onCanGoBackChanged(view?.canGoBack() == true)
                                }

                                override fun onReceivedError(
                                    view: WebView?,
                                    request: WebResourceRequest?,
                                    error: android.webkit.WebResourceError?,
                                ) {
                                    if (request?.isForMainFrame == true) {
                                        isLoading = false
                                        loadError = "Impossibile caricare la pagina. Verifica la connessione internet."
                                    }
                                }

                                override fun shouldOverrideUrlLoading(
                                    view: WebView?,
                                    request: WebResourceRequest?,
                                ): Boolean {
                                    val target = request?.url?.toString().orEmpty()
                                    return if (MacSystemUrls.isMacSystemHost(target)) {
                                        false
                                    } else {
                                        view?.context?.let { ctx ->
                                            runCatching {
                                                val intent = android.content.Intent(
                                                    android.content.Intent.ACTION_VIEW,
                                                    request?.url,
                                                )
                                                ctx.startActivity(intent)
                                            }
                                        }
                                        true
                                    }
                                }
                            }

                            webViewHolder(this)
                            loadUrl(url)
                        }
                    } catch (error: Exception) {
                        loadError = "WebView non disponibile. Aggiorna Android System WebView dal Play Store."
                        android.view.View(context)
                    }
                },
                update = { webView ->
                    if (webView is WebView) {
                        webViewHolder(webView)
                        onTitleChanged(webView.title.orEmpty())
                    }
                },
            )
        }

        if (isLoading && loadError == null) {
            CircularProgressIndicator(
                modifier = Modifier.align(Alignment.Center),
                color = MacBlue,
            )
        }
    }
}
