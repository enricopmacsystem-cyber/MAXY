package it.macsystem.app.web

import android.net.Uri
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

object MacSystemUrls {
    const val BASE = "https://www.macsystem.it"
    const val HOME = "$BASE/homepage"
    const val CATALOG = "$BASE/catalogo"
    const val BRANDS = "$BASE/marchi"
    const val LOGIN = "$BASE/login"
    const val SEARCH = "$BASE/ricerca"
    const val PICKUP_H24 = "$BASE/ritiro-merce-h24"
    const val STORES = "$BASE/punti-vendita-e-contatti"
    const val SUPPORT_EMAIL = "tecnici@macsystem.it"

    fun search(query: String): String {
        val encoded = URLEncoder.encode(query.trim(), StandardCharsets.UTF_8.toString())
        return "$SEARCH?keyword=$encoded"
    }

    fun isMacSystemHost(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val host = runCatching { Uri.parse(url).host?.lowercase() }.getOrNull() ?: return false
        return host == "www.macsystem.it" || host == "macsystem.it"
    }

}
