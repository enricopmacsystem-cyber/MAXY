Usa la skill maxy-pipeline.

Contesto: pre-release gate Maxy AI v2.0 (hub FastAPI + desktop PySide6).

## Obiettivo

Eseguire i gate automatici e coordinare la review parallela prima del build installer.

## Passi

1. Esegui nel repository:
   ```
   python scripts/run_production_pipeline.py --phase preflight,security,review
   ```
2. Leggi l'ultimo report JSON in `dist/pipeline-reports/pipeline_*.json`.
3. Se **preflight** o **security** sono FAIL:
   - Elenca i problemi in ordine di priorita.
   - Proponi fix minimi (skill maxy-implement).
   - **Non** avviare release.
4. Se **preflight** e **security** sono PASS:
   - Indica all'utente di aprire **due chat Cursor in parallelo** con:
     - `dist/pipeline-reports/agent_prompt_review.md`
     - `dist/pipeline-reports/agent_prompt_security.md`
   - Attendi verdetto **OK** o **OK con fix minori** da entrambi.
5. Solo dopo doppio OK, l'utente puo eseguire release:
   ```
   $env:CURSOR_PIPELINE_REVIEW_OK = "1"
   python scripts/run_production_pipeline.py --phase release --require-agent-approval
   ```

## Regole

- Non committare segreti (`hub.env`, `.env`, chiavi API).
- Non modificare file in questa fase salvo fix critici esplicitamente richiesti.
- Output finale: tabella PASS/FAIL per fase + prossima azione consigliata.
