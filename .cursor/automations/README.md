# Automazioni Cursor - Maxy AI

Guida per configurare le automazioni su [cursor.com/automations](https://cursor.com/automations) o nella finestra **Agents** di Cursor.

Repository GitHub: `enricopmacsystem-cyber/MAXY`

> **Nota:** Cursor **non** ha un trigger "Manual". Per esecuzione on-demand usa **Webhook** o la pipeline locale PowerShell.

---

## Trigger disponibili in Cursor (ufficiali)

| Trigger UI | Quando usarlo per MAXY |
|------------|------------------------|
| **Webhook** | Pre-release gate **on-demand** (lo lanci tu con una POST) |
| **Scheduled** | Controllo periodico (es. ogni lunedì mattina) |
| **GitHub - Push to branch** | Review automatica a ogni push su un branch (es. `main`) |
| **GitHub - Pull request opened** | Review automatica all'apertura di una PR |
| **GitHub - Pull request pushed** | Review a ogni nuovo commit su una PR esistente |
| Slack / Linear / Sentry / PagerDuty | Non necessari per il flusso MAXY base |

---

## Automazione 1 - Pre-release gate (on-demand)

**Trigger da scegliere:** `Webhook`

**Repository:** `enricopmacsystem-cyber/MAXY` (branch `main`)

**Modello consigliato:** Claude Sonnet

**Memories:** ON (opzionale)

**Prompt:** copia da [`prompts/pre-release-gate.md`](prompts/pre-release-gate.md)

### Come lanciarla manualmente

Dopo aver salvato l'automazione, Cursor mostra **Webhook URL** e **API key**. Da PowerShell:

```powershell
$headers = @{ Authorization = "Bearer <API_KEY>" }
Invoke-RestMethod -Method POST -Uri "<WEBHOOK_URL>" -Headers $headers
```

### Alternativa senza cloud agent (consigliata per uso quotidiano)

```powershell
cd c:\MAXY
.\scripts\run_production_pipeline.ps1
```

Poi apri due chat Cursor con i prompt generati in `dist/pipeline-reports/`.

---

## Automazione 2 - Code review su push/PR

**Trigger da scegliere (scegli UNO):**

| Se lavori così... | Voce menu GitHub |
|-------------------|------------------|
| Push diretto su `main` (come ora) | **Push to branch** → branch `main` |
| Flusso con Pull Request | **Pull request opened** |
| Vuoi rivedere ogni commit aggiunto a una PR | **Pull request pushed** |

**Repository:** `enricopmacsystem-cyber/MAXY`

**Modello consigliato:** Claude Sonnet (thinking se disponibile)

**Memories:** OFF

**Prompt:** copia da [`prompts/code-review-on-push.md`](prompts/code-review-on-push.md)

**Tools utili:** Comment on pull request (se usi PR)

---

## Automazione 3 - Security audit su push/PR

Stesso trigger dell'Automazione 2 (stessa voce GitHub, stesso branch).

**Modello consigliato:** Claude Opus o Sonnet thinking

**Memories:** OFF

**Prompt:** copia da [`prompts/security-on-push.md`](prompts/security-on-push.md)

> Per review **parallela**, crea **due automazioni separate** (una code review, una security) con lo stesso trigger GitHub.

---

## Quale voce GitHub scegliere - guida rapida

### Situazione attuale (push diretto su `main`)

```
GitHub → Push to branch → Repository: enricopmacsystem-cyber/MAXY → Branch: main
```

Si attiva a ogni `git push origin main`. Adatto se non usi ancora Pull Request.

### Flusso consigliato a medio termine (con PR)

```
GitHub → Pull request opened → Repository: enricopmacsystem-cyber/MAXY
```

Si attiva solo quando apri una PR (es. `feature/xyz` → `main`). La review avviene **prima** del merge.

### Non usare questi per MAXY (salvo casi speciali)

| Voce | Perché |
|------|--------|
| **Pull request merged** | Troppo tardi: il codice è già in `main` |
| **Draft opened** | Solo per bozze PR |
| **CI completed** | Utile solo se hai GitHub Actions configurato |
| **Pull request commented** | Si attiva su commenti, non su nuovo codice |

---

## Setup passo-passo nell'UI Cursor

1. Apri **Cursor → Automations → Create** (o [cursor.com/automations/new](https://cursor.com/automations/new))
2. **Name:** es. `Maxy - Pre-release gate`
3. **Trigger:** scegli dalla tabella sopra
4. **Repository:** `enricopmacsystem-cyber/MAXY`
5. **Branch:** `main` (se richiesto dal trigger)
6. **Model:** Sonnet per orchestrazione/review; Opus per security
7. **Prompt:** incolla il testo dal file in `prompts/`
8. **Tools:** abilita solo quelli necessari (es. Comment on PR)
9. **Save** → per Webhook, copia URL e API key

### Non serve incollare `AGENTS.md`

`AGENTS.md` è documentazione per il team. Nei prompt basta citare la skill (`maxy-pipeline`, `maxy-code-review`, ecc.): Cursor la carica da `.cursor/skills/`.

---

## File di riferimento

| File | Contenuto |
|------|-----------|
| `pre-release-gate.workflow.json` | Bozza JSON (trigger webhook) |
| `parallel-review.workflow.json` | Bozza JSON (trigger GitHub push) |
| `prompts/pre-release-gate.md` | Prompt pronto pre-release |
| `prompts/code-review-on-push.md` | Prompt pronto code review |
| `prompts/security-on-push.md` | Prompt pronto security |

I file `.workflow.json` sono bozze di riferimento. L'UI Cursor potrebbe non importarli direttamente: usa i prompt in `prompts/` e configura i trigger a mano.

---

## Pipeline locale (sempre disponibile)

Non richiede Automations cloud né consumo Max Mode:

```powershell
.\scripts\run_production_pipeline.ps1
```

Solo check rapido:

```powershell
.\scripts\run_production_pipeline.ps1 -Phase preflight,security
```

Build dopo review OK:

```powershell
$env:CURSOR_PIPELINE_REVIEW_OK = "1"
.\scripts\run_production_pipeline.ps1 -Phase release -RequireAgentApproval
```

Report: `dist/pipeline-reports/`

---

## Test automazioni (push su main)

Ultimo test E2E: push su `main` per verificare trigger **Code review** e **Security audit**.
Controlla esito in Cursor Automations → Run History.

**Test #2** — dopo fix GitHub App Cursor (permessi repo salvati).
