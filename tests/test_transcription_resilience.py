"""App-level integration tests for transcription resilience features.

All heavy Qt components (tray, overlay, recorder, listener, transcriber) are
replaced with MagicMock objects so that no real audio hardware, GPU, or Qt
event loop is required.  We exercise the resilience methods directly:
  _on_transcription_error, _on_transcription_finished, _on_transcription_timeout
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, call, patch

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from spkup.app import App
from spkup.config import AppConfig
from spkup.overlay import OverlayState

# One QApplication for the whole module (required for QObject internals).
_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Stub App factory
# ---------------------------------------------------------------------------


def _make_stub_app(
    *,
    device: str = "cuda",
    timeout_seconds: int = 300,
    timeout_was_cuda_retry: bool = False,
    has_pending_retry: bool = True,
    retry_last_returns: bool = True,
) -> App:
    """Return a minimal App shell with all heavy dependencies replaced by mocks."""
    app = QObject.__new__(App)
    QObject.__init__(app)

    app._config = AppConfig(device=device, transcription_timeout_seconds=timeout_seconds)
    app._timeout_was_cuda_retry = timeout_was_cuda_retry

    # Transcriber mock
    transcriber = MagicMock()
    transcriber.has_pending_retry = has_pending_retry
    transcriber.retry_last.return_value = retry_last_returns
    app._transcriber = transcriber

    # Overlay, tray, retry action
    app._overlay = MagicMock()
    app._tray = MagicMock()
    app._retry_action = MagicMock()

    # Watchdog timer mock
    watchdog = MagicMock()
    app._transcription_watchdog = watchdog

    # History mocks (needed by _on_transcription_finished)
    history_entry = MagicMock()
    history_entry.id = "entry-1"
    history = MagicMock()
    history.add.return_value = history_entry
    history.list_entries.return_value = []
    app._transcription_history = history
    app._transcription_history_window = MagicMock()

    return app  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# test_watchdog_fires_on_timeout
# ---------------------------------------------------------------------------


def test_watchdog_fires_on_timeout() -> None:
    """When the watchdog fires (_on_transcription_timeout), cleanup_worker is called."""
    # Use CPU so that the auto-retry branch is skipped.
    app = _make_stub_app(device="cpu", has_pending_retry=False)

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_timeout()

    app._transcriber.cleanup_worker.assert_called_once()


# ---------------------------------------------------------------------------
# test_error_shows_error_overlay
# ---------------------------------------------------------------------------


def test_error_shows_error_overlay() -> None:
    """_on_transcription_error shows OverlayState.ERROR on the overlay."""
    app = _make_stub_app()

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_error("cuda oom")

    app._overlay.show_state.assert_called_with(OverlayState.ERROR)


# ---------------------------------------------------------------------------
# test_retry_action_enabled_on_error
# ---------------------------------------------------------------------------


def test_retry_action_enabled_on_error() -> None:
    """_on_transcription_error enables retry action when has_pending_retry is True."""
    app = _make_stub_app(has_pending_retry=True)

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_error("model not found")

    app._retry_action.setEnabled.assert_called_with(True)


# ---------------------------------------------------------------------------
# test_retry_action_disabled_on_success
# ---------------------------------------------------------------------------


def test_retry_action_disabled_on_success() -> None:
    """_on_transcription_finished disables the retry action."""
    app = _make_stub_app()

    with patch("spkup.app.copy_to_clipboard"), patch("spkup.app.play_cue"):
        app._on_transcription_finished("Hello world")

    app._retry_action.setEnabled.assert_called_with(False)


# ---------------------------------------------------------------------------
# test_timeout_auto_retries_on_cpu
# ---------------------------------------------------------------------------


def test_timeout_auto_retries_on_cpu() -> None:
    """When device is 'cuda' and timeout fires, retry_last(force_cpu=True) is called
    and the overlay transitions back to TRANSCRIBING."""
    app = _make_stub_app(device="cuda", timeout_was_cuda_retry=False, retry_last_returns=True)

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_timeout()

    app._transcriber.retry_last.assert_called_once_with(force_cpu=True)
    app._overlay.show_state.assert_called_with(OverlayState.TRANSCRIBING)
    assert app._timeout_was_cuda_retry is True
