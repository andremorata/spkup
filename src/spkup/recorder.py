from __future__ import annotations

import logging
import math

import numpy as np
import sounddevice
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_log = logging.getLogger(__name__)

# Calibration for the overlay meter: quiet-room noise sits below the floor,
# normal speech on a laptop mic lands around -35..-20 dBFS.
_LEVEL_FLOOR_DB = -50.0
_LEVEL_CEIL_DB = -12.0


def rms_to_level(rms: float) -> float:
    """Map a chunk RMS amplitude to a 0..1 loudness on a dB scale."""
    if rms <= 0.0:
        return 0.0
    db = 20.0 * math.log10(rms)
    return min(1.0, max(0.0, (db - _LEVEL_FLOOR_DB) / (_LEVEL_CEIL_DB - _LEVEL_FLOOR_DB)))


class AudioRecorder(QObject):
    recording_finished = pyqtSignal(object)
    recording_error = pyqtSignal(str)

    def __init__(self, device=None, max_seconds=120):
        super().__init__()
        self._device = device
        self._max_seconds = max_seconds
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._level = 0.0
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_safety_timeout)

    def set_device(self, device) -> None:
        """Select the PortAudio input device for the next recording.

        Passing `None` restores the system default. sounddevice does not
        support hot-swapping a running stream, so the change applies on
        the next `start()` call.
        """
        self._device = device

    def set_max_seconds(self, max_seconds: int) -> None:
        """Update the safety cutoff used for the next recording session."""
        self._max_seconds = max(1, int(max_seconds))

    def start(self):
        if self._stream is not None:
            return

        self._chunks = []
        self._level = 0.0

        try:
            self._stream = sounddevice.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
                device=self._device,
            )
            self._stream.start()
            self._timer.start(self._max_seconds * 1000)
            _log.debug("Recording started on device %s", self._device)
        except sounddevice.PortAudioError as exc:
            _log.error("PortAudio error opening microphone: %s", exc)
            self.recording_error.emit(f"Could not open microphone: {exc}")
            self._stream = None
        except Exception as exc:
            _log.error("Unexpected error opening microphone: %s", exc)
            self.recording_error.emit(str(exc))
            self._stream = None

    def level(self) -> float:
        """Latest input loudness in 0..1; safe to poll from the Qt thread."""
        return self._level

    def _audio_callback(self, indata, frames, time, status):
        # Runs on the PortAudio thread: plain attribute writes only, no Qt calls.
        samples = indata[:, 0].copy()
        self._chunks.append(samples)
        if samples.size:
            self._level = rms_to_level(float(np.sqrt(np.mean(np.square(samples)))))

    def stop(self):
        if self._stream is None:
            return

        self._timer.stop()
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._level = 0.0

        if self._chunks:
            audio = np.concatenate(self._chunks)
        else:
            audio = np.array([], dtype=np.float32)

        self.recording_finished.emit(audio)
        _log.debug("Recording finished: %d samples", len(audio))

    def _on_safety_timeout(self):
        self.stop()
