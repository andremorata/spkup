from __future__ import annotations

import logging

import numpy as np
import sounddevice

_log = logging.getLogger(__name__)

_SAMPLE_RATE = 44100
_AMPLITUDE = 0.4
_FADE_DURATION_S = 0.005

START_CUE_DURATION_MS: int = 350


def _apply_fade_envelope(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    fade_samples = min(int(round(_FADE_DURATION_S * sample_rate)), len(samples) // 2)
    if fade_samples <= 0:
        return np.ascontiguousarray(samples.astype(np.float32, copy=False))

    envelope = np.ones(len(samples), dtype=np.float32)
    envelope[:fade_samples] = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    envelope[-fade_samples:] = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    return np.ascontiguousarray((samples * envelope).astype(np.float32, copy=False))


def _generate_tone(
    freq: float, duration_s: float, sample_rate: int = _SAMPLE_RATE
) -> np.ndarray:
    sample_count = max(1, int(round(duration_s * sample_rate)))
    times = np.arange(sample_count, dtype=np.float64) / sample_rate
    samples = _AMPLITUDE * np.sin(2.0 * np.pi * float(freq) * times)
    return _apply_fade_envelope(samples, sample_rate)


def _generate_sweep(
    start_freq: float,
    end_freq: float,
    duration_s: float,
    sample_rate: int = _SAMPLE_RATE,
) -> np.ndarray:
    sample_count = max(1, int(round(duration_s * sample_rate)))
    times = np.arange(sample_count, dtype=np.float64) / sample_rate
    sweep_rate = (float(end_freq) - float(start_freq)) / duration_s
    phase = 2.0 * np.pi * (
        float(start_freq) * times + 0.5 * sweep_rate * np.square(times)
    )
    samples = _AMPLITUDE * np.sin(phase)
    return _apply_fade_envelope(samples, sample_rate)


def _silence(duration_s: float, sample_rate: int = _SAMPLE_RATE) -> np.ndarray:
    sample_count = max(0, int(round(duration_s * sample_rate)))
    return np.zeros(sample_count, dtype=np.float32)


start = np.ascontiguousarray(
    np.concatenate(
        (
            _generate_sweep(100.0, 1200.0, 0.350),
        )
    ).astype(np.float32, copy=False)
)
transcribing = np.ascontiguousarray(
    np.concatenate(
        (
            _generate_sweep(1200.0, 100.0, 0.150),
        )
    ).astype(np.float32, copy=False)
)
done = np.ascontiguousarray(
    np.concatenate(
        (
            _generate_tone(880.0, 0.090),
            _generate_tone(1108.0, 0.120),
        )
    ).astype(np.float32, copy=False)
)

_CUES = {
    "start": start,
    "transcribing": transcribing,
    "done": done,
}

try:
    _device_info = sounddevice.query_devices(kind="output")
    OUTPUT_LATENCY_MS: int = int(_device_info["default_low_output_latency"] * 1000)
except Exception:
    OUTPUT_LATENCY_MS = 50


def play_cue(name: str, blocking: bool = False) -> None:
    cue = _CUES.get(name)
    if cue is None:
        _log.warning("Unknown sound cue: %s", name)
        return

    try:
        sounddevice.play(cue, samplerate=_SAMPLE_RATE, blocking=blocking)
    except sounddevice.PortAudioError as exc:
        _log.warning("Skipping sound cue '%s' due to PortAudio error: %s", name, exc)


__all__ = ["OUTPUT_LATENCY_MS", "START_CUE_DURATION_MS", "done", "play_cue", "start", "transcribing"]
