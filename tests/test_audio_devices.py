"""Tests for spkup.audio_devices."""
from __future__ import annotations

from spkup import audio_devices


_FAKE_HOSTAPIS = [
    {"name": "MME"},             # index 0
    {"name": "Windows WASAPI"},  # index 1
]

# Typical Windows PortAudio layout: each physical mic appears under MME and
# WASAPI; output devices have max_input_channels == 0.
_FAKE_DEVICES = [
    # Built-in mic — MME (index 0)
    {"name": "Microphone (Realtek)", "hostapi": 0, "max_input_channels": 2},
    # Built-in mic — WASAPI (index 1)
    {"name": "Microphone (Realtek)", "hostapi": 1, "max_input_channels": 2},
    # Output-only speaker — must be excluded
    {"name": "Speakers (Realtek)", "hostapi": 1, "max_input_channels": 0},
    # USB headset — WASAPI only (index 3)
    {"name": "USB Headset Mic", "hostapi": 1, "max_input_channels": 1},
]


def _apply_mocks(monkeypatch, default_input_index: int = 3) -> None:
    monkeypatch.setattr(
        audio_devices.sounddevice, "query_devices", lambda: list(_FAKE_DEVICES)
    )
    monkeypatch.setattr(
        audio_devices.sounddevice, "query_hostapis", lambda: list(_FAKE_HOSTAPIS)
    )

    class _Default:
        device = (default_input_index, 0)

    monkeypatch.setattr(audio_devices.sounddevice, "default", _Default())


# ---------------------------------------------------------------------------
# list_input_devices — WASAPI-only filter
# ---------------------------------------------------------------------------

def test_list_input_devices_wasapi_only(monkeypatch) -> None:
    """Only WASAPI devices are returned — MME duplicates are excluded."""
    _apply_mocks(monkeypatch)
    devices = audio_devices.list_input_devices()
    assert all(d["hostapi"] == "Windows WASAPI" for d in devices)
    names = [d["name"] for d in devices]
    assert names == ["Microphone (Realtek)", "USB Headset Mic"]


def test_list_input_devices_filters_output_only(monkeypatch) -> None:
    """Devices with max_input_channels == 0 are excluded."""
    _apply_mocks(monkeypatch)
    names = [d["name"] for d in audio_devices.list_input_devices()]
    assert "Speakers (Realtek)" not in names


def test_list_input_devices_marks_default(monkeypatch) -> None:
    """The device whose PortAudio index matches the system default is flagged."""
    _apply_mocks(monkeypatch, default_input_index=3)
    devices = audio_devices.list_input_devices()
    usb = next(d for d in devices if d["name"] == "USB Headset Mic")
    realtek = next(d for d in devices if d["name"] == "Microphone (Realtek)")
    assert usb["is_default"] is True
    assert realtek["is_default"] is False


def test_list_input_devices_fallback_when_no_wasapi(monkeypatch) -> None:
    """When no WASAPI devices exist, fall back to all input devices."""
    mme_only = [
        {"name": "Microphone", "hostapi": 0, "max_input_channels": 1},
    ]
    monkeypatch.setattr(
        audio_devices.sounddevice, "query_devices", lambda: mme_only
    )
    monkeypatch.setattr(
        audio_devices.sounddevice, "query_hostapis", lambda: [{"name": "MME"}]
    )

    class _Default:
        device = (0, 0)

    monkeypatch.setattr(audio_devices.sounddevice, "default", _Default())

    devices = audio_devices.list_input_devices()
    assert len(devices) == 1
    assert devices[0]["name"] == "Microphone"


def test_list_input_devices_handles_query_failure(monkeypatch) -> None:
    """If sounddevice raises, list_input_devices returns an empty list."""
    def _raise():
        raise RuntimeError("PortAudio not initialized")

    monkeypatch.setattr(audio_devices.sounddevice, "query_devices", _raise)
    assert audio_devices.list_input_devices() == []


# ---------------------------------------------------------------------------
# resolve_device — searches all hostapis (backward compat)
# ---------------------------------------------------------------------------

def test_resolve_device_none_passthrough(monkeypatch) -> None:
    _apply_mocks(monkeypatch)
    assert audio_devices.resolve_device(None) is None


def test_resolve_device_wasapi_spec(monkeypatch) -> None:
    """A WASAPI spec resolves to the correct PortAudio index."""
    _apply_mocks(monkeypatch)
    idx = audio_devices.resolve_device(
        {"name": "USB Headset Mic", "hostapi": "Windows WASAPI"}
    )
    assert idx == 3


def test_resolve_device_legacy_mme_spec(monkeypatch) -> None:
    """A spec saved with hostapi='MME' (before WASAPI filter) still resolves."""
    _apply_mocks(monkeypatch)
    idx = audio_devices.resolve_device(
        {"name": "Microphone (Realtek)", "hostapi": "MME"}
    )
    assert idx == 0


def test_resolve_device_missing_falls_back_to_none(monkeypatch) -> None:
    _apply_mocks(monkeypatch)
    assert audio_devices.resolve_device(
        {"name": "Ghost Mic", "hostapi": "Windows WASAPI"}
    ) is None


def test_resolve_device_empty_name_returns_none(monkeypatch) -> None:
    _apply_mocks(monkeypatch)
    assert audio_devices.resolve_device({"name": "", "hostapi": "MME"}) is None


# ---------------------------------------------------------------------------
# describe / spec_from_device
# ---------------------------------------------------------------------------

def test_describe_none() -> None:
    assert audio_devices.describe(None) == "System default"


def test_describe_spec() -> None:
    spec = {"name": "USB Headset Mic", "hostapi": "Windows WASAPI"}
    assert audio_devices.describe(spec) == "USB Headset Mic (Windows WASAPI)"


def test_spec_from_device() -> None:
    dev = {
        "index": 3,
        "name": "USB Headset Mic",
        "hostapi": "Windows WASAPI",
        "channels": 1,
        "is_default": True,
    }
    assert audio_devices.spec_from_device(dev) == {
        "name": "USB Headset Mic",
        "hostapi": "Windows WASAPI",
    }
