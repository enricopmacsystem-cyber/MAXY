---
name: maxy-pipeline
description: >-
  Orchestrates the standard Maxy AI production pipeline: preflight, parallel
  code-review and security gates, fix cycle, and release build. Use when
  preparing a release, running production procedure, or user mentions pipeline,
  automatismi, or standard di produzione.
disable-model-invocation: true
---

# Maxy — Pipeline di produzione

## Procedura standard

```
implement → (parallelo) code-review + security → fix → release
```

## Fase 1 — Implementazione

Usa skill `maxy-implement`. Alla fine: diff focalizzato, niente segreti nel repo.

## Fase 2 — Gate automatici

```powershell
cd c:\MAXY
python scripts/run_production_pipeline.py --phase preflight,security
```

Blocca su errori (compile, segreti, hub.spec).

## Fase 3 — Review + Security (parallelo)

```powershell
python scripts/run_production_pipeline.py --phase review
```

Apri in **due chat Cursor parallele**:
- `dist/pipeline-reports/agent_prompt_review.md` → skill `maxy-code-review`
- `dist/pipeline-reports/agent_prompt_security.md` → skill `maxy-security`

Verdetto richiesto: **OK** o **OK con fix minori** su entrambi.

## Fase 4 — Fix

Se Critici: skill `maxy-implement`, poi ripeti fase 2–3.

## Fase 5 — Release

```powershell
$env:CURSOR_PIPELINE_REVIEW_OK = "1"
python scripts/run_production_pipeline.py --phase release --require-agent-approval
```

Oppure tutto in un comando (dopo approval):

```powershell
.\scripts\run_production_pipeline.ps1 -RequireAgentApproval
```

Output: `dist/installer/Maxy 2.0 - daisy.exe`, report in `dist/pipeline-reports/`.

## Automazioni Cursor

Vedi `.cursor/automations/` — import da cursor.com/automations o chiedi prefill URL.

## Escalation

- Build Hub fallisce pydoc → `mac_ai_hub.spec` hiddenimports
- Installer senza ISCC → installare Inno Setup 6
- Review bloccata → non impostare `CURSOR_PIPELINE_REVIEW_OK`
