"""Tests for the overlay animation registry and config integration."""

import json

import pytest

from spkup.animations import (
    ANIMATION_REGISTRY,
    ANIMATION_NAMES,
    get_animation,
    get_display_name,
    get_keys_for_state,
)
from spkup.animations.base import BaseAnimation
from spkup.config import AppConfig, load, save
from spkup.overlay import OverlayState


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------

_EXPECTED_STATES = [
    OverlayState.RECORDING,
    OverlayState.TRANSCRIBING,
    OverlayState.DONE,
    OverlayState.ERROR,
]


def test_registry_has_16_entries():
    assert len(ANIMATION_REGISTRY) == 16


@pytest.mark.parametrize("state", _EXPECTED_STATES)
def test_each_state_has_4_animations(state):
    keys = get_keys_for_state(state)
    assert len(keys) == 4, f"{state} has {len(keys)} keys: {keys}"


@pytest.mark.parametrize("state", _EXPECTED_STATES)
def test_each_state_has_classic_fallback(state):
    keys = get_keys_for_state(state)
    assert "classic" in keys


def test_all_registered_classes_subclass_base():
    for (state, key), cls in ANIMATION_REGISTRY.items():
        assert issubclass(cls, BaseAnimation), f"{cls} is not a BaseAnimation subclass"


def test_all_have_display_names():
    for (state, key) in ANIMATION_REGISTRY:
        name = get_display_name(state, key)
        assert isinstance(name, str) and len(name) > 0


# ---------------------------------------------------------------------------
# get_animation fallback
# ---------------------------------------------------------------------------

def test_get_animation_returns_instance():
    anim = get_animation(OverlayState.RECORDING, "equalizer_bars")
    assert isinstance(anim, BaseAnimation)


def test_get_animation_falls_back_to_classic():
    anim = get_animation(OverlayState.RECORDING, "nonexistent_key")
    # Should not raise — falls back to classic
    assert isinstance(anim, BaseAnimation)


def test_get_animation_raises_for_invalid_state():
    # OverlayState.HIDDEN has no registrations
    with pytest.raises(KeyError):
        get_animation(OverlayState.HIDDEN, "anything")


# ---------------------------------------------------------------------------
# Layout modes
# ---------------------------------------------------------------------------

def test_all_animations_have_valid_layout_mode():
    for (state, key), cls in ANIMATION_REGISTRY.items():
        instance = cls()
        assert instance.layout_mode in ("icon", "full"), (
            f"{cls.__name__}.layout_mode = {instance.layout_mode!r}"
        )


# ---------------------------------------------------------------------------
# Default animation keys in config
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "recording_animation": "equalizer_bars",
    "transcribing_animation": "spinning_arc",
    "done_animation": "checkmark_draw",
    "error_animation": "shake",
}


def test_appconfig_default_animation_keys():
    cfg = AppConfig()
    for field, expected in _DEFAULTS.items():
        assert getattr(cfg, field) == expected


def test_load_returns_default_animation_keys_when_missing(tmp_path, monkeypatch):
    """Old config files without animation keys should get defaults."""
    cfg_dir = tmp_path / "spkup"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    # Simulate an old config without animation fields
    data = {"hotkey": "f9", "model_size": "base"}
    cfg_path.write_text(json.dumps(data), encoding="utf-8")

    result = load()

    for field, expected in _DEFAULTS.items():
        assert getattr(result, field) == expected, f"{field} should be {expected!r}"


def test_animation_keys_round_trip(tmp_path, monkeypatch):
    """Animation keys survive save→load."""
    cfg_dir = tmp_path / "spkup"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    cfg = AppConfig(
        recording_animation="waveform",
        transcribing_animation="bouncing_dots",
        done_animation="confetti_burst",
        error_animation="pulsing_red",
    )
    save(cfg)
    loaded = load()

    assert loaded.recording_animation == "waveform"
    assert loaded.transcribing_animation == "bouncing_dots"
    assert loaded.done_animation == "confetti_burst"
    assert loaded.error_animation == "pulsing_red"


# ---------------------------------------------------------------------------
# Expected keys per state (guard against regressions)
# ---------------------------------------------------------------------------

def test_recording_keys():
    assert get_keys_for_state(OverlayState.RECORDING) == [
        "equalizer_bars", "pulse_ring", "waveform", "classic",
    ]


def test_transcribing_keys():
    assert get_keys_for_state(OverlayState.TRANSCRIBING) == [
        "spinning_arc", "bouncing_dots", "progress_sweep", "classic",
    ]


def test_done_keys():
    assert get_keys_for_state(OverlayState.DONE) == [
        "checkmark_draw", "flash_pop", "confetti_burst", "classic",
    ]


def test_error_keys():
    assert get_keys_for_state(OverlayState.ERROR) == [
        "shake", "xmark_draw", "pulsing_red", "classic",
    ]
