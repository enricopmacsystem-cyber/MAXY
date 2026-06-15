---
name: maxy-code-review
description: >-
  Reviews Maxy AI code for correctness, maintainability, and project conventions.
  Use for pull requests, pre-release review, or when the user asks for code review
  on app/, desktop/, or scripts/ in the MAXY monorepo.
disable-model-invocation: true
---

# Maxy — Code review

## Focus

1. **Correttezza** — edge case, error handling, race (Qt thread, asyncio in adapter)
2. **API contract** — schema Pydantic ↔ HubClient ↔ UI allineati
3. **Regressioni** — modalità commercial vs technical; hub_launcher vs run_hub dev
4. **Performance** — query ChromaDB, PDF di rete, timeout client
5. **UX desktop** — feedback caricamento, messaggi errore in italiano

## Severità feedback

- **Critico** — bug, perdita dati, crash, sicurezza
- **Importante** — manutenibilità, incoerenza API, test mancanti su path critico
- **Suggerimento** — stile, naming, refactor opzionale

## Checklist MAXY

- [ ] Modifiche proporzionate alla richiesta (no scope creep)
- [ ] Logging utile (`app.core.logging`, non print sparsi)
- [ ] Eccezioni utente comprensibili (RuntimeError con messaggio IT in hub_client)
- [ ] PyInstaller: nuovi import nel `.spec` se necessario
- [ ] `version.json` / release_notes se cambio user-facing

## Non segnalare come bug

- `hub.env` onlyifdoesntexist nell’installer (comportamento voluto)
- Prima richiesta tecnica lenta (embedding + PDF rete) se c’è messaggio attesa

## Output

```markdown
## Riepilogo
[1-2 frasi]

## Critici
- ...

## Importanti
- ...

## Suggerimenti
- ...

## Verdetto
[OK / OK con fix minori / Richiede modifiche]
```
