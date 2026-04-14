"""Transcribing-state animations."""

from __future__ import annotations

import math
import time
from typing import Literal

from PyQt6.QtCore import QRect, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from spkup.animations.base import BaseAnimation
from spkup.animations import register
from spkup.overlay import OverlayState


# ---------------------------------------------------------------------------
# Spinning Arc — partial arc rotating continuously
# ---------------------------------------------------------------------------

class SpinningArcAnimation(BaseAnimation):
    """Rotating partial arc — universal loading spinner."""

    layout_mode: Literal["icon"] = "icon"

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
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
        padding = 5
        side = min(rect.width(), rect.height()) - 2 * padding
        cx = rect.center().x()
        cy = rect.center().y()
        arc_rect = QRect(cx - side // 2, cy - side // 2, side, side)

        angle_deg = (t * 270) % 360  # degrees, ~3/4 turn per sec
        start_angle = int(angle_deg * 16)
        span_angle = 90 * 16  # 90-degree arc

        pen = QPen(QColor("#ffffff"), 2.5)
        pen.setCapStyle(pen.capStyle().RoundCap)  # type: ignore[arg-type]
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawArc(arc_rect, start_angle, span_angle)


# ---------------------------------------------------------------------------
# Bouncing Dots — 3 dots bouncing with phase delays
# ---------------------------------------------------------------------------

class BouncingDotsAnimation(BaseAnimation):
    """Three dots bouncing up and down — typing / thinking indicator."""

    layout_mode: Literal["icon"] = "icon"
    _NUM_DOTS = 3

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
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
        radius = 3
        gap = 10
        total_w = self._NUM_DOTS * 2 * radius + (self._NUM_DOTS - 1) * gap
        start_x = rect.center().x() - total_w // 2 + radius
        cy = rect.center().y()
        amplitude = (rect.height() - 2 * radius) * 0.3

        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.setBrush(QColor("#ffffff"))

        for i in range(self._NUM_DOTS):
            phase = i * 0.35  # stagger
            bounce = abs(math.sin((t * 3.0) + phase * math.pi))
            x = start_x + i * (2 * radius + gap)
            y = cy - bounce * amplitude
            painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)


# ---------------------------------------------------------------------------
# Progress Sweep — horizontal bar sweeping left→right
# ---------------------------------------------------------------------------

class ProgressSweepAnimation(BaseAnimation):
    """Indeterminate progress bar — highlight sweeps across the pill."""

    layout_mode: Literal["full"] = "full"

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
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
        cycle = 1.5  # seconds
        progress = (t % cycle) / cycle
        bar_w = int(rect.width() * 0.35)
        x = rect.left() + int((rect.width() + bar_w) * progress) - bar_w
        color = QColor(255, 255, 255, 50)
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.setBrush(color)
        painter.drawRect(x, rect.top(), bar_w, rect.height())


# ---------------------------------------------------------------------------
# Classic — static pill, no animation
# ---------------------------------------------------------------------------

class ClassicTranscribingAnimation(BaseAnimation):
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

register(OverlayState.TRANSCRIBING, "spinning_arc", SpinningArcAnimation, "Spinning Arc")
register(OverlayState.TRANSCRIBING, "bouncing_dots", BouncingDotsAnimation, "Bouncing Dots")
register(OverlayState.TRANSCRIBING, "progress_sweep", ProgressSweepAnimation, "Progress Sweep")
register(OverlayState.TRANSCRIBING, "classic", ClassicTranscribingAnimation, "Classic")
