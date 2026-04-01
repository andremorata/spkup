import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from spkup.recorder import AudioRecorder


def test_stop_before_start_is_safe():
    """stop() on a fresh recorder does not raise."""
    recorder = AudioRecorder()
    recorder.stop()  # must not raise


def test_recording_finished_emitted(monkeypatch):
    """start() then stop() emits recording_finished with a float32 array."""
    fake_stream = MagicMock()
    with patch("spkup.recorder.sounddevice.InputStream", return_value=fake_stream):
        recorder = AudioRecorder()

        received = []
        recorder.recording_finished.connect(lambda arr: received.append(arr))

        recorder.start()
        # Simulate two audio callbacks arriving
        chunk = np.ones((512, 1), dtype=np.float32)
        recorder._audio_callback(chunk, 512, None, None)
        recorder._audio_callback(chunk, 512, None, None)
        recorder.stop()

    assert len(received) == 1
    arr = received[0]
    assert arr.dtype == np.float32
    assert arr.ndim == 1
    assert len(arr) == 1024


def test_safety_timer_calls_stop():
    """_on_safety_timeout() terminates an active recording."""
    fake_stream = MagicMock()
    with patch("spkup.recorder.sounddevice.InputStream", return_value=fake_stream):
        recorder = AudioRecorder()

        received = []
        recorder.recording_finished.connect(lambda arr: received.append(arr))

        recorder.start()
        recorder._on_safety_timeout()

    assert len(received) == 1


def test_array_dtype_is_float32():
    """Emitted array is always float32 regardless of chunk count."""
    fake_stream = MagicMock()
    with patch("spkup.recorder.sounddevice.InputStream", return_value=fake_stream):
        recorder = AudioRecorder()

        received = []
        recorder.recording_finished.connect(lambda arr: received.append(arr))

        recorder.start()
        # No callbacks — empty recording
        recorder.stop()

    assert len(received) == 1
    assert received[0].dtype == np.float32
