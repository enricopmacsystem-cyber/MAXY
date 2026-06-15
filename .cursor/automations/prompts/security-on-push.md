Usa la skill maxy-security.

Contesto: security audit automatico su push/PR nel monorepo MAXY.

## Scope

Analizza il diff del trigger (ultimo push o PR):
- `app/api/`
- `app/services/`
- `app/integrations/`
- `app/core/security.py`, `app/core/permissions.py`
- `desktop/mac_ai_assistant/api/`
- `desktop/mac_ai_assistant/credentials.py`

## Cosa verificare

1. Auth JWT e gestione sessioni.
2. Segreti mai in repo (`hub.env`, `.env`, chiavi Anthropic/Gemini).
3. Hub bind su `127.0.0.1` e CORS.
4. SQL parametrizzato (SQLAlchemy).
5. Path traversal su PDF da share UNC `\\172.17.17.11\`.
6. OAuth mail (redirect URI, token storage).
7. Installer e script PowerShell in `desktop/installer/`.

## Output (formato skill)

- **Riepilogo rischio** (basso/medio/alto)
- **Critici** - vulnerabilita exploitabili
- **Medi** - hardening consigliato
- **Raccomandazioni** - azioni prioritarie
- **Verdetto** - OK / OK con fix minori / FAIL

## Regole

- **Solo report**, nessuna modifica ai file.
- Segnala solo issue reali per questo progetto (desktop + hub locale).
- Non inventare vulnerabilita su codice non presente nel diff.
