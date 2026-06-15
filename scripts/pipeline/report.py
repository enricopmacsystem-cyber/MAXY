from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from scripts.pipeline.config import REPORTS_DIR


@dataclass
class Finding:
    phase: str
    severity: str  # error | warn | info
    message: str
    path: str = ""


@dataclass
class PipelineReport:
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    phases: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    passed: bool = True

    def add(self, phase: str, severity: str, message: str, path: str = "") -> None:
        self.findings.append(Finding(phase, severity, message, path))
        if severity == "error":
            self.passed = False

    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warn"]

    def save(self) -> Path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"pipeline_{stamp}.json"
        path.write_text(
            json.dumps(
                {
                    "started_at": self.started_at,
                    "phases": self.phases,
                    "passed": self.passed,
                    "findings": [asdict(f) for f in self.findings],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("  PIPELINE MAXY — RIEPILOGO")
        print("=" * 60)
        for phase in self.phases:
            print(f"  Fase: {phase}")
        for f in self.findings:
            icon = {"error": "ERR", "warn": "WRN", "info": "INF"}[f.severity]
            loc = f" [{f.path}]" if f.path else ""
            print(f"  {icon}  {f.message}{loc}")
        print("-" * 60)
        print(f"  Esito: {'PASS' if self.passed else 'FAIL'}")
        print("=" * 60)
