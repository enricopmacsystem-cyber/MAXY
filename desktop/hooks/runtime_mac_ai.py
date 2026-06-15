# PyInstaller runtime hook — imposta PATH per Qt e directory applicazione
import os
import sys


def _setup() -> None:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        internal = os.path.join(base, "_internal")
        if os.path.isdir(internal):
            os.environ["PATH"] = internal + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("MAC_AI_APP_DIR", base)


_setup()
