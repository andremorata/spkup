"""Overlay animation registry and helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from spkup.animations.base import BaseAnimation
from spkup.overlay import OverlayState

if TYPE_CHECKING:
    pass

# Populated by each state module at import time via ``register``.
ANIMATION_REGISTRY: dict[tuple[OverlayState, str], type[BaseAnimation]] = {}

# Human-readable display names for the settings UI.
ANIMATION_NAMES: dict[tuple[OverlayState, str], str] = {}


def register(
    state: OverlayState,
    key: str,
    cls: type[BaseAnimation],
    display_name: str,
) -> None:
    """Register an animation class for a given overlay state and key."""
    ANIMATION_REGISTRY[(state, key)] = cls
    ANIMATION_NAMES[(state, key)] = display_name


def get_animation(state: OverlayState, key: str) -> BaseAnimation:
    """Instantiate the animation for *state* / *key*.

    Falls back to the ``"classic"`` variant for the state if *key* is unknown.
    """
    cls = ANIMATION_REGISTRY.get((state, key))
    if cls is None:
        cls = ANIMATION_REGISTRY.get((state, "classic"))
    if cls is None:
        raise KeyError(f"No animation registered for {state!r}, key={key!r}")
    return cls()


def get_keys_for_state(state: OverlayState) -> list[str]:
    """Return the registered animation keys for *state* in insertion order."""
    return [k for (s, k) in ANIMATION_REGISTRY if s == state]


def get_display_name(state: OverlayState, key: str) -> str:
    """Return the human-readable name for an animation, or the key itself."""
    return ANIMATION_NAMES.get((state, key), key)


# Import state modules so they self-register. Order matters for combo display.
import spkup.animations.recording as _rec  # noqa: E402, F401
import spkup.animations.transcribing as _trans  # noqa: E402, F401
import spkup.animations.done as _done  # noqa: E402, F401
import spkup.animations.error as _err  # noqa: E402, F401

__all__ = [
    "BaseAnimation",
    "ANIMATION_REGISTRY",
    "ANIMATION_NAMES",
    "register",
    "get_animation",
    "get_keys_for_state",
    "get_display_name",
]
