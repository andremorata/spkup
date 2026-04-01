from __future__ import annotations

import logging

import numpy as np
import sounddevice
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_log = logging.getLogger(__name__)


class AudioRecorder(QObject):
    recording_finished = pyqtSignal(object)
    recording_error = pyqtSignal(str)

    def __init__(self, device=None, max_seconds=120):
        super().__init__()
        self._device = device
        self._max_seconds = max_seconds
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_safety_timeout)

    def start(self):
        if self._stream is not None:
            return

        self._chunks = []

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

    def _audio_callback(self, indata, frames, time, status):
        self._chunks.append(indata[:, 0].copy())

    def stop(self):
        if self._stream is None:
            return

        self._timer.stop()
        self._stream.stop()
        self._stream.close()
        self._stream = None

        if self._chunks:
            audio = np.concatenate(self._chunks)
        else:
            audio = np.array([], dtype=np.float32)

        self.recording_finished.emit(audio)
        _log.debug("Recording finished: %d samples", len(audio))

    def _on_safety_timeout(self):
        self.stop()
