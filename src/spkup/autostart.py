from __future__ import annotations

import sys
import winreg

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "spkup"


def _exe_command() -> str:
    """Return the command that launches spkup via the current Python interpreter."""
    return f'"{sys.executable}" -m spkup'


def enable_autostart() -> None:
    """Write the autostart registry key for the current user."""
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_command())


def disable_autostart() -> None:
    """Remove the autostart registry key; silently ignores if absent."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _APP_NAME)
    except FileNotFoundError:
        pass


def is_autostart_enabled() -> bool:
    """Return True if the autostart registry key exists."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _APP_NAME)
        return True
    except FileNotFoundError:
        return False
