import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from spkup.app import App, RECORDING_COUNTDOWN_INTERVAL_MS
from spkup.config import AppConfig

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def _make_stub_app(*, max_recording_seconds: int = 120) -> App:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._config = AppConfig(max_recording_seconds=max_recording_seconds)
    app._overlay = MagicMock()
    app._recording_countdown_timer = MagicMock()
    app._recording_deadline_monotonic = None
    app._recording_active = False
    app._recording_start_pending = False
    app._recorder = MagicMock()
    app._tray = MagicMock()
    app._stop_transcription_watchdog = MagicMock()
    app._set_retry_action_enabled = MagicMock()
    return app  # type: ignore[return-value]


def test_start_recording_countdown_sets_deadline_and_updates_overlay(monkeypatch) -> None:
    app = _make_stub_app(max_recording_seconds=120)
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 10.0)

    app._start_recording_countdown()

    assert app._recording_deadline_monotonic == 130.0
    app._recording_countdown_timer.start.assert_called_once_with(
        RECORDING_COUNTDOWN_INTERVAL_MS
    )
    app._overlay.set_recording_countdown.assert_called_once_with(120.0, 120)


def test_refresh_recording_countdown_uses_remaining_time(monkeypatch) -> None:
    app = _make_stub_app(max_recording_seconds=120)
    app._recording_deadline_monotonic = 130.0
    monkeypatch.setattr("spkup.app.time.monotonic", lambda: 21.25)

    app._refresh_recording_countdown()

    app._overlay.set_recording_countdown.assert_called_once_with(108.75, 120)


def test_stop_recording_countdown_clears_overlay_and_deadline() -> None:
    app = _make_stub_app(max_recording_seconds=120)
    app._recording_deadline_monotonic = 130.0

    app._stop_recording_countdown()

    assert app._recording_deadline_monotonic is None
    app._recording_countdown_timer.stop.assert_called_once_with()
    app._overlay.clear_recording_countdown.assert_called_once_with()


def test_begin_recording_session_starts_countdown() -> None:
    app = _make_stub_app(max_recording_seconds=120)
    app._recording_start_pending = True
    app._playback_mute = MagicMock()
    app._config = AppConfig(max_recording_seconds=120, mute_playback_while_recording=True)
    app._start_recording_countdown = MagicMock()

    app._begin_recording_session()

    app._start_recording_countdown.assert_called_once_with()
    app._overlay.show_state.assert_called_once()
    app._recorder.start.assert_called_once_with()


def test_recording_stop_clears_countdown_before_transcribing() -> None:
    app = _make_stub_app(max_recording_seconds=120)
    app._recording_active = True
    app._playback_mute = MagicMock()
    app._start_trigger_suppression_until = 0.0
    app._timeout_was_cuda_retry = False
    app._start_transcription_watchdog = MagicMock()
    app._arm_start_trigger_suppression = MagicMock()
    app._stop_recording_countdown = MagicMock()

    app._on_recording_stopped()

    app._stop_recording_countdown.assert_called_once_with()
    app._recorder.stop.assert_called_once_with()
    assert app._transcribing_active is True


def test_recording_error_clears_countdown() -> None:
    app = _make_stub_app(max_recording_seconds=120)
    app._playback_mute = MagicMock()
    app._arm_start_trigger_suppression = MagicMock()
    app._stop_recording_countdown = MagicMock()

    app._on_recording_error("mic failed")

    app._stop_recording_countdown.assert_called_once_with()
