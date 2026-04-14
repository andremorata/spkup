from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from PyQt6.QtCore import QRect
    from PyQt6.QtGui import QPainter
    from PyQt6.QtWidgets import QWidget


class BaseAnimation(ABC):
    """Abstract base for overlay animations.

    Each animation manages its own timers / property-animations internally.
    The overlay widget calls *start*, *stop*, *paint*, and *cleanup* at the
    appropriate moments.
    """

    @property
    @abstractmethod
    def layout_mode(self) -> Literal["icon", "full"]:
        """Return ``"icon"`` for left-zone animations or ``"full"`` for
        whole-pill animations."""

    @abstractmethod
    def start(self, widget: QWidget) -> None:
        """Begin the animation, using *widget* for ``update()`` scheduling."""

    @abstractmethod
    def stop(self) -> None:
        """Halt all timers / property-animations."""

    @abstractmethod
    def paint(self, painter: QPainter, rect: QRect) -> None:
        """Draw the current animation frame.

        *rect* is either the icon zone (~36×36 px) for ``layout_mode="icon"``
        or the full pill rect for ``layout_mode="full"``.
        """

    def cleanup(self) -> None:
        """Release resources.  Default implementation calls :meth:`stop`."""
        self.stop()
