from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from spkup.app import App, TRIGGER_SUPPRESSION_WINDOW_S
from spkup.config import AppConfig

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def _make_request_stub_app(
    *,
    recording_active: bool = False,
    recording_start_pending: bool = False,
    suppression_until: float = 0.0,
    transcribing_active: bool = False,
) -> App:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._recording_active = recording_active
    app._recording_start_pending = recording_start_pending
    app._transcribing_active = transcribing_active
    app._start_trigger_suppression_until = suppression_until
    app._on_recording_started = MagicMock()
    app._on_recording_stopped = MagicMock()
    return app  # type: ignore[return-value]


def _make_full_stub_app(
    *,
    duration_s: float = 5.0,
    recording_active: bool = False,
    recording_start_pending: bool = False,
) -> App:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._config = AppConfig()
    app._recording_active = recording_active
    app._recording_start_pending = recording_start_pending
    app._start_trigger_suppression_until = 0.0
    app._last_recording_duration = duration_s
    app._overlay = MagicMock()
    app._tray = MagicMock()
    app._recorder = MagicMock()
    app._transcription_history = MagicMock()
    app._transcription_history_window = MagicMock()
    app._retry_action = MagicMock()
    app._stop_transcription_watchdog = MagicMock()
    app._set_retry_action_enabled = MagicMock()
    app._restore_playback_mute = MagicMock()
    app._transcription_history.add.return_value = MagicMock(id="entry-1")
    app._transcription_history.list_entries.return_value = []
    return app  # type: ignore[return-value]


def test_tray_left_click_starts_when_idle() -> None:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._recording_active = False
    app._recording_start_pending = False
    app._request_recording_start = MagicMock()
    app._request_recording_stop = MagicMock()

    app._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)

    app._request_recording_start.assert_called_once_with("tray")
    app._request_recording_stop.assert_not_called()


def test_tray_left_click_stops_when_recording_or_pending() -> None:
    for active, pending in ((True, False), (False, True)):
        app = QObject.__new__(App)
        QObject.__init__(app)
        app._recording_active = active
        app._recording_start_pending = pending
        app._request_recording_start = MagicMock()
        app._request_recording_stop = MagicMock()

        app._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)

        app._request_recording_stop.assert_called_once_with("tray")
        app._request_recording_start.assert_not_called()


def test_tray_non_trigger_activation_is_ignored_off_macos() -> None:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._recording_active = False
    app._recording_start_pending = False
    app._request_recording_start = MagicMock()
    app._request_recording_stop = MagicMock()
    app._menu = MagicMock()

    with patch("spkup.app.is_macos", return_value=False):
        app._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
        app._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)

    app._request_recording_start.assert_not_called()
    app._request_recording_stop.assert_not_called()
    app._menu.popup.assert_not_called()


def test_tray_right_click_pops_menu_on_macos() -> None:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._recording_active = False
    app._recording_start_pending = False
    app._request_recording_start = MagicMock()
    app._request_recording_stop = MagicMock()
    app._menu = MagicMock()

    with patch("spkup.app.is_macos", return_value=True):
        app._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
        # Other non-trigger reasons stay inert even on macOS.
        app._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)

    app._menu.popup.assert_called_once()
    app._request_recording_start.assert_not_called()
    app._request_recording_stop.assert_not_called()


def test_request_recording_start_ignored_during_suppression_window(monkeypatch) -> None:
    app = _make_request_stub_app(suppression_until=10.75)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 10.25)

    app._request_recording_start("hotkey")

    app._on_recording_started.assert_not_called()


def test_request_recording_start_ignored_when_already_active_or_pending(monkeypatch) -> None:
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 5.0)

    active_app = _make_request_stub_app(recording_active=True)
    active_app._request_recording_start("hotkey")
    active_app._on_recording_started.assert_not_called()

    pending_app = _make_request_stub_app(recording_start_pending=True)
    pending_app._request_recording_start("hotkey")
    pending_app._on_recording_started.assert_not_called()


def test_request_recording_stop_allowed_during_suppression_window() -> None:
    app = _make_request_stub_app(recording_active=True, suppression_until=99.0)

    app._request_recording_stop("hotkey")

    app._on_recording_stopped.assert_called_once()


def test_request_recording_stop_ignored_when_idle() -> None:
    app = _make_request_stub_app(suppression_until=99.0)

    app._request_recording_stop("hotkey")

    app._on_recording_stopped.assert_not_called()


def test_cancelled_pending_start_sets_suppression_window(monkeypatch) -> None:
    app = _make_full_stub_app(recording_start_pending=True)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 12.0)

    app._on_recording_stopped()

    assert app._start_trigger_suppression_until == 12.0 + TRIGGER_SUPPRESSION_WINDOW_S


def test_recording_error_sets_suppression_window(monkeypatch) -> None:
    app = _make_full_stub_app(recording_active=True)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 25.0)

    app._on_recording_error("mic failed")

    assert app._start_trigger_suppression_until == 25.0 + TRIGGER_SUPPRESSION_WINDOW_S


def test_transcription_finish_sets_suppression_window(monkeypatch) -> None:
    app = _make_full_stub_app(duration_s=3.0)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 40.0)

    with patch("spkup.app.copy_to_clipboard"), patch("spkup.app.play_cue"):
        app._on_transcription_finished("hello")

    assert app._start_trigger_suppression_until == 40.0 + TRIGGER_SUPPRESSION_WINDOW_S
