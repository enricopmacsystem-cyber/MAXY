package it.macsystem.app.web

import android.app.Application
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.CookieManager
import android.webkit.WebView
import androidx.webkit.WebViewCompat

object WebViewInitializer {
    private const val TAG = "MacSystemWebView"

    fun init(application: Application) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            runCatching {
                WebView.setDataDirectorySuffix("macsystem")
            }.onFailure { error ->
                Log.w(TAG, "Impossibile impostare la directory dati WebView", error)
            }
        }

        CookieManager.getInstance().setAcceptCookie(true)

        if (!isWebViewAvailable(application)) {
            Log.e(TAG, "Android System WebView non disponibile sul dispositivo")
            return
        }

        Handler(Looper.getMainLooper()).post {
            runCatching {
                val webView = WebView(application.applicationContext)
                webView.settings.javaScriptEnabled = false
                CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)
                webView.destroy()
            }.onFailure { error ->
                Log.e(TAG, "Precaricamento WebView fallito", error)
            }
        }
    }

    fun isWebViewAvailable(application: Application): Boolean {
        return runCatching {
            val provider = WebViewCompat.getCurrentWebViewPackage(application)
            if (provider != null) {
                true
            } else {
                application.packageManager.getPackageInfo(
                    "com.google.android.webview",
                    PackageManager.GET_META_DATA,
                )
                true
            }
        }.getOrDefault(false)
    }
}
