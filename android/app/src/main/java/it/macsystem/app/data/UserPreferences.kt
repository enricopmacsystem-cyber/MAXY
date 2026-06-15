package it.macsystem.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "macsystem_user")

class UserPreferences(private val context: Context) {
    private val nameKey = stringPreferencesKey("contact_name")
    private val emailKey = stringPreferencesKey("contact_email")
    private val companyKey = stringPreferencesKey("contact_company")

    val contactName: Flow<String> = context.dataStore.data.map { it[nameKey].orEmpty() }
    val contactEmail: Flow<String> = context.dataStore.data.map { it[emailKey].orEmpty() }
    val contactCompany: Flow<String> = context.dataStore.data.map { it[companyKey].orEmpty() }

    suspend fun saveContact(name: String, email: String, company: String) {
        context.dataStore.edit { prefs ->
            prefs[nameKey] = name.trim()
            prefs[emailKey] = email.trim()
            prefs[companyKey] = company.trim()
        }
    }
}
