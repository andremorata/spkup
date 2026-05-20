import sys

from PyQt6.QtWidgets import QApplication

from spkup.overlay import (
    OverlayState,
    OverlayWidget,
    build_recording_countdown_visual,
)

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def test_build_recording_countdown_visual_formats_mm_ss() -> None:
    visual = build_recording_countdown_visual(119.2, 120)

    assert visual.text == "02:00"
    assert visual.caption == "Time left"
    assert visual.urgent is False
    assert 0.99 <= visual.progress <= 1.0


def test_build_recording_countdown_visual_marks_low_time_as_urgent() -> None:
    visual = build_recording_countdown_visual(9.1, 120)

    assert visual.text == "00:10"
    assert visual.caption == "Stopping soon"
    assert visual.urgent is True
    assert 0.07 <= visual.progress <= 0.08


def test_build_recording_countdown_visual_clamps_bounds() -> None:
    over_limit = build_recording_countdown_visual(999.0, 120)
    under_limit = build_recording_countdown_visual(-5.0, 120)

    assert over_limit.text == "02:00"
    assert over_limit.progress == 1.0
    assert under_limit.text == "00:00"
    assert under_limit.progress == 0.0


def test_hidden_state_clears_recording_countdown_visual() -> None:
    overlay = OverlayWidget()
    overlay.set_recording_countdown(12.0, 120)

    overlay.show_state(OverlayState.HIDDEN)

    assert overlay._recording_countdown_visual is None
