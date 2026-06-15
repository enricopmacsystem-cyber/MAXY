# Automazioni Cursor — Maxy AI

Bozze workflow da importare in [cursor.com/automations](https://cursor.com/automations).

## 1. Pre-release gate (manuale / cron settimanale)

**File:** `pre-release-gate.workflow.json`

Dopo implementazione, esegue preflight + security scan e genera prompt review paralleli.

## 2. MR / push — review parallela

**File:** `parallel-review.workflow.json`

Su push branch feature: lancia code-review e security su scope disgiunti (solo report).

## Import

1. Apri Cursor → Automations → Create
2. Incolla il JSON del workflow o usa il prefill URL generato da:
   ```powershell
   # L'agente può chiamare build_automation_prefill_url con il JSON
   ```
3. Collega il repository `c:\MAXY` (o remoto GitLab) come workspace

## Pipeline locale (sempre disponibile)

Non richiede Automations cloud:

```powershell
.\scripts\run_production_pipeline.ps1
```

Con gate agenti obbligatorio prima del build:

```powershell
.\scripts\run_production_pipeline.ps1 -RequireAgentApproval
```
