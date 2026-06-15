#!/usr/bin/env python3
"""
Pipeline di produzione standard Maxy AI.

Fasi:
  1. preflight  — compile, import app, version, hub.spec
  2. security   — scan segreti (automatico)
  3. review     — prompt per agenti Cursor (code-review + security in parallelo)
  4. release    — build_release.py + smoke test Hub

Uso:
  python scripts/run_production_pipeline.py
  python scripts/run_production_pipeline.py --phase preflight,security
  python scripts/run_production_pipeline.py --phase release --skip-build
  python scripts/run_production_pipeline.py --require-agent-approval

Dopo review/security manuali con Cursor:
  set CURSOR_PIPELINE_REVIEW_OK=1
  python scripts/run_production_pipeline.py --phase release
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pipeline.preflight import run_preflight
from scripts.pipeline.release_gate import run_release_gate
from scripts.pipeline.report import PipelineReport
from scripts.pipeline.review_gate import run_review_gate
from scripts.pipeline.security_scan import run_security_scan

ALL_PHASES = ("preflight", "security", "review", "release")


def parse_phases(raw: str | None) -> tuple[str, ...]:
    if not raw or raw.strip().lower() == "all":
        return ALL_PHASES
    names = tuple(p.strip().lower() for p in raw.split(",") if p.strip())
    unknown = set(names) - set(ALL_PHASES)
    if unknown:
        raise SystemExit(f"Fasi sconosciute: {', '.join(sorted(unknown))}")
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline produzione Maxy AI")
    parser.add_argument(
        "--phase",
        default="all",
        help="Fasi: all | preflight,security,review,release",
    )
    parser.add_argument("--skip-build", action="store_true", help="Release: solo verifica artefatti")
    parser.add_argument("--skip-installer", action="store_true", help="Release: no Inno Setup")
    parser.add_argument("--skip-deps", action="store_true", default=True, help="Release: no pip install")
    parser.add_argument(
        "--require-agent-approval",
        action="store_true",
        help="Blocca release se CURSOR_PIPELINE_REVIEW_OK non è impostato",
    )
    parser.add_argument(
        "--no-agent-prompts",
        action="store_true",
        help="Review: non generare file prompt per Cursor",
    )
    args = parser.parse_args()

    phases = parse_phases(args.phase)
    report = PipelineReport()

    print("Pipeline Maxy AI — fasi:", ", ".join(phases))

    if "preflight" in phases:
        run_preflight(report)
        if not report.passed:
            report.save()
            report.print_summary()
            return 1

    if "security" in phases:
        run_security_scan(report)
        if not report.passed:
            report.save()
            report.print_summary()
            return 1

    if "review" in phases:
        run_review_gate(report, emit_agent_prompts=not args.no_agent_prompts)

    if "release" in phases:
        if args.require_agent_approval and not os.getenv("CURSOR_PIPELINE_REVIEW_OK"):
            report.add(
                "release",
                "error",
                "Review agenti non approvata. Eseguire prompt in "
                "dist/pipeline-reports/agent_prompt_*.md poi: "
                "set CURSOR_PIPELINE_REVIEW_OK=1",
            )
            report.save()
            report.print_summary()
            return 1
        run_release_gate(
            report,
            skip_build=args.skip_build,
            skip_installer=args.skip_installer,
            skip_deps=args.skip_deps,
        )

    report_path = report.save()
    report.print_summary()
    print(f"\nReport JSON: {report_path}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
