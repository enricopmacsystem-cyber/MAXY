# Mac System — App Android

App Android per consultare il catalogo, acquistare sul sito [macsystem.it](https://www.macsystem.it), gestire il login, i marchi, i punti vendita, il ritiro H24 e l'assistenza tecnica.

## Funzionalità

- **Home** con ricerca prodotti per parola chiave
- **Catalogo** e checkout tramite sito ufficiale (sessione condivisa via cookie)
- **Login** con le credenziali già usate sul sito
- **Marchi** consultabili con apertura ricerca prodotti
- **Ritiro merci H24** con pagina dedicata e richiesta PIN
- **Punti vendita** con indirizzi, orari, telefono e mappa
- **Assistenza tecnica** in stile chat con invio email a `tecnici@macsystem.it`

## Requisiti

- Android Studio Ladybug o successivo
- JDK 17
- Android SDK 35

## Build APK

```bash
cd android
python scripts/generate_android_icons.py
gradlew.bat assembleRelease
```

APK pronto per installazione:

`dist/MacSystem-2.0.1-Dandelion.apk`

## Info build corrente

- **Versione:** 2.0.1 — Dandelion
- **Sviluppatore:** Andrea Santin
- **Azienda:** MacSystem s.r.l.
- **Email:** andrea.santin@macsystem.it

Per la release firmata:

```bash
gradlew.bat assembleRelease
```

## Installazione sul telefono

1. Copia l'APK sullo smartphone
2. Abilita **Installa app sconosciute** per il file manager usato
3. Apri l'APK e conferma l'installazione

## Note tecniche

- L'app usa una shell nativa (Jetpack Compose) e **WebView** per login, catalogo, carrello e pagamenti sul portale Liferay esistente.
- I cookie di sessione restano nel WebView: dopo il login in **Account** puoi acquistare dal **Catalogo** senza ripetere l'accesso.
- L'icona è generata da `desktop/resources/logo-m.png` per mantenere il logo nitido su tutte le densità.
