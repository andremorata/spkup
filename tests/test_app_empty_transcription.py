"""App-level tests for empty-transcription detection.

`_on_transcription_finished` is the single place that translates whisper
output into user-visible UX (clipboard, history, overlay, tray). These tests
bypass App.__init__ and stub every collaborator so behaviour can be asserted
without audio hardware or a real Qt tray.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from spkup.app import App, EMPTY_WARNING_THRESHOLD_S
from spkup.config import AppConfig

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def _make_stub_app(duration_s: float) -> App:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._config = AppConfig()
    app._last_recording_duration = duration_s
    app._overlay = MagicMock()
    app._tray = MagicMock()
    app._transcription_history = MagicMock()
    app._transcription_history_window = MagicMock()
    app._retry_action = MagicMock()
    app._transcription_watchdog = MagicMock()
    return app  # type: ignore[return-value]


def test_capture_recording_duration_computes_seconds() -> None:
    """_capture_recording_duration stores samples / 16 kHz as a float."""
    import numpy as np

    app = _make_stub_app(duration_s=0.0)
    audio = np.zeros(32000, dtype=np.float32)  # 2.0 s at 16 kHz
    app._capture_recording_duration(audio)
    assert app._last_recording_duration == 2.0


def test_capture_recording_duration_handles_bad_payload() -> None:
    """A non-numpy payload must not raise."""
    app = _make_stub_app(duration_s=42.0)
    app._capture_recording_duration(None)
    assert app._last_recording_duration == 0.0


def test_empty_long_recording_shows_no_speech_warning() -> None:
    """≥ 5 s recording with empty text: tray warning + ERROR overlay + no writes."""
    app = _make_stub_app(duration_s=EMPTY_WARNING_THRESHOLD_S + 0.5)

    with patch("spkup.app.copy_to_clipboard") as clip, \
         patch("spkup.app.play_cue") as cue, \
         patch.object(QSystemTrayIcon, "supportsMessages", return_value=True):
        app._on_transcription_finished("   ")

    clip.assert_not_called()
    cue.assert_not_called()
    app._transcription_history.add.assert_not_called()
    app._tray.showMessage.assert_called_once()
    title, body, icon, timeout = app._tray.showMessage.call_args.args
    assert "No speech detected" in title
    assert "microphone" in body.lower()
    assert icon == QSystemTrayIcon.MessageIcon.Warning
    app._overlay.show_state.assert_called_once()
    state_arg = app._overlay.show_state.call_args.args[0]
    assert state_arg.name == "ERROR"


def test_empty_short_recording_is_silent() -> None:
    """< 5 s empty recording: DONE overlay, no tray warning, no writes."""
    app = _make_stub_app(duration_s=1.0)

    with patch("spkup.app.copy_to_clipboard") as clip, \
         patch("spkup.app.play_cue") as cue, \
         patch.object(QSystemTrayIcon, "supportsMessages", return_value=True):
        app._on_transcription_finished("")

    clip.assert_not_called()
    cue.assert_not_called()
    app._transcription_history.add.assert_not_called()
    app._tray.showMessage.assert_not_called()
    app._overlay.show_state.assert_called_once()
    state_arg = app._overlay.show_state.call_args.args[0]
    assert state_arg.name == "DONE"


def test_non_empty_transcription_preserves_existing_behavior() -> None:
    """Non-empty text: clipboard copied, history appended, DONE overlay, 'done' cue."""
    app = _make_stub_app(duration_s=3.0)
    app._transcription_history.add.return_value = MagicMock(id="entry-1")
    app._transcription_history.list_entries.return_value = []

    with patch("spkup.app.copy_to_clipboard") as clip, \
         patch("spkup.app.play_cue") as cue:
        app._on_transcription_finished("  hello world  ")

    clip.assert_called_once_with("hello world")
    cue.assert_called_once_with("done")
    app._transcription_history.add.assert_called_once_with("hello world")
    app._tray.showMessage.assert_not_called()
    state_arg = app._overlay.show_state.call_args.args[0]
    assert state_arg.name == "DONE"


def test_empty_threshold_is_five_seconds() -> None:
    """Sanity-check the module constant doesn't drift accidentally."""
    assert EMPTY_WARNING_THRESHOLD_S == 5.0
