from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes as wintypes
import sys
from configparser import ConfigParser
from pathlib import Path

from mac_ai_assistant.config import get_app_data_dir

_CREDENTIALS_FILE = "login.ini"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _credentials_path() -> Path:
    return get_app_data_dir() / _CREDENTIALS_FILE


def _bytes_to_blob(data: bytes) -> _DATA_BLOB:
    buffer = ctypes.create_string_buffer(data)
    return _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))


def _encrypt_password(password: str) -> str:
    if sys.platform != "win32":
        return base64.b64encode(password.encode("utf-8")).decode("ascii")
    data = password.encode("utf-16-le")
    blob_in = _bytes_to_blob(data)
    blob_out = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        return base64.b64encode(password.encode("utf-8")).decode("ascii")
    encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return base64.b64encode(encrypted).decode("ascii")


def _decrypt_password(token: str) -> str:
    raw = base64.b64decode(token.encode("ascii"))
    if sys.platform != "win32":
        return raw.decode("utf-8")
    blob_in = _bytes_to_blob(raw)
    blob_out = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        return raw.decode("utf-8", errors="ignore")
    decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return decrypted.decode("utf-16-le")


def load_saved_login() -> tuple[str, str, bool]:
    """Restituisce (username, password, remember)."""
    path = _credentials_path()
    if not path.is_file():
        return "", "", False
    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if not parser.has_section("login"):
        return "", "", False
    remember = parser.getboolean("login", "remember", fallback=False)
    username = parser.get("login", "username", fallback="").strip()
    if not remember or not username:
        return username, "", remember
    token = parser.get("login", "password_enc", fallback="").strip()
    if not token:
        return username, "", remember
    try:
        password = _decrypt_password(token)
    except Exception:
        return username, "", False
    return username, password, True


def save_login(*, username: str, password: str, remember: bool) -> None:
    if not remember:
        clear_saved_login()
        return
    path = _credentials_path()
    parser = ConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")
    if not parser.has_section("login"):
        parser.add_section("login")
    parser.set("login", "remember", "true")
    parser.set("login", "username", username.strip())
    parser.set("login", "password_enc", _encrypt_password(password))
    with path.open("w", encoding="utf-8") as fh:
        parser.write(fh)


def clear_saved_login() -> None:
    path = _credentials_path()
    if path.is_file():
        path.unlink()


def save_refresh_token(refresh_token: str) -> None:
    """Salva il refresh token per ripristinare la sessione al prossimo avvio."""
    path = _credentials_path()
    parser = ConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")
    if not parser.has_section("session"):
        parser.add_section("session")
    parser.set("session", "refresh_token_enc", _encrypt_password(refresh_token))
    with path.open("w", encoding="utf-8") as fh:
        parser.write(fh)


def load_refresh_token() -> str | None:
    path = _credentials_path()
    if not path.is_file():
        return None
    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if not parser.has_section("session"):
        return None
    token = parser.get("session", "refresh_token_enc", fallback="").strip()
    if not token:
        return None
    try:
        value = _decrypt_password(token)
    except Exception:
        return None
    return value or None


def clear_refresh_token() -> None:
    path = _credentials_path()
    if not path.is_file():
        return
    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if parser.has_section("session"):
        parser.remove_section("session")
        with path.open("w", encoding="utf-8") as fh:
            parser.write(fh)
