package it.macsystem.app.data

object StoreRepository {
    val stores: List<StoreLocation> = listOf(
        StoreLocation(
            id = "mirandola",
            city = "Mirandola",
            province = "MO",
            address = "Via Santa Liberata, 118",
            hours = "8:30 - 12:30, 14:00 - 18:00 (lun-ven)",
            badge = "Nuova apertura",
        ),
        StoreLocation(
            id = "villorba",
            city = "Villorba",
            province = "TV",
            address = "Via I. Newton, 29",
            hours = "8:00 - 12:00, 14:00 - 18:00 (lun-ven)",
        ),
        StoreLocation(
            id = "gruaro",
            city = "Gruaro",
            province = "VE",
            address = "Via Della Tecnica 8",
            hours = "8:00 - 12:00, 14:00 - 18:00 (lun-ven)",
        ),
        StoreLocation(
            id = "marghera",
            city = "Marghera",
            province = "VE",
            address = "Via Monzani 12/4",
            hours = "8:00 - 12:00, 14:00 - 18:00 (lun-ven)",
        ),
        StoreLocation(
            id = "padova",
            city = "Padova",
            province = "PD",
            address = "Viale della Navigazione interna, 49/A int.2",
            hours = "8:00 - 12:00, 14:00 - 18:00 (lun-ven)",
            phone = "+39 049 748 3832",
        ),
        StoreLocation(
            id = "verona",
            city = "Verona",
            province = "VR",
            address = "Viale delle Nazioni, 15/D",
            hours = "8:00 - 12:00, 14:00 - 18:00 (lun-ven)",
            phone = "+39 045 825 0146",
        ),
        StoreLocation(
            id = "tavagnacco",
            city = "Tavagnacco",
            province = "UD",
            address = "Via Cotonificio 47",
            hours = "8:00 - 12:00, 14:00 - 18:00 (lun-ven)",
        ),
    )
}
