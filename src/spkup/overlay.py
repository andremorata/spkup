from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPaintEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from spkup.platform_support import is_macos, ui_font_family

_MARGIN = 16
_WIN_W, _WIN_H = 200, 60  # fixed window; the capsule morphs inside it
_CAPSULE_H = 34
_PAD_X = 14
_BAR_COUNT = 16
_BAR_W, _BAR_GAP = 3.0, 2.0
_BAR_MIN_H, _BAR_MAX_H = 3.0, 20.0
_TRANSCRIBING_BARS = 7
_TICK_MS = 16
_HISTORY_PUSH_TICKS = 3  # one new bar every ~48 ms, so the strip shows ~0.8 s of voice
_ATTACK, _RELEASE = 0.55, 0.18  # level smoothing: rise fast, fall slow
_COUNTDOWN_URGENT_THRESHOLD_S = 10.0

_BG = QColor(20, 20, 22, 235)
_BORDER = QColor(255, 255, 255, 30)
_FG = QColor(255, 255, 255, 235)
_RED = QColor("#FF453A")
_GREEN = QColor("#30D158")
_AMBER = QColor("#FFD60A")


class OverlayState(Enum):
    HIDDEN = "hidden"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    ERROR = "error"


_STATE_LABELS: dict[OverlayState, str] = {
    OverlayState.DONE: "Copied",
    OverlayState.ERROR: "Failed",
}


@dataclass(frozen=True)
class RecordingCountdownVisual:
    text: str
    urgent: bool


def build_recording_countdown_visual(
    seconds_remaining: float, max_seconds: float
) -> RecordingCountdownVisual:
    bounded_total = max(1.0, float(max_seconds))
    bounded_remaining = min(max(float(seconds_remaining), 0.0), bounded_total)
    minutes, seconds = divmod(int(math.ceil(bounded_remaining)), 60)
    return RecordingCountdownVisual(
        text=f"{minutes}:{seconds:02d}",
        urgent=bounded_remaining <= _COUNTDOWN_URGENT_THRESHOLD_S,
    )


def _approach(current: float, target: float, rate: float) -> float:
    return current + (target - current) * rate


class OverlayWidget(QWidget):
    """Frameless, always-on-top, click-through status capsule.

    RECORDING draws a scrolling waveform driven by the live microphone level
    from *level_source*; TRANSCRIBING a soft shimmer; DONE / ERROR a glyph and
    a short label. The capsule width morphs between states and the whole
    overlay fades in and out.
    """

    def __init__(
        self,
        overlay_position: str = "bottom-center",
        *,
        level_source: Callable[[], float] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._state = OverlayState.HIDDEN
        self._painted_state = OverlayState.HIDDEN  # keeps content while fading out
        self._overlay_position = overlay_position
        self._level_source = level_source
        self._recording_countdown_visual: RecordingCountdownVisual | None = None

        self._level = 0.0
        self._history: deque[float] = deque([0.0] * _BAR_COUNT, maxlen=_BAR_COUNT)
        self._ticks = 0
        self._opacity = 0.0
        self._capsule_w = float(_CAPSULE_H)
        self._phase_started = time.monotonic()

        # On macOS, Qt.WindowType.Tool windows are tied to the owning app
        # being frontmost. spkup is a menu-bar app that never becomes frontmost,
        # so a Tool window would never display. Use a plain frameless top-level
        # window with WA_TransparentForMouseEvents instead so the overlay stays
        # visible and click-through on macOS.
        if is_macos():
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
                | Qt.WindowType.BypassWindowManagerHint
                # The system shadow follows a stale alpha mask while the capsule morphs.
                | Qt.WindowType.NoDropShadowWindowHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        else:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowTransparentForInput
            )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(_WIN_W, _WIN_H)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(_TICK_MS)
        self._tick_timer.timeout.connect(self._tick)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_hide)

        self._reposition()

    # ---------- Public API ----------

    def set_recording_countdown(
        self, seconds_remaining: float, max_seconds: float
    ) -> None:
        self._recording_countdown_visual = build_recording_countdown_visual(
            seconds_remaining, max_seconds
        )

    def clear_recording_countdown(self) -> None:
        self._recording_countdown_visual = None

    def show_state(self, state: OverlayState) -> None:
        """Transition to *state*, managing fade, morph and auto-hide."""
        self._hide_timer.stop()
        self._state = state

        if state != OverlayState.RECORDING:
            self._recording_countdown_visual = None

        if state == OverlayState.HIDDEN:
            return  # _tick fades out and hides

        if state == OverlayState.RECORDING:
            self._level = 0.0
            self._history = deque([0.0] * _BAR_COUNT, maxlen=_BAR_COUNT)

        if not self.isVisible():
            self._capsule_w = float(_CAPSULE_H)  # grow out of a circle
        self._painted_state = state
        self._phase_started = time.monotonic()
        self.show()
        self._tick_timer.start()

        if state == OverlayState.DONE:
            self._hide_timer.start(1200)
        elif state == OverlayState.ERROR:
            self._hide_timer.start(3000)

    # ---------- Internals ----------

    def _do_hide(self) -> None:
        self._state = OverlayState.HIDDEN

    def _tick(self) -> None:
        self._ticks += 1
        if self._state == OverlayState.RECORDING and self._level_source is not None:
            target = max(0.0, min(1.0, float(self._level_source())))
            rate = _ATTACK if target > self._level else _RELEASE
            self._level = _approach(self._level, target, rate)
            if self._ticks % _HISTORY_PUSH_TICKS == 0:
                self._history.append(self._level)
            else:
                self._history[-1] = max(self._history[-1], self._level)

        self._capsule_w = _approach(self._capsule_w, self._target_width(), 0.22)

        if self._state == OverlayState.HIDDEN:
            self._opacity = max(0.0, self._opacity - 0.12)
            if self._opacity <= 0.0:
                self._tick_timer.stop()
                self._painted_state = OverlayState.HIDDEN
                self.hide()
                return
        else:
            self._opacity = min(1.0, self._opacity + 0.15)
        self.update()

    def _label_font(self) -> QFont:
        font = QFont(ui_font_family())
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    def _countdown_text(self) -> str | None:
        visual = self._recording_countdown_visual
        if self._painted_state == OverlayState.RECORDING and visual and visual.urgent:
            return visual.text
        return None

    def _leading_width(self) -> float:
        """Width of the slot before the bars / label: dot, countdown or glyph."""
        countdown = self._countdown_text()
        if countdown is not None:
            return QFontMetricsF(self._label_font()).horizontalAdvance(countdown) + 10
        return 18.0

    def _target_width(self) -> float:
        state = self._painted_state
        if state == OverlayState.RECORDING:
            bars = _BAR_COUNT * (_BAR_W + _BAR_GAP) - _BAR_GAP
            return 2 * _PAD_X + self._leading_width() + bars
        if state == OverlayState.TRANSCRIBING:
            return 2 * _PAD_X + _TRANSCRIBING_BARS * (_BAR_W + _BAR_GAP) - _BAR_GAP
        if state in _STATE_LABELS:
            text_w = QFontMetricsF(self._label_font()).horizontalAdvance(_STATE_LABELS[state])
            return 2 * _PAD_X + self._leading_width() + text_w
        return float(_CAPSULE_H)

    def _capsule_rect(self) -> QRectF:
        w = min(self._capsule_w, _WIN_W - 8.0)
        y = (_WIN_H - _CAPSULE_H) / 2
        pos = self._overlay_position
        if pos.endswith("right"):
            x = _WIN_W - 4.0 - w
        elif pos.endswith("left"):
            x = 4.0
        else:
            x = (_WIN_W - w) / 2
        return QRectF(x, y, w, _CAPSULE_H)

    def paintEvent(self, a0: QPaintEvent | None) -> None:  # noqa: N802
        state = self._painted_state
        if state == OverlayState.HIDDEN:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)

        capsule = self._capsule_rect()
        radius = _CAPSULE_H / 2

        # Soft shadow: a few widening low-alpha rings under the capsule.
        p.setPen(Qt.PenStyle.NoPen)
        for spread, alpha in ((6, 14), (4, 22), (2, 34)):
            p.setBrush(QColor(0, 0, 0, alpha))
            r = capsule.adjusted(-spread, -spread + 2, spread, spread + 2)
            p.drawRoundedRect(r, radius + spread, radius + spread)

        p.setBrush(_BG)
        p.setPen(QPen(_BORDER, 1.0))
        p.drawRoundedRect(capsule, radius, radius)

        clip = QPainterPath()
        clip.addRoundedRect(capsule, radius, radius)
        p.setClipPath(clip)

        if state == OverlayState.RECORDING:
            self._paint_recording(p, capsule)
        elif state == OverlayState.TRANSCRIBING:
            self._paint_transcribing(p, capsule)
        else:
            self._paint_result(p, capsule, state)
        p.end()

    def _paint_bars(
        self, p: QPainter, left: float, cy: float, heights: list[float], color: QColor
    ) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        x = left
        for h in heights:
            p.drawRoundedRect(QRectF(x, cy - h / 2, _BAR_W, h), _BAR_W / 2, _BAR_W / 2)
            x += _BAR_W + _BAR_GAP

    def _paint_recording(self, p: QPainter, capsule: QRectF) -> None:
        cy = capsule.center().y()
        lead = self._leading_width()
        countdown = self._countdown_text()
        if countdown is not None:
            p.setFont(self._label_font())
            p.setPen(_AMBER)
            p.drawText(
                QRectF(capsule.left() + _PAD_X, capsule.top(), lead, capsule.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                countdown,
            )
        else:
            dot_r = 3.5 + 1.5 * self._level
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_RED)
            p.drawEllipse(QRectF(
                capsule.left() + _PAD_X + 4 - dot_r, cy - dot_r, 2 * dot_r, 2 * dot_r
            ))

        heights = [_BAR_MIN_H + (_BAR_MAX_H - _BAR_MIN_H) * v for v in self._history]
        bars_w = _BAR_COUNT * (_BAR_W + _BAR_GAP) - _BAR_GAP
        # Anchor bars to the right edge so the strip slides in while the capsule grows.
        self._paint_bars(p, capsule.right() - _PAD_X - bars_w, cy, heights, _FG)

    def _paint_transcribing(self, p: QPainter, capsule: QRectF) -> None:
        t = time.monotonic() - self._phase_started
        heights = [
            _BAR_MIN_H + 7.0 * (0.5 + 0.5 * math.sin(t * 7.0 - i * 0.75))
            for i in range(_TRANSCRIBING_BARS)
        ]
        bars_w = _TRANSCRIBING_BARS * (_BAR_W + _BAR_GAP) - _BAR_GAP
        color = QColor(_FG)
        color.setAlpha(170)
        self._paint_bars(p, capsule.center().x() - bars_w / 2, capsule.center().y(), heights, color)

    def _paint_result(self, p: QPainter, capsule: QRectF, state: OverlayState) -> None:
        cy = capsule.center().y()
        gx = capsule.left() + _PAD_X + 5
        color = _GREEN if state == OverlayState.DONE else _RED
        pen = QPen(color, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        if state == OverlayState.DONE:
            path.moveTo(gx - 5, cy)
            path.lineTo(gx - 1.5, cy + 3.5)
            path.lineTo(gx + 5, cy - 4)
        else:
            path.moveTo(gx - 4, cy - 4)
            path.lineTo(gx + 4, cy + 4)
            path.moveTo(gx + 4, cy - 4)
            path.lineTo(gx - 4, cy + 4)
        p.drawPath(path)

        p.setFont(self._label_font())
        p.setPen(_FG)
        text_left = capsule.left() + _PAD_X + self._leading_width()
        p.drawText(
            QRectF(text_left, capsule.top(), capsule.right() - text_left, capsule.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            _STATE_LABELS[state],
        )

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
            x, y = cx, avail.bottom() - h - _MARGIN

        self.move(x, y)
