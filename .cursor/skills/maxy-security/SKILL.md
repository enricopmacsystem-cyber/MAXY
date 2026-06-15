---
name: maxy-security
description: >-
  Security audit for Maxy AI: auth, secrets, API exposure, PostgreSQL, OAuth,
  Anthropic/Gemini keys, UNC paths, and desktop Hub communication.
  Use when reviewing security, before release, or when user mentions sicurezza.
disable-model-invocation: true
---

# Maxy — Security audit

## Superfici da controllare

| Area | Path / nota |
|------|-------------|
| Auth JWT | `app/api/routes/auth.py`, `app/services/auth_service.py` |
| API esposte | `app/api/routes/*`, middleware audit |
| Segreti | `%APPDATA%\MAC AI Assistant\hub.env` — mai in git |
| DB | `DATABASE_URL`, SQL injection (SQLAlchemy parametrizzato) |
| OAuth mail | redirect URI, token storage |
| Hub locale | bind `127.0.0.1`, CORS in `app/main.py` |
| Desktop | credenziali salvate, refresh token |
| Bot tecnico | `ANTHROPIC_KEY`, path UNC `\\172.17.17.11\` |
| Installer | privilegi, script PowerShell in `desktop/installer/` |

## Checklist

- [ ] Nessuna API key in sorgente o commit
- [ ] Endpoint sensibili protetti da auth quando `AUTH_REQUIRED=true`
- [ ] Input utente sanitizzato (chat, search, upload path)
- [ ] `path_manuale_sicuro` / traversal su PDF e share
- [ ] Log senza password/token/chunk PII eccessivi
- [ ] Dipendenze note (requirements.txt) senza versioni pin critiche assenti su fix CVE

## Output

```markdown
## Riepilogo rischio
[Livello: basso / medio / alto]

## Trovati
### Critici
- [file:line] descrizione + remediation

### Medi
- ...

### Informativi
- ...

## Raccomandazioni release
- ...
```

## Non allarmare per

- Hub solo localhost in installazione desktop standard
- ChromaDB locale read-only su path configurato (rischio = accesso file system utente)
