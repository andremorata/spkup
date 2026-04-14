"""Recording-state animations."""

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
# Equalizer Bars — 5 vertical bars oscillating at different phases
# ---------------------------------------------------------------------------

class EqualizerBarsAnimation(BaseAnimation):
    """Five bouncing vertical bars — classic audio equalizer look."""

    layout_mode: Literal["icon"] = "icon"
    _NUM_BARS = 5

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
        self._widget: QWidget | None = None
        self._t0 = 0.0
        self._phases = [i * (2.0 * math.pi / self._NUM_BARS) for i in range(self._NUM_BARS)]

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
        padding = 4
        bar_area_w = rect.width() - 2 * padding
        bar_w = max(2, int(bar_area_w / (self._NUM_BARS * 2 - 1)))
        gap = max(1, (bar_area_w - bar_w * self._NUM_BARS) // max(1, self._NUM_BARS - 1))
        max_h = rect.height() - 2 * padding

        painter.setPen(QPen(QColor("#ffffff"), 0))
        painter.setBrush(QColor("#ffffff"))

        for i in range(self._NUM_BARS):
            frac = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 4.0 + self._phases[i]))
            h = max(3, int(frac * max_h))
            x = rect.left() + padding + i * (bar_w + gap)
            y = rect.top() + padding + (max_h - h)
            painter.drawRoundedRect(x, y, bar_w, h, 1, 1)


# ---------------------------------------------------------------------------
# Pulse Ring — concentric circle radiates outward and fades
# ---------------------------------------------------------------------------

class PulseRingAnimation(BaseAnimation):
    """Expanding/fading ring — sonar / listening effect."""

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
        cycle = 1.6  # seconds per ring
        progress = (t % cycle) / cycle  # 0→1
        cx = rect.left() + 14
        cy = rect.center().y()
        max_r = rect.height() * 0.45
        r = progress * max_r
        alpha = max(0, int(200 * (1.0 - progress)))
        color = QColor(255, 255, 255, alpha)
        pen = QPen(color, 2.0)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Second ring offset by half cycle
        progress2 = ((t + cycle / 2) % cycle) / cycle
        r2 = progress2 * max_r
        alpha2 = max(0, int(200 * (1.0 - progress2)))
        color2 = QColor(255, 255, 255, alpha2)
        pen2 = QPen(color2, 2.0)
        painter.setPen(pen2)
        painter.drawEllipse(int(cx - r2), int(cy - r2), int(2 * r2), int(2 * r2))


# ---------------------------------------------------------------------------
# Waveform — oscillating sine wave polyline
# ---------------------------------------------------------------------------

class WaveformAnimation(BaseAnimation):
    """Live audio waveform — sine wave in icon zone."""

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
        padding = 3
        cy = rect.center().y()
        amp = (rect.height() - 2 * padding) * 0.4
        w = rect.width() - 2 * padding
        steps = max(4, w)

        path = QPainterPath()
        for i in range(steps):
            frac = i / max(1, steps - 1)
            x = rect.left() + padding + frac * w
            y = cy + amp * math.sin(frac * 3.0 * math.pi + t * 5.0) * (0.6 + 0.4 * math.sin(t * 2.5 + frac * math.pi))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        pen = QPen(QColor("#ffffff"), 2.0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawPath(path)


# ---------------------------------------------------------------------------
# Classic — the original opacity pulse (ported from OverlayWidget)
# ---------------------------------------------------------------------------

class ClassicRecordingAnimation(BaseAnimation):
    """Original opacity-pulse animation (whole-pill fade in/out)."""

    layout_mode: Literal["full"] = "full"

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
        self._widget: QWidget | None = None
        self._t0 = 0.0
        self.opacity = 1.0

    def start(self, widget: QWidget) -> None:
        self._widget = widget
        self._t0 = time.monotonic()
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        t = time.monotonic() - self._t0
        # 1800 ms cycle, dip to 0.45
        cycle = 1.8
        phase = (t % cycle) / cycle
        self.opacity = 0.45 + 0.55 * (0.5 + 0.5 * math.cos(phase * 2 * math.pi))
        if self._widget is not None:
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
        # The overlay reads self.opacity and sets QPainter opacity externally.
        pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register(OverlayState.RECORDING, "equalizer_bars", EqualizerBarsAnimation, "Equalizer Bars")
register(OverlayState.RECORDING, "pulse_ring", PulseRingAnimation, "Pulse Ring")
register(OverlayState.RECORDING, "waveform", WaveformAnimation, "Waveform")
register(OverlayState.RECORDING, "classic", ClassicRecordingAnimation, "Classic")
