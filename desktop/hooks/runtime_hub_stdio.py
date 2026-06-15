"""PyInstaller runtime hook: exe senza console non ha stdout/stderr."""
import os
import sys

if getattr(sys, "frozen", False):
    sink = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = sink
    if sys.stderr is None:
        sys.stderr = sink
