from __future__ import annotations

import sys

from spkup.platform_support import supports_autostart

try:
    import winreg as _winreg
except ImportError:
    _winreg = None

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "spkup"


class AutostartUnavailableError(RuntimeError):
    """Raised when login autostart is not supported on the current platform."""


def _require_winreg():
    if not supports_autostart() or _winreg is None:
        raise AutostartUnavailableError(
            "Start on login is currently supported only on Windows."
        )
    return _winreg


def _exe_command() -> str:
    """Return the command that launches spkup in dev or frozen mode."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m spkup'


def enable_autostart() -> None:
    """Write the autostart registry key for the current user."""
    winreg = _require_winreg()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_command())


def disable_autostart() -> None:
    """Remove the autostart registry key; silently ignores if absent."""
    winreg = _require_winreg()
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _APP_NAME)
    except FileNotFoundError:
        pass


def is_autostart_enabled() -> bool:
    """Return True if the autostart registry key exists."""
    if not supports_autostart() or _winreg is None:
        return False
    winreg = _winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _APP_NAME)
        return True
    except FileNotFoundError:
        return False
