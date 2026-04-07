from __future__ import annotations

from spkup.playback_mute import PlaybackMuteController


class FakePlaybackMuteBackend:
    def __init__(
        self,
        *,
        muted: bool,
        fail_on_get: bool = False,
        fail_on_set: bool = False,
    ) -> None:
        self.muted = muted
        self.fail_on_get = fail_on_get
        self.fail_on_set = fail_on_set
        self.calls: list[tuple[str, bool | None]] = []

    def get_mute(self) -> bool:
        self.calls.append(("get", None))
        if self.fail_on_get:
            raise OSError("default playback endpoint unavailable")
        return self.muted

    def set_mute(self, muted: bool) -> None:
        self.calls.append(("set", muted))
        if self.fail_on_set:
            raise OSError("failed to set mute")
        self.muted = muted


def test_mute_for_recording_snapshots_and_restores_previous_state() -> None:
    backend = FakePlaybackMuteBackend(muted=False)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is True
    assert controller.restore_pending is True
    assert backend.muted is True

    assert controller.restore() is True
    assert controller.restore_pending is False
    assert backend.muted is False
    assert backend.calls == [("get", None), ("set", True), ("set", False)]


def test_mute_for_recording_preserves_already_muted_state() -> None:
    backend = FakePlaybackMuteBackend(muted=True)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is True
    assert backend.muted is True

    assert controller.restore() is True
    assert backend.muted is True
    assert backend.calls == [("get", None)]


def test_restore_is_idempotent_after_successful_restore() -> None:
    backend = FakePlaybackMuteBackend(muted=False)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is True
    assert controller.restore() is True
    assert controller.restore() is False
    assert backend.calls == [("get", None), ("set", True), ("set", False)]


def test_backend_failure_falls_back_to_no_op_behavior() -> None:
    backend = FakePlaybackMuteBackend(muted=False, fail_on_get=True)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is False
    assert controller.restore_pending is False
    assert controller.restore() is False
    assert backend.calls == [("get", None)]


def test_set_mute_failure_during_mute_for_recording_leaves_no_restore_pending() -> None:
    """If set_mute raises while applying the mute, the snapshot is cleared so no restore is pending."""
    backend = FakePlaybackMuteBackend(muted=False, fail_on_set=True)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is False
    assert controller.restore_pending is False
    assert controller.restore() is False
    assert backend.calls == [("get", None), ("set", True)]


def test_set_mute_failure_during_restore_leaves_snapshot_pending() -> None:
    """If set_mute raises while restoring, the snapshot is preserved so a retry can succeed later."""
    backend = FakePlaybackMuteBackend(muted=False)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is True
    assert controller.restore_pending is True

    backend.fail_on_set = True
    assert controller.restore() is False
    assert controller.restore_pending is True


def test_mute_for_recording_is_idempotent_when_snapshot_already_set() -> None:
    """A second call to mute_for_recording before restore must not overwrite the snapshot."""
    backend = FakePlaybackMuteBackend(muted=False)
    controller = PlaybackMuteController(backend=backend)

    assert controller.mute_for_recording() is True
    assert controller.mute_for_recording() is True  # re-entry guard
    assert backend.calls == [("get", None), ("set", True)]  # backend called only once
