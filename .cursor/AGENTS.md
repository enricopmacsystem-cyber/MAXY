# Agenti MAXY — come lavorare in team (AI)

Questo progetto supporta **ruoli specializzati** tramite Skill in `.cursor/skills/`.
Ogni skill istruisce l’agente su obiettivo, vincoli e formato dell’output.

## Ruoli disponibili

| Ruolo | Skill | Quando usarlo |
|-------|-------|----------------|
| **Implementazione** | `maxy-implement` | Nuove feature, bug fix, refactor mirati |
| **Code review** | `maxy-code-review` | Prima di merge/build; qualità e convenzioni |
| **Sicurezza** | `maxy-security` | Auth, segreti, API, dati clienti, supply chain |
| **Build & release** | `maxy-release` | PyInstaller, installer, version bump |
| **Pipeline completa** | `maxy-pipeline` | Procedura standard implement → review → release |

## Pipeline di produzione (standard)

```powershell
# Gate automatici + prompt agenti
.\scripts\run_production_pipeline.ps1

# Solo check rapido
python scripts/run_production_pipeline.py --phase preflight,security

# Build dopo review OK
$env:CURSOR_PIPELINE_REVIEW_OK = "1"
.\scripts\run_production_pipeline.ps1 -Phase release -RequireAgentApproval
```

Report JSON: `dist/pipeline-reports/`  
Prompt paralleli: `agent_prompt_review.md` + `agent_prompt_security.md`  
Automazioni Cursor: `.cursor/automations/` (vedi README)

### Flusso

1. **implement** (`maxy-implement`)
2. **preflight + security** (script automatico)
3. **review ∥ security** (due chat Cursor con i prompt generati)
4. **fix** se necessario
5. **release** (`maxy-release` / script con `CURSOR_PIPELINE_REVIEW_OK=1`)

## Come invocare un agente

In una nuova chat Cursor, scrivi ad esempio:

```
Usa la skill maxy-code-review e rivedi le modifiche in desktop/mac_ai_assistant/ui/main_window.py
```

oppure:

```
@maxy-security — audit completo su app/api e hub.env handling
```

## Lavoro in parallelo

**Sì, possono lavorare in parallelo**, con queste regole:

1. **Stesso obiettivo, aree diverse** — OK in parallelo  
   Esempio: mentre un agente fa *code review* su `desktop/`, un altro fa *security* su `app/api/`.

2. **Stessi file in scrittura** — NO in parallelo  
   Due agenti che modificano `main_window.py` o `adapter.py` nello stesso momento creano conflitti.

3. **Pipeline consigliata per feature nuove**
   ```
   implement → (in parallelo) code-review + security → fix → release
   ```

4. **Nella stessa chat** puoi chiedere esplicitamente:
   ```
   Lancia in parallelo: code review su desktop/ e security audit su app/
   ```

5. **Chat separate** — apri una Composer/chat per ruolo (Implementer, Reviewer, Security) e assegna scope disgiunti.

## Contesto progetto (tutti gli agenti)

- **Hub**: FastAPI in `app/`, exe `MAC_AI_Hub.exe`, config `%APPDATA%\MAC AI Assistant\hub.env`
- **Desktop**: PySide6 in `desktop/mac_ai_assistant/`
- **Modalità Maxy**: commerciale (Gemini) + tecnica (ChromaDB + Claude via `app/integrations/macsystem_bot/`)
- **Build**: `python scripts/build_release.py` → `dist/installer/`
- **Non committare** `hub.env`, chiavi API, `.env` con segreti

## Estendere

Aggiungi skill in `.cursor/skills/<nome>/SKILL.md` seguendo il template delle skill esistenti.
