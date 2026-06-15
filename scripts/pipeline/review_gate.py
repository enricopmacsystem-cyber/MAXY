from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.pipeline.config import PROJECT_ROOT, REPORTS_DIR
from scripts.pipeline.report import PipelineReport

REVIEW_PROMPT = """Usa la skill maxy-code-review.

Contesto: pipeline di produzione Maxy AI (fase REVIEW).

1. Analizza le modifiche rispetto al branch base (o l'intero diff working tree).
2. Verifica: correttezza, convenzioni MAXY, regressioni commercial/technical, thread Qt.
3. Output nel formato della skill (Critici / Importanti / Suggerimenti / Verdetto).
4. Se ci sono Critici, elenca fix minimi richiesti prima del merge/release.

Scope suggerito: app/, desktop/mac_ai_assistant/, scripts/pipeline/
"""

SECURITY_PROMPT = """Usa la skill maxy-security.

Contesto: pipeline di produzione Maxy AI (fase SECURITY, in parallelo con code review).

1. Audit su app/api/, app/services/, app/integrations/, desktop/mac_ai_assistant/api/
2. Verifica: auth JWT, segreti, path traversal PDF, hub.env, SQL parametrizzato.
3. Output nel formato della skill (Riepilogo rischio / Critici / Medi / Raccomandazioni).
4. Segnala solo issue reali per questo progetto desktop+hub locale.

Non modificare file in questa fase — solo report.
"""


def _git_changed_files() -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
        lines = [ln.strip().split()[-1] for ln in proc.stdout.splitlines() if ln.strip()]
        return [ln for ln in lines if ln]
    except OSError:
        return []


def run_review_gate(report: PipelineReport, *, emit_agent_prompts: bool = True) -> None:
    report.phases.append("review")

    changed = _git_changed_files()
    if changed:
        report.add("review", "info", f"File modificati ({len(changed)}): " + ", ".join(changed[:12]))
        if len(changed) > 12:
            report.add("review", "info", f"... e altri {len(changed) - 12} file")
    else:
        report.add("review", "info", "Nessun git diff rilevato — review su tree corrente")

    critical_paths = (
        "desktop/mac_ai_assistant/ui/main_window.py",
        "desktop/mac_ai_assistant/api/hub_client.py",
        "app/integrations/macsystem_bot/adapter.py",
        "desktop/mac_ai_hub.spec",
    )
    for rel in critical_paths:
        if (PROJECT_ROOT / rel).is_file():
            report.add("review", "info", f"Path critico presente: {rel}")

    if emit_agent_prompts:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        review_path = REPORTS_DIR / "agent_prompt_review.md"
        security_path = REPORTS_DIR / "agent_prompt_security.md"
        review_path.write_text(REVIEW_PROMPT, encoding="utf-8")
        security_path.write_text(SECURITY_PROMPT, encoding="utf-8")
        report.add(
            "review",
            "info",
            f"Prompt agente code-review: {review_path}",
        )
        report.add(
            "review",
            "info",
            f"Prompt agente security (parallelo): {security_path}",
        )
        report.add(
            "review",
            "warn",
            "Gate review agenti: eseguire i due prompt in Cursor in parallelo; "
            "impostare CURSOR_PIPELINE_REVIEW_OK=1 dopo verdetto OK",
        )
