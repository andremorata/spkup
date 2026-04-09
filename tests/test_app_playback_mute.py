"""App-level lifecycle tests for playback-mute integration.

These tests bypass App.__init__ via object.__new__ and replace every heavy Qt
component (tray icon, overlay, recorder, listener) with MagicMock objects.
The PlaybackMuteController is replaced with a lightweight call-counting spy so
the exact mute/restore interactions can be asserted without real audio hardware.

A module-level QApplication is created once so that Qt internals invoked inside
_on_recording_stopped and _on_recording_error (_make_tray_icon → QPixmap) do
not crash.
"""
from __future__ import annotations

import sys
from typing import cast
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from spkup.app import App
from spkup.config import AppConfig
from spkup.playback_mute import PlaybackMuteController

# Ensure a QApplication exists for the Qt calls inside _on_recording_stopped
# and _on_recording_error (specifically _make_tray_icon which creates a QPixmap).
_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Minimal fake PlaybackMuteController
# ---------------------------------------------------------------------------


class _FakePlaybackMuteController:
    """Call-counting spy that mirrors PlaybackMuteController's public API."""

    def __init__(self) -> None:
        self._restore_pending = False
        self.mute_call_count = 0
        self.restore_call_count = 0

    @property
    def restore_pending(self) -> bool:
        return self._restore_pending

    def mute_for_recording(self) -> bool:
        self.mute_call_count += 1
        self._restore_pending = True
        return True

    def restore(self) -> bool:
        self.restore_call_count += 1
        self._restore_pending = False
        return True


# ---------------------------------------------------------------------------
# Stub App factory
# ---------------------------------------------------------------------------


def _make_stub_app(
    *,
    mute_playback: bool,
    recording_active: bool = False,
    recording_start_pending: bool = False,
    controller: _FakePlaybackMuteController | None = None,
) -> tuple[App, _FakePlaybackMuteController]:
    """Build a minimal App shell with all heavy dependencies replaced by mocks."""
    app = QObject.__new__(App)
    QObject.__init__(app)

    if controller is None:
        controller = _FakePlaybackMuteController()

    app._config = AppConfig(mute_playback_while_recording=mute_playback)
    app._playback_mute = cast(PlaybackMuteController, controller)
    app._recording_active = recording_active
    app._recording_start_pending = recording_start_pending

    app._overlay = MagicMock()
    app._recorder = MagicMock()
    app._tray = MagicMock()
    app._listener = MagicMock()
    app._listener_active = False

    return app, controller  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# _begin_recording_session
# ---------------------------------------------------------------------------


def test_begin_recording_session_mutes_when_setting_enabled() -> None:
    """When the mute setting is on, _begin_recording_session calls mute_for_recording."""
    app, ctrl = _make_stub_app(mute_playback=True, recording_start_pending=True)

    app._begin_recording_session()

    assert ctrl.mute_call_count == 1
    assert app._recording_active is True
    assert app._recording_start_pending is False


def test_begin_recording_session_skips_mute_when_setting_disabled() -> None:
    """When the mute setting is off, mute_for_recording must never be called."""
    app, ctrl = _make_stub_app(mute_playback=False, recording_start_pending=True)

    app._begin_recording_session()

    assert ctrl.mute_call_count == 0
    assert app._recording_active is True


def test_begin_recording_session_aborts_when_not_pending() -> None:
    """_begin_recording_session is a no-op if _recording_start_pending is False."""
    app, ctrl = _make_stub_app(mute_playback=True, recording_start_pending=False)

    app._begin_recording_session()

    assert ctrl.mute_call_count == 0
    assert app._recording_active is False


# ---------------------------------------------------------------------------
# _on_recording_stopped
# ---------------------------------------------------------------------------


def test_on_recording_stopped_restores_mute_on_normal_path() -> None:
    """Normal stop (active recording, timer idle) must restore the mute snapshot."""
    ctrl = _FakePlaybackMuteController()
    ctrl.mute_for_recording()  # pre-arm: restore_pending = True
    app, _ = _make_stub_app(mute_playback=True, recording_active=True, controller=ctrl)

    with patch("spkup.app.play_cue") as play_cue:
        app._on_recording_stopped()

    assert ctrl.restore_call_count == 1
    assert app._recording_active is False
    play_cue.assert_called_once_with("transcribing")


def test_on_recording_stopped_no_restore_when_timer_still_active() -> None:
    """Key released before the start-cue timer fires means no mute was ever
    applied, so no restore must happen."""
    ctrl = _FakePlaybackMuteController()
    app, _ = _make_stub_app(
        mute_playback=True,
        recording_start_pending=True,
        controller=ctrl,
    )

    app._on_recording_stopped()

    assert ctrl.mute_call_count == 0
    assert ctrl.restore_call_count == 0


def test_on_recording_stopped_noop_restore_when_already_cleared() -> None:
    """Stale stop signal after error already cleared state: restore_pending is
    False so restore must not be called."""
    ctrl = _FakePlaybackMuteController()
    # ctrl.restore_pending is False (mute_for_recording was never called)
    app, _ = _make_stub_app(mute_playback=True, recording_active=False, controller=ctrl)

    app._on_recording_stopped()

    assert ctrl.restore_call_count == 0


# ---------------------------------------------------------------------------
# _on_recording_error
# ---------------------------------------------------------------------------


def test_on_recording_error_restores_mute() -> None:
    """A recording error must restore the playback mute snapshot and clear flags."""
    ctrl = _FakePlaybackMuteController()
    ctrl.mute_for_recording()
    app, _ = _make_stub_app(mute_playback=True, recording_active=True, controller=ctrl)

    app._on_recording_error("mic failed")

    assert ctrl.restore_call_count == 1
    assert app._recording_active is False
    assert app._recording_start_pending is False


def test_on_recording_error_noop_restore_when_setting_disabled() -> None:
    """If mute was never enabled, the error handler must not invoke restore."""
    app, ctrl = _make_stub_app(mute_playback=False, recording_active=True)

    app._on_recording_error("device unavailable")

    assert ctrl.restore_call_count == 0


# ---------------------------------------------------------------------------
# _cleanup
# ---------------------------------------------------------------------------


def test_cleanup_restores_pending_mute() -> None:
    """If a mute snapshot is still pending at shutdown, _cleanup must restore it."""
    ctrl = _FakePlaybackMuteController()
    ctrl.mute_for_recording()
    app, _ = _make_stub_app(mute_playback=True, recording_active=True, controller=ctrl)

    app._cleanup()

    assert ctrl.restore_call_count == 1


def test_cleanup_noop_restore_when_setting_disabled() -> None:
    """With the mute setting off, no snapshot is ever taken; cleanup must not
    call restore."""
    app, ctrl = _make_stub_app(mute_playback=False)

    app._cleanup()

    assert ctrl.restore_call_count == 0
