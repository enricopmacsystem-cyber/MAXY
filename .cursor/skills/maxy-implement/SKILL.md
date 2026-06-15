---
name: maxy-implement
description: >-
  Implements features and fixes for Maxy AI (FastAPI Hub + PySide6 desktop).
  Use when building new functionality, fixing bugs, or refactoring MAXY code.
  Covers app/, desktop/, scripts/, technical/commercial assistant modes.
disable-model-invocation: true
---

# Maxy — Implementazione

## Scope

- `app/` — Hub FastAPI, servizi, integrazioni (EasyOne, Gemini, macsystem_bot)
- `desktop/mac_ai_assistant/` — UI PySide6, HubClient, hub_launcher
- `scripts/` — build, init_db, run_hub (dev)

## Principi

1. **Diff minimo** — solo ciò che serve alla richiesta
2. **Convenzioni esistenti** — stile, naming, logging come il file circostante
3. **Non toccare** segreti in repo (`hub.env`, `.env`, chiavi)
4. **Desktop + Hub** — se cambi API (`app/api/`), aggiorna `hub_client.py` se serve
5. **Modalità tecnica** — logica bot in `app/integrations/macsystem_bot/`; preferire patch in `adapter.py` vs `bot_engine.py` salvo bug nel motore

## Checklist pre-consegna

- [ ] Import e tipi coerenti
- [ ] Nessun segreto hardcoded
- [ ] UI: non bloccare il main thread Qt (usare QThread per HTTP lunghe)
- [ ] Timeout adeguati: tecnico 300s, commerciale 90s in `hub_client.py`
- [ ] Se tocchi build: `mac_ai_hub.spec` hiddenimports per nuove dipendenze Hub

## Test rapido dev

```powershell
python c:\MAXY\scripts\run_hub.py
python c:\MAXY\scripts\run_desktop.py
```

Health: `GET http://127.0.0.1:8000/api/health` → `technical_ai_configured`, `database`

## Output atteso

Breve riepilogo: cosa è cambiato, perché, file toccati, come testare.
