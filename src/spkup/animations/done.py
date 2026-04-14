"""Done-state animations."""

from __future__ import annotations

import math
import random
import time
from typing import Literal

from PyQt6.QtCore import QRect, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from spkup.animations.base import BaseAnimation
from spkup.animations import register
from spkup.overlay import OverlayState


# ---------------------------------------------------------------------------
# Checkmark Draw — animated ✓ drawn stroke-by-stroke
# ---------------------------------------------------------------------------

class CheckmarkDrawAnimation(BaseAnimation):
    """Animated checkmark drawn stroke-by-stroke in the icon zone."""

    layout_mode: Literal["icon"] = "icon"
    _DRAW_DURATION = 0.4  # seconds to complete the stroke

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

        pad = 6
        x0, y0 = rect.left() + pad, rect.center().y()
        x1, y1 = rect.left() + rect.width() * 0.38, rect.bottom() - pad
        x2, y2 = rect.right() - pad, rect.top() + pad

        # Two segments: (x0,y0)→(x1,y1) is ~40% of stroke, (x1,y1)→(x2,y2) is ~60%
        seg1_frac = 0.4
        path = QPainterPath()
        path.moveTo(x0, y0)

        if progress <= seg1_frac:
            f = progress / seg1_frac
            path.lineTo(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        else:
            path.lineTo(x1, y1)
            f = (progress - seg1_frac) / (1.0 - seg1_frac)
            path.lineTo(x1 + (x2 - x1) * f, y1 + (y2 - y1) * f)

        pen = QPen(QColor("#ffffff"), 3.0)
        pen.setCapStyle(pen.capStyle().RoundCap)  # type: ignore[arg-type]
        pen.setJoinStyle(pen.joinStyle().RoundJoin)  # type: ignore[arg-type]
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawPath(path)


# ---------------------------------------------------------------------------
# Flash Pop — pill scales up and flashes, then back to normal
# ---------------------------------------------------------------------------

class FlashPopAnimation(BaseAnimation):
    """Brief scale-up + bright flash — celebratory pop."""

    layout_mode: Literal["full"] = "full"
    _DURATION = 0.35  # seconds

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(16)
        self._widget: QWidget | None = None
        self._t0 = 0.0
        self.flash_alpha = 0

    def start(self, widget: QWidget) -> None:
        self._widget = widget
        self._t0 = time.monotonic()
        self.flash_alpha = 0
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
        self.flash_alpha = 0
        self._widget = None

    def paint(self, painter: QPainter, rect: QRect) -> None:
        t = time.monotonic() - self._t0
        progress = min(1.0, t / self._DURATION)

        # Flash overlay: sharp peak at ~30%, then fade
        if progress < 0.3:
            self.flash_alpha = int(120 * (progress / 0.3))
        else:
            self.flash_alpha = int(120 * (1.0 - (progress - 0.3) / 0.7))

        self.flash_alpha = max(0, min(255, self.flash_alpha))
        color = QColor(255, 255, 255, self.flash_alpha)
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 6, 6)


# ---------------------------------------------------------------------------
# Confetti Burst — particles sparkle/fade within pill bounds
# ---------------------------------------------------------------------------

class ConfettiBurstAnimation(BaseAnimation):
    """Micro-confetti sparkling within the pill — celebration effect."""

    layout_mode: Literal["full"] = "full"
    _NUM_PARTICLES = 12
    _DURATION = 1.2  # seconds

    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(30)
        self._widget: QWidget | None = None
        self._t0 = 0.0
        self._particles: list[dict] = []

    def start(self, widget: QWidget) -> None:
        self._widget = widget
        self._t0 = time.monotonic()
        self._particles = []
        rng = random.Random(42)  # deterministic seed for reproducibility
        for _ in range(self._NUM_PARTICLES):
            self._particles.append({
                "x": rng.random(),  # 0-1 normalized position
                "y": rng.random(),
                "vx": (rng.random() - 0.5) * 0.6,
                "vy": -(rng.random() * 0.5 + 0.2),  # upward bias
                "size": rng.randint(2, 5),
                "hue": rng.randint(0, 360),
                "delay": rng.random() * 0.15,
            })
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
        self._particles = []
        self._widget = None

    def paint(self, painter: QPainter, rect: QRect) -> None:
        t = time.monotonic() - self._t0
        painter.setPen(QPen(QColor(0, 0, 0, 0)))

        for p in self._particles:
            age = t - p["delay"]
            if age < 0:
                continue
            life_frac = age / self._DURATION
            if life_frac > 1.0:
                continue

            alpha = max(0, int(220 * (1.0 - life_frac)))
            x = (p["x"] + p["vx"] * age) % 1.0
            y = p["y"] + p["vy"] * age + 0.3 * age * age  # gravity
            y = max(0.0, min(1.0, y))

            px = rect.left() + int(x * rect.width())
            py = rect.top() + int(y * rect.height())
            s = p["size"]

            color = QColor.fromHsv(p["hue"], 200, 255, alpha)
            painter.setBrush(color)
            painter.drawEllipse(px - s // 2, py - s // 2, s, s)


# ---------------------------------------------------------------------------
# Classic — static green pill
# ---------------------------------------------------------------------------

class ClassicDoneAnimation(BaseAnimation):
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

register(OverlayState.DONE, "checkmark_draw", CheckmarkDrawAnimation, "Checkmark Draw")
register(OverlayState.DONE, "flash_pop", FlashPopAnimation, "Flash Pop")
register(OverlayState.DONE, "confetti_burst", ConfettiBurstAnimation, "Confetti Burst")
register(OverlayState.DONE, "classic", ClassicDoneAnimation, "Classic")
