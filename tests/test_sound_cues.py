from __future__ import annotations

import logging
from unittest.mock import patch

import numpy as np
import sounddevice

import spkup.sound_cues as sound_cues


def test_generate_tone_returns_faded_float32_array() -> None:
    tone = sound_cues._generate_tone(700.0, 0.070)

    assert tone.dtype == np.float32
    assert tone.ndim == 1
    assert np.isclose(float(tone[0]), 0.0)
    assert np.isclose(float(tone[-1]), 0.0)
    assert np.max(np.abs(tone)) <= 0.4 + 1e-6


def test_precomputed_cues_have_expected_shape_and_length() -> None:
    assert sound_cues.START_CUE_DURATION_MS == 350

    assert sound_cues.start.dtype == np.float32
    assert sound_cues.transcribing.dtype == np.float32
    assert sound_cues.done.dtype == np.float32

    assert len(sound_cues.start) == int(round(0.120 * 44100)) + int(round(0.230 * 44100))
    assert len(sound_cues.transcribing) == int(round(0.150 * 44100))
    assert len(sound_cues.done) == int(round(0.090 * 44100)) + int(
        round(0.120 * 44100)
    )


def test_play_cue_plays_known_cue_non_blocking() -> None:
    with patch("spkup.sound_cues.sounddevice.play") as play:
        sound_cues.play_cue("start")

    play.assert_called_once_with(sound_cues.start, samplerate=44100, blocking=False)


def test_play_cue_logs_warning_for_unknown_name(caplog) -> None:
    with patch("spkup.sound_cues.sounddevice.play") as play, caplog.at_level(
        logging.WARNING
    ):
        sound_cues.play_cue("missing")

    play.assert_not_called()
    assert "Unknown sound cue: missing" in caplog.text


def test_play_cue_swallows_portaudio_error(caplog) -> None:
    error = sounddevice.PortAudioError("device unavailable")

    with patch(
        "spkup.sound_cues.sounddevice.play", side_effect=error
    ) as play, caplog.at_level(logging.WARNING):
        sound_cues.play_cue("done")

    play.assert_called_once_with(sound_cues.done, samplerate=44100, blocking=False)
    assert "Skipping sound cue 'done' due to PortAudio error" in caplog.text
