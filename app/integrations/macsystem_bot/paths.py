"""Percorsi multi-root per manuali e datasheet (share di rete + fallback locale)."""

from __future__ import annotations

from pathlib import Path


class MultiRootManualDir:
    """Sostituisce MANUALI_DIR singola: ricerca su più cartelle UNC/locali."""

    def __init__(self, roots: list[Path]) -> None:
        self.roots = [Path(r) for r in roots if str(r).strip()]

    def exists(self) -> bool:
        return any(root.exists() for root in self.roots)

    def glob(self, pattern: str):
        seen: set[Path] = set()
        for root in self.roots:
            if not root.is_dir():
                continue
            for match in root.glob(pattern):
                resolved = match.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield match

    def __truediv__(self, other: str) -> Path:
        for root in self.roots:
            candidate = root / other
            if candidate.exists():
                return candidate
        return self.roots[0] / other if self.roots else Path(other)

    def __str__(self) -> str:
        return ";".join(str(r) for r in self.roots)

    def __fspath__(self) -> str:
        return str(self.roots[0]) if self.roots else ""

    def resolve(self) -> Path:
        return self.roots[0].resolve() if self.roots else Path(".")

    def find_file(self, name: str) -> Path | None:
        nome = Path(name).name
        for root in self.roots:
            if not root.is_dir():
                continue
            candidate = (root / nome).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                continue
            if candidate.is_file():
                return candidate
        return None
