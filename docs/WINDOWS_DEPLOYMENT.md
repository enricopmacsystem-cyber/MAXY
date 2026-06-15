# MAC AI Assistant — Distribuzione Windows Professionale

Guida completa per Senior Windows Software Engineer / Release Manager.

---

## 1. Architettura distribuzione

```
┌─────────────────────────────────────────────────────────────┐
│  POSTO DI LAVORO WINDOWS 10/11 (cliente)                  │
│                                                             │
│  MAC_AI_Assistant_Setup.exe  ──install──►  Program Files    │
│                                            MAC AI Assistant │
│                                              ├─ MAC_AI_Assistant.exe
│                                              └─ _internal\  (runtime Python+Qt)
│                                                             │
│  %APPDATA%\MAC AI Assistant\                                │
│    ├─ config.ini          (URL Hub, preferenze)             │
│    ├─ logs\               (crash log)                       │
│    └─ cache\                                              │
└─────────────────────────────────────────────────────────────┘
                              │ HTTPS/HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SERVER AZIENDALE (Integration Hub)                         │
│  FastAPI + PostgreSQL + Qdrant + OpenAI                     │
│  (NON incluso nel Setup client — deploy separato)           │
└─────────────────────────────────────────────────────────────┘
```

**Nota:** PostgreSQL, Qdrant e OpenAI **non** vengono installati sul PC utente.  
Il Setup.exe installa solo il **client desktop** autocontenuto (runtime Python embedded via PyInstaller).

---

## 2. Struttura directory progetto (build)

```
tech-distributor-assistant/
├── desktop/
│   ├── version.json                 # Versione singola fonte di verità
│   ├── generate_version_info.py     # Metadati exe Windows
│   ├── mac_ai_assistant.spec        # PyInstaller onedir
│   ├── requirements.txt             # Dipendenze build desktop
│   ├── hooks/
│   │   ├── hook-PySide6.py
│   │   └── runtime_mac_ai.py
│   ├── resources/
│   │   ├── app.ico                  # Icona (generata o brand)
│   │   └── generate_app_icon.py
│   ├── mac_ai_assistant/            # Sorgente client PySide6
│   ├── installer/
│   │   ├── setup.iss                # Inno Setup professionale
│   │   ├── version.iss              # Generato da build
│   │   ├── config.default.ini
│   │   └── redist/
│   │       └── VC_redist.x64.exe    # Opzionale — VC++ runtime
│   ├── build/                       # Temp PyInstaller (gitignore)
│   └── dist/
│       └── MAC_AI_Assistant/        # Output PyInstaller
│           ├── MAC_AI_Assistant.exe
│           └── _internal/
├── dist/
│   ├── installer/
│   │   └── MAC_AI_Assistant_Setup.exe   # OUTPUT FINALE
│   └── release/
│       ├── manifest.json
│       └── manifest_1.0.0_b1.json
└── scripts/
    ├── build_release.py
    ├── build_release.ps1
    └── publish_release.py
```

---

## 3. Prerequisiti macchina di build

| Software | Versione | Download |
|---|---|---|
| Windows | 10/11 x64 | — |
| Python | 3.12 x64 | python.org |
| Inno Setup | 6.x | https://jrsoftware.org/isdl.php |
| VC++ Redistributable | 2015-2022 x64 | https://aka.ms/vs/17/release/vc_redist.x64.exe |

### PATH richiesto

```
C:\Program Files\Python312\
C:\Program Files\Python312\Scripts\
C:\Program Files (x86)\Inno Setup 6\
```

### VC++ Redistributable (opzionale ma consigliato)

Copiare in `desktop/installer/redist/`:

```
desktop/installer/redist/VC_redist.x64.exe
```

L'installer lo propone automaticamente se mancante sul PC target.

---

## 4. Procedura di compilazione passo-passo

### Passo 1 — Clonare e preparare ambiente

```powershell
cd C:\Projects\tech-distributor-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r desktop\requirements.txt
```

### Passo 2 — Aggiornare versione (ogni release)

Modificare `desktop/version.json`:

```json
{
  "version": "1.0.1",
  "build": 2
}
```

Incrementare sempre `build` per ogni compilazione.

### Passo 3 — Build completa

```powershell
python scripts\build_release.py --clean
```

Oppure via PowerShell:

```powershell
.\scripts\build_release.ps1 -Clean
```

### Passo 4 — Verificare output

| Artefatto | Percorso |
|---|---|
| Applicazione portable | `desktop\dist\MAC_AI_Assistant\MAC_AI_Assistant.exe` |
| Cartella dist | `desktop\dist\MAC_AI_Assistant\_internal\` |
| **Installer finale** | `dist\installer\MAC_AI_Assistant_Setup.exe` |
| Manifest release | `dist\release\manifest.json` |
| SHA256 | nel manifest JSON |

### Passo 5 — Test locale installer

```powershell
dist\installer\MAC_AI_Assistant_Setup.exe
```

Verificare:
- [x] Wizard installazione in italiano
- [x] Pagina configurazione URL Hub
- [x] Icona Desktop creata
- [x] Voce Menu Start creata
- [x] Avvio applicazione post-install
- [x] Wizard configurazione iniziale app
- [x] Disinstallazione da Impostazioni Windows

### Passo 6 — Pubblicazione aggiornamenti

```powershell
python scripts\publish_release.py --output \\server\updates\mac-ai-assistant
```

---

## 5. Cosa fa l'installer (Inno Setup)

| Funzione | Implementazione |
|---|---|
| Installazione guidata | Wizard moderno italiano/inglese |
| Cartella applicazione | `{autopf}\MAC AI Assistant` |
| Icona Desktop | Task `desktopicon` (selezionato di default) |
| Menu Start | Gruppo `MAC AI Assistant` + disinstalla |
| Configurazione Hub | Pagina custom URL Integration Hub |
| Cartella dati | `%APPDATA%\MAC AI Assistant\` |
| Log | `%APPDATA%\MAC AI Assistant\logs\` |
| Prerequisiti VC++ | Installazione silenziosa se `redist\` presente |
| Disinstallazione | Pannello di controllo / Impostazioni Windows |
| Aggiornamenti | Stesso `AppId` — `UsePreviousAppDir=yes` |
| Preserva config | `config.ini` non sovrascritto su upgrade |

---

## 6. PyInstaller — dettagli tecnici

| Opzione | Valore | Motivo |
|---|---|---|
| Modalità | `onedir` | Affidabilità PySide6, aggiornamenti parziali |
| Console | `False` | Applicazione GUI |
| UPX | `True` | Riduzione dimensioni |
| Icona | `resources/app.ico` | Brand + shortcut Windows |
| Version info | `version_info.txt` | Proprietà file exe |
| Excludes | numpy, pandas, tkinter | Riduzione bundle |

### Solo PyInstaller (senza installer)

```powershell
python scripts\build_release.py --skip-installer --clean
```

---

## 7. Procedura aggiornamento (release N → N+1)

1. Incrementare `version` e `build` in `desktop/version.json`
2. Aggiornare `CHANGELOG` / note release
3. `python scripts\build_release.py --clean`
4. Test UAT su Windows 10 e Windows 11
5. Firma digitale Setup.exe (certificato code signing — vedi §8)
6. `python scripts\publish_release.py`
7. Eseguire SQL su hub PostgreSQL (`app_releases`)
8. Gli utenti: verifica aggiornamento da menu app o reinstallazione Setup

L'installer con stesso `AppId` aggiorna in-place preservando `config.ini`.

---

## 8. Firma digitale (produzione)

```powershell
signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 `
  dist\installer\MAC_AI_Assistant_Setup.exe
```

Richiede certificato code signing (EV consigliato per SmartScreen).

---

## 9. Risoluzione problemi build

| Problema | Soluzione |
|---|---|
| `ISCC non trovato` | Installare Inno Setup 6, aggiungere al PATH |
| `PyInstaller ModuleNotFoundError` | `pip install -r desktop/requirements.txt` |
| App non si avvia — DLL mancante | Includere VC_redist in `installer/redist/` |
| Icona mancante | `python desktop/resources/generate_app_icon.py` |
| Qt platform plugin error | Verificare hook PySide6 e cartella `_internal` completa |
| Setup troppo grande (~150MB) | Normale per PySide6 embedded |

---

## 10. Comandi rapidi

```powershell
# Build completa
python scripts\build_release.py --clean

# Solo exe + dist (no installer)
python scripts\build_release.py --clean --skip-installer

# Pubblica release
python scripts\publish_release.py

# Genera solo metadati versione
python desktop\generate_version_info.py
python desktop\resources\generate_app_icon.py
```

---

## 11. Requisiti sistema target (PC utente)

| Requisito | Dettaglio |
|---|---|
| OS | Windows 10 22H2+ / Windows 11 x64 |
| RAM | 4 GB minimo, 8 GB consigliato |
| Disco | 500 MB liberi |
| Rete | Accesso Integration Hub aziendale |
| Runtime | VC++ 2015-2022 (installato dall'installer se configurato) |
| Admin | Non richiesto (`PrivilegesRequired=lowest`) |

---

*MAC AI Assistant — Windows Deployment Guide v1.0*
