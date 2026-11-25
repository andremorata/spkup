"""Regenerate the spkup sound cues as WAV files.

Usage:
    python scripts/make_sounds.py src/spkup/resources/sounds

Each cue is a few soft bell-like notes: a sine with two quieter overtones,
a short raised-cosine attack, and an exponential decay (higher overtones die
faster). Peaks sit around -12 dBFS so the cues stay quiet next to other audio.
"""
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 44100
PEAK = 0.25


def note(freq: float, tau: float, length: float) -> np.ndarray:
    t = np.arange(int(length * RATE)) / RATE
    partials = (
        np.sin(2 * np.pi * freq * t) * np.exp(-t / tau)
        + 0.22 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t / (tau * 0.5))
        + 0.06 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t / (tau * 0.3))
    )
    attack = int(0.004 * RATE)
    partials[:attack] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, attack))
    return partials


def sequence(notes: list[tuple[float, float, float, float]], length: float) -> np.ndarray:
    """notes: (start_s, freq_hz, tau_s, gain)."""
    out = np.zeros(int(length * RATE))
    for start, freq, tau, gain in notes:
        i = int(start * RATE)
        n = note(freq, tau, length - start)
        out[i:i + len(n)] += gain * n
    fade = int(0.010 * RATE)  # guarantee silence at the end, no click
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / np.max(np.abs(out)) * PEAK


D5, FS5, A5, D6 = 587.33, 739.99, 880.0, 1174.66
CUES = {
    # rising fifth: "listening"
    "start": sequence([(0.0, D5, 0.07, 0.8), (0.06, A5, 0.09, 1.0)], 0.26),
    # falling fifth, softer: "got it"
    "transcribing": sequence([(0.0, A5, 0.06, 0.9), (0.055, D5, 0.08, 0.8)], 0.22) * 0.7,
    # bright open chime with a longer tail: "copied"
    "done": sequence([(0.0, FS5, 0.12, 0.7), (0.05, A5, 0.14, 0.8), (0.10, D6, 0.2, 0.9)], 0.6),
}

out_dir = Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)
for name, samples in CUES.items():
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(out_dir / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    print(f"{name}.wav  {len(samples) / RATE * 1000:.0f} ms")
