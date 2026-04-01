from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

_MARGIN = 16


class OverlayState(Enum):
    HIDDEN = "hidden"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    DONE = "done"


_STATE_COLORS: dict[OverlayState, str] = {
    OverlayState.RECORDING: "#A11E1B",
    OverlayState.TRANSCRIBING: "#FFB963",
    OverlayState.DONE: "#A2FFA7",
}

_STATE_LABELS: dict[OverlayState, str] = {
    OverlayState.RECORDING:    "Capturing",
    OverlayState.TRANSCRIBING: "Transcribing",
    OverlayState.DONE:         "Copied",
}


class OverlayWidget(QWidget):
    """Frameless, always-on-top, click-through status pill.

    Shows recording / transcribing / done states as a colour-coded pill in a
    configurable corner of the primary screen.  Pulses during RECORDING and
    auto-hides 1.5 s after transitioning to DONE.
    """

    def __init__(self, overlay_position: str = "bottom-right", parent=None) -> None:
        super().__init__(parent)
        self._state = OverlayState.HIDDEN
        self._pill_opacity_val: float = 1.0
        self._overlay_position = overlay_position

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(260, 44)

        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_hide)

        self._pulse_anim = QPropertyAnimation(self, b"pill_opacity")
        self._pulse_anim.setDuration(1800)
        self._pulse_anim.setKeyValueAt(0.0, 1.0)
        self._pulse_anim.setKeyValueAt(0.5, 0.45)
        self._pulse_anim.setKeyValueAt(1.0, 1.0)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.Linear)

        self._reposition()

    # ---------- Qt property for QPropertyAnimation ----------

    def _get_pill_opacity(self) -> float:
        return self._pill_opacity_val

    def _set_pill_opacity(self, value: float) -> None:
        self._pill_opacity_val = value
        self.update()

    pill_opacity = pyqtProperty(float, _get_pill_opacity, _set_pill_opacity)

    # ---------- Public API ----------

    def show_state(self, state: OverlayState) -> None:
        """Transition to *state*, managing animation and auto-hide."""
        self._hide_timer.stop()
        self._state = state

        if state == OverlayState.HIDDEN:
            self._pulse_anim.stop()
            self._pill_opacity_val = 1.0
            self.hide()
            return

        self.show()
        self.update()

        if state == OverlayState.RECORDING:
            self._pill_opacity_val = 1.0
            self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._pill_opacity_val = 1.0
            if state == OverlayState.DONE:
                self._hide_timer.start(1500)

    # ---------- Internals ----------

    def _do_hide(self) -> None:
        self._state = OverlayState.HIDDEN
        self.hide()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._state == OverlayState.HIDDEN:
            return

        color_hex = _STATE_COLORS.get(self._state, "#999999")
        label = _STATE_LABELS.get(self._state, "")

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._pill_opacity_val)

        bg = QColor(color_hex)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, label)
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
