"""Avvio automatico Integration Hub locale (nessun server centrale)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mac_ai_assistant.config import get_app_data_dir

_hub_process: subprocess.Popen | None = None
CREATE_NO_WINDOW = 0x08000000
_POSTGRES_PORT = 5432

_EASYONE_ENV_KEYS = (
    "EASYONE_API_URL",
    "EASYONE_BASE_URL",
    "EASYONE_EVENTS_URL",
    "EASYONE_EVENTS_BASE_URL",
    "EASYONE_TENANT_ID",
    "EASYONE_PORTAL_URL",
    "EASYONE_CRM_URL",
    "EASYONE_AUTH_MODE",
    "EASYONE_MODE",
)


def _project_root() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _hub_env_file() -> Path:
    return get_app_data_dir() / "hub.env"


def _db_init_pending_flag() -> Path:
    return get_app_data_dir() / "db_init_pending.flag"


def _installer_dir() -> Path | None:
    root = _project_root()
    if not root:
        return None
    installer = root / "installer"
    return installer if installer.is_dir() else None


def _is_mock_easyone_url(url: str) -> bool:
    lowered = (url or "").lower()
    return "8090" in lowered or "127.0.0.1" in lowered or "localhost" in lowered


def _read_hub_env_values() -> dict[str, str]:
    path = _hub_env_file()
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in _EASYONE_ENV_KEYS and val:
            values[key] = val
    return values


def _apply_hub_env(env: dict[str, str]) -> dict[str, str]:
    """hub.env deve vincere su variabili di sviluppo residue (es. :8090)."""
    file_vals = _read_hub_env_values()
    api_url = file_vals.get("EASYONE_API_URL") or file_vals.get("EASYONE_BASE_URL", "")
    if api_url and "macsystem" in api_url.lower():
        for key in _EASYONE_ENV_KEYS:
            current = env.get(key, "")
            if _is_mock_easyone_url(current) or key not in env:
                env.pop(key, None)
        for key, val in file_vals.items():
            env[key] = val
        env["EASYONE_API_URL"] = api_url
        env["EASYONE_BASE_URL"] = file_vals.get("EASYONE_BASE_URL") or api_url

    hub_env = _hub_env_file()
    if hub_env.is_file():
        env["MAC_AI_HUB_ENV"] = str(hub_env)
        try:
            from dotenv import load_dotenv

            load_dotenv(hub_env, override=True)
            for key, val in file_vals.items():
                if val:
                    env[key] = val
            if api_url:
                env["EASYONE_API_URL"] = api_url
                env["EASYONE_BASE_URL"] = file_vals.get("EASYONE_BASE_URL") or api_url
        except ImportError:
            pass
    return env


def _hub_port(base_url: str) -> int:
    parsed = urlparse(base_url)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def _hub_easyone_ok(base_url: str) -> bool:
    try:
        health = httpx.get(f"{base_url.rstrip('/')}/api/health", timeout=3).json()
    except Exception:
        return False
    if health.get("easyone_mock"):
        return False
    api_url = (health.get("easyone_api_url") or "").strip()
    if not api_url:
        return False
    lowered = api_url.lower()
    return "macsystem" in lowered and not _is_mock_easyone_url(api_url)


def _postgres_port_open(port: int = _POSTGRES_PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def _run_powershell_script(script: Path, *args: str) -> int:
    if not script.is_file():
        return 127
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *args,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return int(result.returncode)
    except Exception:
        return 1


def _ensure_postgresql_running() -> bool:
    if _postgres_port_open():
        return True

    installer = _installer_dir()
    if installer:
        ensure_script = installer / "ensure_postgresql.ps1"
        if ensure_script.is_file():
            if _run_powershell_script(ensure_script, "-TimeoutSeconds", "45") == 0:
                return _postgres_port_open()

    if sys.platform == "win32":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        "Get-Service -ErrorAction SilentlyContinue | "
                        "Where-Object { $_.Name -like '*postgres*' } | "
                        "ForEach-Object { if ($_.Status -ne 'Running') { Start-Service $_.Name } }"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                time.sleep(2)
                return _postgres_port_open()
        except Exception:
            pass
    return False


def _try_install_postgresql() -> bool:
    installer = _installer_dir()
    if not installer:
        return False

    redist_candidates = [
        installer / "redist" / "postgresql-18-windows-x64.exe",
        installer / "redist" / "postgresql-windows-x64.exe",
    ]
    installer_path = next((path for path in redist_candidates if path.is_file()), None)
    if not installer_path:
        return False

    install_script = installer / "install_postgresql.ps1"
    if not install_script.is_file():
        return False

    code = _run_powershell_script(
        install_script,
        "-InstallerPath",
        str(installer_path),
        "-SuperPassword",
        "admin",
    )
    return code == 0 and _postgres_port_open()


def _init_database_if_needed() -> bool:
    pending = _db_init_pending_flag()
    if not pending.is_file() and _postgres_port_open():
        return True

    exe = _hub_exe_path()
    if not exe:
        return False

    env = _build_subprocess_env()
    try:
        result = subprocess.run(
            [str(exe), "--init-db"],
            cwd=str(exe.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception:
        return False

    if result.returncode != 0:
        return False

    if pending.is_file():
        try:
            pending.unlink()
        except OSError:
            pass
    return True


def _postgres_error_message() -> str:
    hub_env = _hub_env_file()
    installer = _installer_dir()
    setup_guide = (
        str(installer / "POSTGRESQL_SETUP.txt")
        if installer and (installer / "POSTGRESQL_SETUP.txt").is_file()
        else "installer\\POSTGRESQL_SETUP.txt"
    )
    return (
        "PostgreSQL non è installato o non è in esecuzione su questo PC (porta 5432).\n\n"
        "1. Installare PostgreSQL 18 per Windows oppure usare l'installer Maxy AI.\n"
        f"2. Configurare la password in:\n   {hub_env}\n"
        "   (chiave DATABASE_URL — predefinita: admin)\n"
        "3. Riavviare: avviare il servizio PostgreSQL e riaprire Maxy AI.\n\n"
        f"Guida: {setup_guide}\n\n"
        "In alternativa, reinstallare Maxy AI accettando l'installazione automatica di PostgreSQL."
    )


def _terminate_listener_on_port(port: int) -> None:
    if sys.platform != "win32" or port <= 0:
        return
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"(Get-NetTCPConnection -LocalPort {port} -State Listen "
                    "-ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        pid = (result.stdout or "").strip()
        if pid.isdigit():
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True,
                timeout=12,
                check=False,
            )
            time.sleep(1)
    except Exception:
        pass


def _hub_exe_path() -> Path | None:
    root = _project_root()
    if not root:
        return None
    bundled = root / "hub" / "MAC_AI_Hub.exe"
    if bundled.is_file():
        return bundled
    return None


def _hub_dev_entry() -> Path | None:
    root = _project_root()
    if not root:
        return None
    entry = root / "scripts" / "hub_entry.py"
    if entry.is_file():
        return entry
    return None


def is_hub_healthy(base_url: str, *, timeout: float = 2.0) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/health", timeout=timeout)
        if response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("database") == "up"
    except Exception:
        return False


def _build_subprocess_env() -> dict[str, str]:
    return _apply_hub_env(os.environ.copy())


def start_hub_process() -> subprocess.Popen | None:
    global _hub_process
    env = _build_subprocess_env()
    exe = _hub_exe_path()

    if exe:
        _hub_process = subprocess.Popen(
            [str(exe)],
            cwd=str(exe.parent),
            env=env,
            creationflags=CREATE_NO_WINDOW,
        )
        return _hub_process

    entry = _hub_dev_entry()
    if entry and sys.executable:
        _hub_process = subprocess.Popen(
            [sys.executable, str(entry)],
            cwd=str(entry.parents[1]),
            env=env,
            creationflags=CREATE_NO_WINDOW,
        )
        return _hub_process

    return None


def ensure_hub_running(base_url: str, *, timeout_seconds: int = 60) -> tuple[bool, str]:
    """
    Verifica PostgreSQL, inizializza il DB se necessario e avvia l'Hub locale.
    """
    if not _ensure_postgresql_running():
        if not _try_install_postgresql():
            return False, _postgres_error_message()

    if not _init_database_if_needed():
        return False, (
            "Impossibile inizializzare il database locale.\n\n"
            f"{_postgres_error_message()}"
        )

    if is_hub_healthy(base_url) and _hub_easyone_ok(base_url):
        return True, ""

    if is_hub_healthy(base_url) and not _hub_easyone_ok(base_url):
        _terminate_listener_on_port(_hub_port(base_url))

    proc = start_hub_process()
    if proc is None:
        return False, (
            "Servizio locale non trovato.\n\n"
            "Reinstallare Maxy AI dall'installer aziendale."
        )

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False, _postgres_error_message()

        if is_hub_healthy(base_url) and _hub_easyone_ok(base_url):
            return True, ""

        time.sleep(1)

    return False, _postgres_error_message()
