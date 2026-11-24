import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from spkup.recorder import AudioRecorder, rms_to_level


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


def test_set_device_is_used_on_next_start():
    """set_device() updates the device passed to the next InputStream."""
    recorder = AudioRecorder()
    recorder.set_device(7)

    fake_stream = MagicMock()
    with patch(
        "spkup.recorder.sounddevice.InputStream", return_value=fake_stream
    ) as mk:
        recorder.start()
        recorder.stop()

    assert mk.call_args.kwargs["device"] == 7


def test_set_device_none_restores_default():
    """set_device(None) means 'system default' — passed straight to sounddevice."""
    recorder = AudioRecorder(device=3)
    recorder.set_device(None)

    fake_stream = MagicMock()
    with patch(
        "spkup.recorder.sounddevice.InputStream", return_value=fake_stream
    ) as mk:
        recorder.start()
        recorder.stop()

    assert mk.call_args.kwargs["device"] is None


def test_set_max_seconds_updates_next_safety_timeout():
    recorder = AudioRecorder(max_seconds=120)
    recorder.set_max_seconds(45)

    fake_stream = MagicMock()
    with patch("spkup.recorder.sounddevice.InputStream", return_value=fake_stream):
        recorder.start()

    assert recorder._timer.interval() == 45000


def test_rms_to_level_maps_db_range_to_unit_interval():
    assert rms_to_level(0.0) == 0.0
    assert rms_to_level(0.001) == 0.0  # -60 dBFS: room noise stays flat
    assert rms_to_level(1.0) == 1.0
    assert 0.3 < rms_to_level(0.03) < 0.8  # normal speech lands mid-scale
    assert rms_to_level(0.01) < rms_to_level(0.05)


def test_level_tracks_callbacks_and_resets_on_stop():
    fake_stream = MagicMock()
    with patch("spkup.recorder.sounddevice.InputStream", return_value=fake_stream):
        recorder = AudioRecorder()
        recorder.start()
        assert recorder.level() == 0.0

        recorder._audio_callback(np.full((512, 1), 0.1, dtype=np.float32), 512, None, None)
        assert recorder.level() > 0.5

        recorder.stop()
    assert recorder.level() == 0.0
