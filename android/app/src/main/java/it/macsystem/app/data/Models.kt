package it.macsystem.app.data

data class StoreLocation(
    val id: String,
    val city: String,
    val province: String,
    val address: String,
    val hours: String,
    val phone: String? = null,
    val badge: String? = null,
)

data class BrandItem(
    val name: String,
    val description: String,
    val searchKeyword: String,
)

data class ChatMessage(
    val id: Long,
    val text: String,
    val isUser: Boolean,
    val timestamp: Long,
)
