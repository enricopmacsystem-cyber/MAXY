package it.macsystem.app

import android.app.Application
import it.macsystem.app.web.WebViewInitializer

class MacSystemApp : Application() {
    override fun onCreate() {
        super.onCreate()
        WebViewInitializer.init(this)
    }
}
