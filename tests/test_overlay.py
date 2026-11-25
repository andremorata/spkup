import sys

from PyQt6.QtWidgets import QApplication

from spkup.overlay import (
    OverlayState,
    OverlayWidget,
    build_recording_countdown_visual,
)

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def test_build_recording_countdown_visual_formats_m_ss() -> None:
    visual = build_recording_countdown_visual(119.2, 120)

    assert visual.text == "2:00"
    assert visual.urgent is False


def test_build_recording_countdown_visual_marks_low_time_as_urgent() -> None:
    visual = build_recording_countdown_visual(9.1, 120)

    assert visual.text == "0:10"
    assert visual.urgent is True


def test_build_recording_countdown_visual_clamps_bounds() -> None:
    assert build_recording_countdown_visual(999.0, 120).text == "2:00"
    assert build_recording_countdown_visual(-5.0, 120).text == "0:00"


def test_hidden_state_clears_recording_countdown_visual() -> None:
    overlay = OverlayWidget()
    overlay.set_recording_countdown(12.0, 120)

    overlay.show_state(OverlayState.HIDDEN)

    assert overlay._recording_countdown_visual is None


def test_recording_bars_follow_the_level_source() -> None:
    level = {"value": 0.0}
    overlay = OverlayWidget(level_source=lambda: level["value"])
    overlay.show_state(OverlayState.RECORDING)
    for _ in range(6):
        overlay._tick()
    assert max(overlay._history) == 0.0

    level["value"] = 1.0
    for _ in range(6):
        overlay._tick()
    assert overlay._history[-1] > 0.9

    level["value"] = 0.0
    for _ in range(30):
        overlay._tick()
    assert overlay._history[-1] < 0.1
    assert max(overlay._history) > 0.9  # the loud moment scrolls left, not erased
    overlay.show_state(OverlayState.HIDDEN)


def test_hidden_state_fades_out_and_hides() -> None:
    overlay = OverlayWidget()
    overlay.show_state(OverlayState.DONE)
    for _ in range(10):
        overlay._tick()
    assert overlay.isVisible()

    overlay.show_state(OverlayState.HIDDEN)
    for _ in range(20):
        overlay._tick()

    assert not overlay.isVisible()
    assert not overlay._tick_timer.isActive()
