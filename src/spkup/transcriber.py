from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from spkup.config import AppConfig
from spkup.model_manager import ModelNotFoundError, is_downloaded, model_path


class _TranscriptionWorker(QThread):
    """Transcribes a float32 audio array in a background thread via faster-whisper."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        audio: np.ndarray,
        model_size: str,
        device: str,
        compute_type: str,
    ) -> None:
        super().__init__()
        self._audio = audio
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type

    def run(self) -> None:
        try:
            if not is_downloaded(self._model_size):
                raise ModelNotFoundError(
                    f"Model '{self._model_size}' is not downloaded. "
                    "Open Settings to download it."
                )

            from faster_whisper import WhisperModel

            mp = str(model_path(self._model_size))
            model = WhisperModel(
                mp,
                device=self._device,
                compute_type=self._compute_type,
            )
            segments, _ = model.transcribe(
                self._audio,
                language=None,
                vad_filter=True,
                beam_size=5,
            )
            text = " ".join(seg.text for seg in segments).strip()
            self.finished.emit(text)
        except Exception as exc:
            self.error.emit(str(exc))


class Transcriber(QObject):
    """Facade that accepts audio arrays and emits transcribed text.

    Busy-guards concurrent transcription requests — if a worker is already
    running, subsequent calls to ``transcribe()`` are silently discarded.
    """

    transcription_finished = pyqtSignal(str)
    transcription_error = pyqtSignal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._worker: _TranscriptionWorker | None = None

    def transcribe(self, audio: np.ndarray) -> None:
        """Start transcription; no-op if a transcription is already running."""
        if self._worker is not None and self._worker.isRunning():
            return

        self._worker = _TranscriptionWorker(
            audio,
            self._config.model_size,
            self._config.device,
            self._config.compute_type,
        )
        self._worker.finished.connect(self.transcription_finished)
        self._worker.error.connect(self.transcription_error)
        self._worker.finished.connect(lambda _: self._cleanup_worker())
        self._worker.error.connect(lambda _: self._cleanup_worker())
        self._worker.start()

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
