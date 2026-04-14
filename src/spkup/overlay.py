from __future__ import annotations

from enum import Enum
from typing import Any, cast

from PyQt6 import QtCore
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPaintEvent, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

_MARGIN = 16
_PILL_W, _PILL_H = 160, 44
_CORNER_RADIUS = 6
_ICON_ZONE = 36  # px reserved for icon-mode animations
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

    def show_state(self, state: OverlayState) -> None:
        """Transition to *state*, managing animation and auto-hide."""
        self._hide_timer.stop()

        # Stop existing animation
        if self._current_animation is not None:
            self._current_animation.cleanup()
            self._current_animation = None

        self._state = state

        if state == OverlayState.HIDDEN:
            self._pill_opacity_val = 1.0
            self.hide()
            return

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

        # Layout mode determines text placement and animation zone
        layout = getattr(anim, "layout_mode", "full") if anim else "full"
        if layout == "icon" and anim is not None:
            icon_rect = QRect(4, 4, _ICON_ZONE, _PILL_H - 8)
            anim.paint(p, icon_rect)
            text_rect = QRect(
                _ICON_ZONE + 4, 0, _PILL_W - _ICON_ZONE - 8, _PILL_H
            )
        else:
            text_rect = self.rect()
            if anim is not None:
                anim.paint(p, self.rect())

        # Draw label
        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
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
