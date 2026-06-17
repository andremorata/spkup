"""macOS Accessibility and Input Monitoring permission helpers.

The global push-to-talk hotkey relies on `pynput`, which on macOS observes
keyboard events through a CGEventTap. That tap is gated by two TCC grants:

1. **Input Monitoring** — required for the event tap to receive keyboard
   events (Privacy & Security → Privacy → Input Monitoring).
2. **Accessibility** — sometimes also required depending on how pynput
   interacts with the system (Privacy & Security → Privacy → Accessibility).

Without Input Monitoring, `pynput` silently receives no events and the hotkey
appears dead, so spkup needs to detect the state and guide the user to grant it.

There is no equivalent gate on Windows/Linux, so every function treats those
platforms as already trusted and no-ops.
"""

from __future__ import annotations

import logging
import subprocess

from spkup.platform_support import is_macos

_log = logging.getLogger(__name__)

# Deep link to the Input Monitoring pane in System Settings.
INPUT_MONITORING_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
)
# Deep link to the Accessibility pane in System Settings.
ACCESSIBILITY_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def input_monitoring_required(sys_platform: str | None = None) -> bool:
    """Whether the running platform gates global input on Input Monitoring."""
    return is_macos(sys_platform)


def accessibility_required(sys_platform: str | None = None) -> bool:
    """Whether the running platform gates global input on Accessibility."""
    return is_macos(sys_platform)


def is_input_monitoring_trusted(sys_platform: str | None = None) -> bool:
    """Return True when the process may observe global keyboard events via CGEventTap.

    On non-macOS platforms there is no such gate, so this is always True. On
    macOS it checks whether the app has been granted Input Monitoring permission.
    This uses tccutil query to check if the app bundle ID is in the allowed list.

    If the check fails or pyobjc is unavailable, returns True so spkup never
    nags the user about a state it cannot actually verify.
    """
    if not is_macos(sys_platform):
        return True

    try:
        import subprocess
        # Get the bundle identifier of the current process
        try:
            from Foundation import NSBundle
            bundle_id = NSBundle.mainBundle().bundleIdentifier()
        except Exception:
            _log.warning("Could not determine bundle ID; skipping Input Monitoring check")
            return True
        
        if not bundle_id:
            _log.warning("Empty bundle ID; skipping Input Monitoring check")
            return True

        # Query TCC database for ListenEvent permission
        result = subprocess.run(
            ["tccutil", "info", "kTCCServiceListenEvent", bundle_id],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # If tccutil returns 0 and output contains "authorized", it's granted
        if result.returncode == 0 and "authorized" in result.stdout.lower():
            return True
        return False
    except Exception:  # pragma: no cover - defensive
        _log.exception("Input Monitoring check failed")
        return True


def is_accessibility_trusted(sys_platform: str | None = None) -> bool:
    """Return True when the process may observe global keyboard events.

    On non-macOS platforms there is no such gate, so this is always True. On
    macOS it queries ``AXIsProcessTrusted``. If pyobjc is somehow unavailable
    or the call fails, it returns True so spkup never nags the user about a
    state it cannot actually verify.
    """
    if not is_macos(sys_platform):
        return True
    try:
        from ApplicationServices import AXIsProcessTrusted
    except Exception:  # pragma: no cover - pyobjc ships transitively with pynput
        _log.warning("ApplicationServices unavailable; skipping Accessibility check")
        return True
    try:
        return bool(AXIsProcessTrusted())
    except Exception:  # pragma: no cover - defensive
        _log.exception("AXIsProcessTrusted() failed")
        return True


def request_input_monitoring_trust(sys_platform: str | None = None) -> bool:
    """Surface the native Input Monitoring prompt if the grant is missing.

    Returns the current trust state. Unlike Accessibility, macOS does not
    provide a programmatic way to trigger the Input Monitoring grant dialog.
    Instead, this opens System Settings directly to the correct pane.
    No-op / always True off macOS.
    """
    if not is_macos(sys_platform):
        return True
    # Cannot programmatically trigger Input Monitoring dialog
    # Just open settings
    open_input_monitoring_settings(sys_platform)
    return is_input_monitoring_trusted(sys_platform)


def request_accessibility_trust(sys_platform: str | None = None) -> bool:
    """Surface the native Accessibility prompt if the grant is missing.

    Returns the current trust state. When untrusted, macOS shows its standard
    dialog (with an "Open System Settings" button) the first time this is
    called for the process. No-op / always True off macOS.
    """
    if not is_macos(sys_platform):
        return True
    try:
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
    except Exception:  # pragma: no cover - pyobjc ships transitively with pynput
        _log.warning("ApplicationServices unavailable; skipping Accessibility prompt")
        return True
    try:
        return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
    except Exception:  # pragma: no cover - defensive
        _log.exception("AXIsProcessTrustedWithOptions() failed")
        return is_accessibility_trusted(sys_platform)


def open_input_monitoring_settings(sys_platform: str | None = None) -> None:
    """Open the Input Monitoring pane in System Settings. No-op off macOS."""
    if not is_macos(sys_platform):
        return
    try:
        subprocess.run(["open", INPUT_MONITORING_SETTINGS_URL], check=False)
    except Exception:  # pragma: no cover - defensive
        _log.exception("Failed to open Input Monitoring settings")


def open_accessibility_settings(sys_platform: str | None = None) -> None:
    """Open the Accessibility pane in System Settings. No-op off macOS."""
    if not is_macos(sys_platform):
        return
    try:
        subprocess.run(["open", ACCESSIBILITY_SETTINGS_URL], check=False)
    except Exception:  # pragma: no cover - defensive
        _log.exception("Failed to open Accessibility settings")
