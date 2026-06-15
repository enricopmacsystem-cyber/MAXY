Usa la skill maxy-code-review.

Contesto: review automatica su push/PR nel monorepo MAXY (Maxy AI v2.0 daisy).

## Scope

Analizza il diff del trigger (ultimo push o PR):
- `app/`
- `desktop/mac_ai_assistant/`
- `scripts/` (incluso `scripts/pipeline/`)

## Cosa verificare

1. Correttezza e regressioni (modalita commercial vs technical).
2. Allineamento API: schema Pydantic, HubClient, UI Qt.
3. Threading Qt: nessuna chiamata HTTP bloccante sul main thread.
4. Timeout client per modalita technical (fino a 300s).
5. Convenzioni progetto e messaggi errore in italiano.

## Output (formato skill)

- **Critici** - bug, crash, perdita dati
- **Importanti** - manutenibilita, incoerenze API
- **Suggerimenti** - stile, refactor opzionale
- **Verdetto** - OK / OK con fix minori / FAIL

## Regole

- **Solo report**, nessuna modifica ai file.
- Se ci sono Critici, elenca fix minimi prima di merge/release.
- Se il diff e vuoto o solo documentazione, rispondi "Nessuna review codice necessaria".
