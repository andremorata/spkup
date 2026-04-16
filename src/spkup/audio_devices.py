"""Input-device enumeration + spec resolution for the microphone picker.

A device **spec** is a `{"name": str, "hostapi": str}` dict or `None`.
`None` means "system default". The spec is persisted in `config.json`.
Resolving a spec to a PortAudio index happens at recording-start time so
hotplug/reorder does not invalidate the config.

`list_input_devices()` returns **WASAPI devices only**. PortAudio's WASAPI
hostapi maps 1-to-1 with the Windows Sound Settings microphone list, so this
produces exactly the same set of entries the user sees in Windows — no
duplicates from MME / WDM-KS / DirectSound.

`resolve_device()` falls back to the full raw device list so specs saved
before this filter was introduced still resolve correctly.
"""
from __future__ import annotations

import logging
from typing import Any, cast

import sounddevice

_log = logging.getLogger(__name__)

_PREFERRED_HOSTAPI = "Windows WASAPI"


def _hostapi_name(hostapi_index: int) -> str:
    try:
        hostapis = cast(list[dict], sounddevice.query_hostapis())
        return str(hostapis[hostapi_index].get("name", f"hostapi#{hostapi_index}"))
    except Exception:
        return f"hostapi#{hostapi_index}"


def _all_input_devices() -> list[dict[str, Any]]:
    """Return every input-capable PortAudio device, all hostapis included."""
    try:
        devices = cast(list[dict], sounddevice.query_devices())
    except Exception as exc:
        _log.warning("Could not query audio devices: %s", exc)
        return []

    try:
        default_input_index = sounddevice.default.device[0]
    except Exception:
        default_input_index = -1

    result: list[dict[str, Any]] = []
    for idx, dev in enumerate(devices):
        if int(dev.get("max_input_channels", 0) or 0) <= 0:
            continue
        result.append(
            {
                "index": idx,
                "name": str(dev.get("name", f"device#{idx}")),
                "hostapi": _hostapi_name(int(dev.get("hostapi", 0))),
                "channels": int(dev["max_input_channels"]),
                "is_default": idx == default_input_index,
            }
        )
    return result


def list_input_devices() -> list[dict[str, Any]]:
    """Return input devices via the Windows WASAPI hostapi only.

    This matches the Windows Sound Settings microphone list exactly — one
    entry per physical endpoint, no MME/WDM-KS/DirectSound duplicates.

    Falls back to all input devices if no WASAPI devices are found (e.g.
    non-Windows platform or unusual PortAudio build).

    Each item: {"index": int, "name": str, "hostapi": str,
                "channels": int, "is_default": bool}
    """
    all_devs = _all_input_devices()
    wasapi = [d for d in all_devs if d["hostapi"] == _PREFERRED_HOSTAPI]
    return wasapi if wasapi else all_devs


def resolve_device(spec: dict | None) -> int | None:
    """Convert a stored spec to a PortAudio index.

    - `None` → `None` (system default, same as today).
    - Matching `(name, hostapi)` found → its index.
    - No match → `None` (fall back to system default) and log a warning.
    """
    if spec is None:
        return None

    want_name = spec.get("name")
    want_hostapi = spec.get("hostapi")
    if not want_name:
        return None

    # Search the full raw list so specs saved before deduplication was added
    # (e.g. with hostapi="MME") still resolve correctly.
    for dev in _all_input_devices():
        if dev["name"] == want_name and dev["hostapi"] == want_hostapi:
            return int(dev["index"])

    _log.warning(
        "Configured input device not found: name=%r hostapi=%r — falling back to system default",
        want_name, want_hostapi,
    )
    return None


def describe(spec: dict | None) -> str:
    """Human-readable label for a spec. Used in logs and menu checkmarks."""
    if spec is None:
        return "System default"
    name = spec.get("name") or "(unknown)"
    hostapi = spec.get("hostapi")
    return f"{name} ({hostapi})" if hostapi else str(name)


def spec_from_device(device: dict) -> dict:
    """Build a persistable spec from a device dict returned by list_input_devices()."""
    return {"name": device["name"], "hostapi": device["hostapi"]}
