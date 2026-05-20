from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from PyQt6 import QtCore
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPaintEvent, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

_MARGIN = 16
_PILL_W, _PILL_H = 220, 44
_CORNER_RADIUS = 6
_ICON_ZONE = 40  # px reserved for icon-mode animations
_COUNTDOWN_URGENT_THRESHOLD_S = 10.0
_pyqt_property = cast(Any, getattr(QtCore, "pyqtProperty"))


class OverlayState(Enum):
    HIDDEN = "hidden"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    ERROR = "error"


_STATE_COLORS: dict[OverlayState, str] = {
    OverlayState.RECORDING: "#A11E1B",
    OverlayState.TRANSCRIBING: "#FB8A00",
    OverlayState.DONE: "#0EE367",
    OverlayState.ERROR: "#E53935",
}

_STATE_LABELS: dict[OverlayState, str] = {
    OverlayState.RECORDING:    "Capturing",
    OverlayState.TRANSCRIBING: "Transcribing",
    OverlayState.DONE:         "Copied",
    OverlayState.ERROR:        "Failed",
}


@dataclass(frozen=True)
class RecordingCountdownVisual:
    text: str
    caption: str
    progress: float
    urgent: bool


def build_recording_countdown_visual(
    seconds_remaining: float, max_seconds: float
) -> RecordingCountdownVisual:
    bounded_total = max(1.0, float(max_seconds))
    bounded_remaining = min(max(float(seconds_remaining), 0.0), bounded_total)
    display_seconds = int(math.ceil(bounded_remaining))
    minutes, seconds = divmod(display_seconds, 60)
    progress = bounded_remaining / bounded_total
    urgent = bounded_remaining <= _COUNTDOWN_URGENT_THRESHOLD_S
    return RecordingCountdownVisual(
        text=f"{minutes:02d}:{seconds:02d}",
        caption="Stopping soon" if urgent else "Time left",
        progress=progress,
        urgent=urgent,
    )


class OverlayWidget(QWidget):
    """Frameless, always-on-top, click-through status pill.

    Shows recording / transcribing / done states as a colour-coded pill in a
    configurable corner of the primary screen.  Delegates visual effects to
    pluggable animation objects from the ``spkup.animations`` package.
    """

    def __init__(
        self,
        overlay_position: str = "bottom-right",
        *,
        recording_animation: str = "equalizer_bars",
        transcribing_animation: str = "spinning_arc",
        done_animation: str = "checkmark_draw",
        error_animation: str = "shake",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._state = OverlayState.HIDDEN
        self._pill_opacity_val: float = 1.0
        self._overlay_position = overlay_position
        self._recording_countdown_visual: RecordingCountdownVisual | None = None

        # Animation key settings
        self._animation_keys: dict[OverlayState, str] = {
            OverlayState.RECORDING: recording_animation,
            OverlayState.TRANSCRIBING: transcribing_animation,
            OverlayState.DONE: done_animation,
            OverlayState.ERROR: error_animation,
        }

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(_PILL_W, _PILL_H)

        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_hide)

        # Import lazily to avoid circular import
        from spkup.animations import get_animation

        self._get_animation = get_animation

        # Active animation instance (None when hidden)
        self._current_animation: Any | None = None

        self._reposition()

    # ---------- Public API ----------

    def set_animation_key(self, state: OverlayState, key: str) -> None:
        """Update the animation key for *state*."""
        self._animation_keys[state] = key

    def set_recording_countdown(
        self, seconds_remaining: float, max_seconds: float
    ) -> None:
        self._recording_countdown_visual = build_recording_countdown_visual(
            seconds_remaining, max_seconds
        )
        if self._state == OverlayState.RECORDING:
            self.update()

    def clear_recording_countdown(self) -> None:
        self._recording_countdown_visual = None
        if self._state == OverlayState.RECORDING:
            self.update()

    def show_state(self, state: OverlayState) -> None:
        """Transition to *state*, managing animation and auto-hide."""
        self._hide_timer.stop()

        # Stop existing animation
        if self._current_animation is not None:
            self._current_animation.cleanup()
            self._current_animation = None

        self._state = state

        if state == OverlayState.HIDDEN:
            self._recording_countdown_visual = None
            self._pill_opacity_val = 1.0
            self.hide()
            return

        if state != OverlayState.RECORDING:
            self._recording_countdown_visual = None

        # Instantiate and start the new animation
        key = self._animation_keys.get(state, "classic")
        self._current_animation = self._get_animation(state, key)
        self._pill_opacity_val = 1.0

        self.show()
        self._current_animation.start(self)
        self.update()

        if state == OverlayState.DONE:
            self._hide_timer.start(1500)
        elif state == OverlayState.ERROR:
            self._hide_timer.start(4000)

    # ---------- Internals ----------

    def _do_hide(self) -> None:
        if self._current_animation is not None:
            self._current_animation.cleanup()
            self._current_animation = None
        self._state = OverlayState.HIDDEN
        self.hide()

    def paintEvent(self, a0: QPaintEvent | None) -> None:  # noqa: N802
        if self._state == OverlayState.HIDDEN:
            return

        color_hex = _STATE_COLORS.get(self._state, "#999999")
        label = _STATE_LABELS.get(self._state, "")

        anim = self._current_animation

        # Some animations expose an opacity attribute
        opacity = getattr(anim, "opacity", None)
        if opacity is not None:
            self._pill_opacity_val = opacity

        # Some animations expose a shake_offset_x attribute
        shake_x = getattr(anim, "shake_offset_x", 0)
        if shake_x:
            self.move(self.x() + shake_x, self.y())

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._pill_opacity_val)

        # Draw pill background
        bg = QColor(color_hex)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), _CORNER_RADIUS, _CORNER_RADIUS)

        countdown_visual = (
            self._recording_countdown_visual
            if self._state == OverlayState.RECORDING
            else None
        )
        layout = getattr(anim, "layout_mode", "full") if anim else "full"
        if countdown_visual is not None:
            icon_rect = QRect(8, 6, _ICON_ZONE, _PILL_H - 14)
            if anim is not None:
                anim.paint(p, icon_rect)
            text_rect = QRect(
                icon_rect.right() + 8,
                0,
                self.width() - icon_rect.right() - 18,
                self.height() - 6,
            )
        elif layout == "icon" and anim is not None:
            icon_rect = QRect(4, 4, _ICON_ZONE, _PILL_H - 8)
            anim.paint(p, icon_rect)
            text_rect = QRect(
                _ICON_ZONE + 4, 0, _PILL_W - _ICON_ZONE - 8, _PILL_H
            )
        else:
            text_rect = self.rect()
            if anim is not None:
                anim.paint(p, self.rect())

        if countdown_visual is None:
            p.setPen(QColor("#ffffff"))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
            p.end()
            return

        status_rect = QRect(
            text_rect.left(),
            text_rect.top(),
            max(1, text_rect.width() // 2),
            text_rect.height(),
        )
        countdown_rect = QRect(
            status_rect.right(),
            text_rect.top(),
            max(1, text_rect.right() - status_rect.right()),
            text_rect.height(),
        )
        track_rect = QRect(10, self.height() - 6, self.width() - 20, 3)

        p.setPen(QColor("#ffffff"))
        status_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        p.setFont(status_font)
        p.drawText(
            status_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )

        countdown_color = QColor("#FFF59D" if countdown_visual.urgent else "#FFFFFF")
        p.setPen(countdown_color)
        countdown_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        p.setFont(countdown_font)
        p.drawText(
            countdown_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            countdown_visual.text,
        )

        track_color = QColor(255, 255, 255, 72)
        p.setBrush(track_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track_rect, 1.5, 1.5)

        fill_width = max(0, int(round(track_rect.width() * countdown_visual.progress)))
        if fill_width > 0:
            fill_rect = QRect(track_rect.left(), track_rect.top(), fill_width, track_rect.height())
            fill_color = QColor("#FFF59D" if countdown_visual.urgent else "#FFFFFF")
            p.setBrush(fill_color)
            p.drawRoundedRect(fill_rect, 1.5, 1.5)
        p.end()

    def _reposition(self) -> None:
        """Move to the configured corner of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        w, h = self.width(), self.height()
        pos = self._overlay_position

        cx = avail.left() + (avail.width() - w) // 2

        if pos == "bottom-right":
            x, y = avail.right() - w - _MARGIN, avail.bottom() - h - _MARGIN
        elif pos == "bottom-left":
            x, y = avail.left() + _MARGIN, avail.bottom() - h - _MARGIN
        elif pos == "bottom-center":
            x, y = cx, avail.bottom() - h - _MARGIN
        elif pos == "top-right":
            x, y = avail.right() - w - _MARGIN, avail.top() + _MARGIN
        elif pos == "top-left":
            x, y = avail.left() + _MARGIN, avail.top() + _MARGIN
        elif pos == "top-center":
            x, y = cx, avail.top() + _MARGIN
        else:
            x, y = avail.right() - w - _MARGIN, avail.bottom() - h - _MARGIN

        self.move(x, y)
