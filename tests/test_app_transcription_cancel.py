"""App-level tests for manual cancellation of in-progress transcription.

Covers the single App-level cancel entry point wired in `app.py`:

- cancel accepted only while transcribing
- cancel does not copy to clipboard or append to history
- cancel returns overlay to hidden and disables retry action
- trigger-suppression window is armed so the cancel gesture does not
  re-enter recording
- start-trigger requests during the transcribing state are routed through
  the cancel entry point instead of starting a new recording
- existing timeout/retry/error paths keep `_transcribing_active` consistent

All heavy dependencies (recorder, overlay, tray, transcriber, watchdog) are
replaced with MagicMock objects; no audio hardware, GPU, or real Qt event
loop is needed.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from spkup.app import App, TRIGGER_SUPPRESSION_WINDOW_S
from spkup.config import AppConfig
from spkup.overlay import OverlayState

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Stub factory
# ---------------------------------------------------------------------------


def _make_stub_app(
    *,
    transcribing_active: bool = True,
    recording_active: bool = False,
    recording_start_pending: bool = False,
    has_pending_retry: bool = True,
    device: str = "cuda",
) -> App:
    app = QObject.__new__(App)
    QObject.__init__(app)

    app._config = AppConfig(device=device)
    app._transcribing_active = transcribing_active
    app._recording_active = recording_active
    app._recording_start_pending = recording_start_pending
    app._start_trigger_suppression_until = 0.0
    app._timeout_was_cuda_retry = False
    app._last_recording_duration = 10.0

    transcriber = MagicMock()
    transcriber.has_pending_retry = has_pending_retry
    transcriber.cancel_active.return_value = True
    app._transcriber = transcriber

    app._overlay = MagicMock()
    app._tray = MagicMock()
    app._retry_action = MagicMock()
    app._transcription_watchdog = MagicMock()

    history_entry = MagicMock()
    history_entry.id = "entry-1"
    history = MagicMock()
    history.add.return_value = history_entry
    history.list_entries.return_value = []
    app._transcription_history = history
    app._transcription_history_window = MagicMock()

    return app  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# _cancel_active_transcription direct behavior
# ---------------------------------------------------------------------------


def test_cancel_during_transcribing_discards_worker_and_hides_overlay(monkeypatch) -> None:
    app = _make_stub_app()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 50.0)

    result = app._cancel_active_transcription("hotkey")

    assert result is True
    assert app._transcribing_active is False
    app._transcriber.cancel_active.assert_called_once()
    app._transcriber.clear_retry_state.assert_called_once()
    app._transcription_watchdog.stop.assert_called()
    app._overlay.show_state.assert_called_with(OverlayState.HIDDEN)
    app._retry_action.setEnabled.assert_called_with(False)
    assert app._start_trigger_suppression_until == 50.0 + TRIGGER_SUPPRESSION_WINDOW_S
    assert app._timeout_was_cuda_retry is False


def test_cancel_when_not_transcribing_is_noop() -> None:
    app = _make_stub_app(transcribing_active=False)

    result = app._cancel_active_transcription("hotkey")

    assert result is False
    app._transcriber.cancel_active.assert_not_called()
    app._transcriber.clear_retry_state.assert_not_called()
    app._overlay.show_state.assert_not_called()


def test_cancel_does_not_copy_clipboard_or_append_history(monkeypatch) -> None:
    app = _make_stub_app()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)

    with patch("spkup.app.copy_to_clipboard") as mock_copy:
        app._cancel_active_transcription("hotkey")

    mock_copy.assert_not_called()
    app._transcription_history.add.assert_not_called()


# ---------------------------------------------------------------------------
# Routing via _request_recording_start
# ---------------------------------------------------------------------------


def test_request_start_during_transcribing_routes_to_cancel(monkeypatch) -> None:
    app = _make_stub_app()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._on_recording_started = MagicMock()

    app._request_recording_start("hotkey")

    app._transcriber.cancel_active.assert_called_once()
    app._on_recording_started.assert_not_called()
    assert app._transcribing_active is False


def test_request_start_during_transcribing_from_tray_also_cancels(monkeypatch) -> None:
    app = _make_stub_app()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._on_recording_started = MagicMock()

    app._request_recording_start("tray")

    app._transcriber.cancel_active.assert_called_once()
    app._on_recording_started.assert_not_called()


def test_request_start_when_idle_still_starts_recording(monkeypatch) -> None:
    app = _make_stub_app(transcribing_active=False)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._on_recording_started = MagicMock()

    app._request_recording_start("hotkey")

    app._on_recording_started.assert_called_once()
    app._transcriber.cancel_active.assert_not_called()


# ---------------------------------------------------------------------------
# Trigger-guard interaction
# ---------------------------------------------------------------------------


def test_cancel_followed_by_immediate_start_is_suppressed(monkeypatch) -> None:
    app = _make_stub_app()

    # Cancel at t=10
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 10.0)
    app._cancel_active_transcription("hotkey")

    # Immediate start trigger (t=10.2) should be blocked by the suppression window
    app._on_recording_started = MagicMock()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 10.2)
    app._request_recording_start("hotkey")

    app._on_recording_started.assert_not_called()


def test_cancel_allows_fresh_start_after_suppression_window(monkeypatch) -> None:
    app = _make_stub_app()

    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 10.0)
    app._cancel_active_transcription("hotkey")

    # After the suppression window, a start trigger should go through
    app._on_recording_started = MagicMock()
    monkeypatch.setattr(
        "spkup.app.time.monotonic",
        lambda: 10.0 + TRIGGER_SUPPRESSION_WINDOW_S + 0.1,
    )
    app._request_recording_start("hotkey")

    app._on_recording_started.assert_called_once()


# ---------------------------------------------------------------------------
# Transcribing flag stays consistent on terminal paths
# ---------------------------------------------------------------------------


def test_transcription_finished_clears_transcribing_active(monkeypatch) -> None:
    app = _make_stub_app()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._stop_transcription_watchdog = MagicMock()
    app._set_retry_action_enabled = MagicMock()

    with patch("spkup.app.copy_to_clipboard"), patch("spkup.app.play_cue"):
        app._on_transcription_finished("hello world")

    assert app._transcribing_active is False


def test_transcription_error_clears_transcribing_active(monkeypatch) -> None:
    app = _make_stub_app()
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._stop_transcription_watchdog = MagicMock()
    app._set_retry_action_enabled = MagicMock()

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_error("boom")

    assert app._transcribing_active is False


def test_timeout_terminal_path_clears_transcribing_active(monkeypatch) -> None:
    # device=cpu so the auto-retry branch is skipped -> terminal path
    app = _make_stub_app(device="cpu", has_pending_retry=False)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._set_retry_action_enabled = MagicMock()

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_timeout()

    assert app._transcribing_active is False


def test_timeout_auto_retry_keeps_transcribing_active(monkeypatch) -> None:
    app = _make_stub_app(device="cuda")
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 0.0)
    app._transcriber.retry_last.return_value = True
    app._start_transcription_watchdog = MagicMock()
    app._set_retry_action_enabled = MagicMock()

    with patch("spkup.app.QSystemTrayIcon") as MockQSTI:
        MockQSTI.supportsMessages.return_value = False
        app._on_transcription_timeout()

    # CUDA->CPU auto-retry kept a worker alive, so transcribing state continues
    assert app._transcribing_active is True
    app._transcriber.retry_last.assert_called_once_with(force_cpu=True)


def test_manual_retry_reenters_transcribing_active(monkeypatch) -> None:
    app = _make_stub_app(transcribing_active=False)
    app._transcriber.retry_last.return_value = True
    app._start_transcription_watchdog = MagicMock()
    app._set_retry_action_enabled = MagicMock()

    app._on_retry_last()

    assert app._transcribing_active is True
    app._overlay.show_state.assert_called_with(OverlayState.TRANSCRIBING)


# ---------------------------------------------------------------------------
# Transcriber.clear_retry_state unit check
# ---------------------------------------------------------------------------


def test_transcriber_clear_retry_state_disables_has_pending_retry() -> None:
    from spkup.transcriber import Transcriber
    import numpy as np

    t = Transcriber(AppConfig())
    t._last_audio = np.zeros(100, dtype=np.float32)
    t._last_params = {"model_size": "m", "device": "cuda", "compute_type": "int8"}

    assert t.has_pending_retry is True

    t.clear_retry_state()

    assert t.has_pending_retry is False
    assert t._last_audio is None
    assert t._last_params is None
