"""Error-state animations."""

from __future__ import annotations

import math
import time
from typing import Literal

from PyQt6.QtCore import QRect, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from spkup.animations.base import BaseAnimation
from spkup.animations import register
from spkup.overlay import OverlayState


# ---------------------------------------------------------------------------
# Shake — horizontal oscillation with damping
# ---------------------------------------------------------------------------

class ShakeAnimation(BaseAnimation):
    """Quick horizontal shake — ±3px, 2 oscillations, ~300ms, damped."""

    layout_mode: Literal["full"] = "full"
    _DURATION = 0.32  # seconds
    _AMPLITUDE = 3  # pixels
    _OSCILLATIONS = 2

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(16)
        self._widget: QWidget | None = None
        self._t0 = 0.0
        self.shake_offset_x = 0

    def start(self, widget: QWidget) -> None:
        self._widget = widget
        self._t0 = time.monotonic()
        self.shake_offset_x = 0
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        if self._widget is None:
            return
        t = time.monotonic() - self._t0
        progress = min(1.0, t / self._DURATION)
        # Damped sine
        envelope = 1.0 - progress
        angle = progress * self._OSCILLATIONS * 2 * math.pi
        self.shake_offset_x = int(self._AMPLITUDE * envelope * math.sin(angle))
        self._widget.update()

    def stop(self) -> None:
        self._timer.stop()
        try:
            self._timer.timeout.disconnect(self._tick)
        except (TypeError, RuntimeError):
            pass
        self.shake_offset_x = 0
        self._widget = None

    def paint(self, painter: QPainter, rect: QRect) -> None:
        # Shake is handled by the overlay adjusting its position via shake_offset_x.
        # Paint is a no-op — the pill itself looks normal, just shifted.
        pass


# ---------------------------------------------------------------------------
# X-Mark Draw — animated ✗ drawn stroke-by-stroke
# ---------------------------------------------------------------------------

class XMarkDrawAnimation(BaseAnimation):
    """Animated X mark drawn stroke-by-stroke in the icon zone."""

    layout_mode: Literal["icon"] = "icon"
    _DRAW_DURATION = 0.4  # seconds

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(16)
        self._widget: QWidget | None = None
        self._t0 = 0.0

    def start(self, widget: QWidget) -> None:
        self._widget = widget
        self._t0 = time.monotonic()
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        if self._widget is not None:
            self._widget.update()

    def stop(self) -> None:
        self._timer.stop()
        try:
            self._timer.timeout.disconnect(self._tick)
        except (TypeError, RuntimeError):
            pass
        self._widget = None

    def paint(self, painter: QPainter, rect: QRect) -> None:
        t = time.monotonic() - self._t0
        progress = min(1.0, t / self._DRAW_DURATION)

        pad = 7
        cx, cy = rect.center().x(), rect.center().y()
        half = min(rect.width(), rect.height()) // 2 - pad

        pen = QPen(QColor("#ffffff"), 3.0)
        pen.setCapStyle(pen.capStyle().RoundCap)  # type: ignore[arg-type]
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))

        # First stroke: top-left → bottom-right (0→50%)
        if progress > 0:
            f = min(1.0, progress / 0.5)
            path1 = QPainterPath()
            path1.moveTo(cx - half, cy - half)
            path1.lineTo(
                cx - half + 2 * half * f,
                cy - half + 2 * half * f,
            )
            painter.drawPath(path1)

        # Second stroke: top-right → bottom-left (50%→100%)
        if progress > 0.5:
            f = min(1.0, (progress - 0.5) / 0.5)
            path2 = QPainterPath()
            path2.moveTo(cx + half, cy - half)
            path2.lineTo(
                cx + half - 2 * half * f,
                cy - half + 2 * half * f,
            )
            painter.drawPath(path2)


# ---------------------------------------------------------------------------
# Pulsing Red — fast opacity pulse
# ---------------------------------------------------------------------------

class PulsingRedAnimation(BaseAnimation):
    """Fast 600ms opacity pulse — urgent warning feel."""

    layout_mode: Literal["full"] = "full"
    _PERIOD = 0.6  # seconds per cycle

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
        self._widget: QWidget | None = None
        self._t0 = 0.0
        self.opacity = 1.0

    def start(self, widget: QWidget) -> None:
        self._widget = widget
        self._t0 = time.monotonic()
        self.opacity = 1.0
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        if self._widget is None:
            return
        t = time.monotonic() - self._t0
        phase = (t % self._PERIOD) / self._PERIOD
        # Smooth triangle wave between 0.45 and 1.0
        self.opacity = 0.45 + 0.55 * (1.0 - abs(2.0 * phase - 1.0))
        self._widget.update()

    def stop(self) -> None:
        self._timer.stop()
        try:
            self._timer.timeout.disconnect(self._tick)
        except (TypeError, RuntimeError):
            pass
        self.opacity = 1.0
        self._widget = None

    def paint(self, painter: QPainter, rect: QRect) -> None:
        # Opacity is applied by the overlay widget reading self.opacity.
        pass


# ---------------------------------------------------------------------------
# Classic — static red pill
# ---------------------------------------------------------------------------

class ClassicErrorAnimation(BaseAnimation):
    """No animation — static colored pill (original behavior)."""

    layout_mode: Literal["full"] = "full"

    def start(self, widget: QWidget) -> None:
        pass

    def stop(self) -> None:
        pass

    def paint(self, painter: QPainter, rect: QRect) -> None:
        pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register(OverlayState.ERROR, "shake", ShakeAnimation, "Shake")
register(OverlayState.ERROR, "xmark_draw", XMarkDrawAnimation, "X-Mark Draw")
register(OverlayState.ERROR, "pulsing_red", PulsingRedAnimation, "Pulsing Red")
register(OverlayState.ERROR, "classic", ClassicErrorAnimation, "Classic")
