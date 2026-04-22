from __future__ import annotations

import logging
import time

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from spkup.config import AppConfig
from spkup.model_manager import ModelNotFoundError, is_downloaded, model_path

_log = logging.getLogger(__name__)


def _should_fallback_to_cpu(device: str, exc: Exception) -> bool:
    if device == "cpu":
        return False

    message = str(exc).lower()
    if "out of memory" in message:
        return True

    runtime_markers = (
        "cublas",
        "cudnn",
        "cudart",
        "cuda driver",
        "cuda runtime",
        "cannot be loaded",
        "failed to load",
    )
    return any(marker in message for marker in runtime_markers)


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
            text = self._run_transcription()
            self.finished.emit(text)
        except Exception as exc:
            _log.error("Transcription error: %s", exc)
            self.error.emit(str(exc))

    def _run_transcription(self) -> str:
        if not is_downloaded(self._model_size):
            raise ModelNotFoundError(
                f"Model '{self._model_size}' is not downloaded. "
                "Open Settings to download it."
            )

        from faster_whisper import WhisperModel

        mp = str(model_path(self._model_size))

        try:
            return self._load_and_transcribe(
                WhisperModel,
                mp,
                device=self._device,
                compute_type=self._compute_type,
            )
        except Exception as exc:
            if _should_fallback_to_cpu(self._device, exc):
                _log.warning(
                    "CUDA transcription failed; falling back to CPU/int8: %s",
                    exc,
                )
                return self._load_and_transcribe(
                    WhisperModel,
                    mp,
                    device="cpu",
                    compute_type="int8",
                )
            raise

    def _load_and_transcribe(
        self,
        model_cls,
        model_path_str: str,
        *,
        device: str,
        compute_type: str,
    ) -> str:
        audio_duration_s = len(self._audio) / 16000.0
        _log.info(
            "Transcription starting: %.1f s audio, device=%s, model=%s",
            audio_duration_s,
            device,
            self._model_size,
        )

        _log.debug("Loading model...")
        model_load_started = time.monotonic()
        model = model_cls(model_path_str, device=device, compute_type=compute_type)
        _log.info("Model loaded in %.1f s", time.monotonic() - model_load_started)
        return self._transcribe_with(model)

    def _transcribe_with(self, model) -> str:
        _log.debug("Inference starting...")
        inference_started = time.monotonic()
        segments, _ = model.transcribe(
            self._audio, language=None, vad_filter=True, beam_size=5
        )
        text = " ".join(seg.text for seg in segments).strip()
        _log.info(
            "Inference completed in %.1f s",
            time.monotonic() - inference_started,
        )
        return text


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
        self._active_job_id: int | None = None
        self._next_job_id = 0
        self._detached_workers: set[_TranscriptionWorker] = set()
        self._last_audio: np.ndarray | None = None
        self._last_params: dict[str, str] | None = None

    @property
    def has_pending_retry(self) -> bool:
        return self._last_audio is not None

    def transcribe(self, audio: np.ndarray) -> None:
        """Start transcription; no-op if a transcription is already running."""
        if self._worker is not None:
            if self._worker.isRunning():
                return
            self.cleanup_worker()

        model_size = self._config.model_size
        device = self._config.device
        compute_type = self._config.compute_type

        self._last_audio = audio
        self._last_params = {
            "model_size": model_size,
            "device": device,
            "compute_type": compute_type,
        }
        self._start_worker(audio, model_size, device, compute_type)

    def cancel_active(self) -> bool:
        """Discard the active job so any late result is ignored by the facade.

        This is a discard-only contract for the current worker. Callers own any
        user-facing cancel state transition and can start a replacement job
        later; late success or error signals from the discarded worker are
        ignored.
        """
        worker = self._worker
        if worker is None:
            return False

        if not worker.isRunning():
            self.cleanup_worker()
            return False

        job_id = self._active_job_id
        if job_id is None:
            return False

        _log.info("Discarding active transcription job %s", job_id)
        self._detach_worker(worker)
        self._worker = None
        self._active_job_id = None
        return True

    def retry_last(self, *, force_cpu: bool = False) -> bool:
        if self._last_audio is None or self._last_params is None:
            return False

        if self._worker is not None:
            if self._worker.isRunning():
                return False
            self.cleanup_worker()

        try:
            model_size = self._last_params["model_size"]
            device = self._last_params["device"]
            compute_type = self._last_params["compute_type"]
        except KeyError:
            _log.warning("Cannot retry transcription: retained params are incomplete")
            return False

        if force_cpu:
            device = "cpu"
            compute_type = "int8"

        self._start_worker(self._last_audio, model_size, device, compute_type)
        return True

    def clear_retry_state(self) -> None:
        """Forget the last audio/params so manual retry is no longer offered.

        Used after a user-initiated cancel so the retained buffer for the
        canceled job does not power a later "Retry last transcription" action.
        Does not touch the active worker — pair with ``cancel_active()`` when
        aborting an in-flight job.
        """
        self._last_audio = None
        self._last_params = None

    def cleanup_worker(self) -> None:
        worker = self._worker
        if worker is not None:
            self._disconnect_worker_signals(worker)
            self._stop_worker(worker)
            if self._worker is worker:
                self._worker = None
            if self._active_job_id == getattr(worker, "_job_id", None):
                self._active_job_id = None

        detached_workers = tuple(self._detached_workers)
        self._detached_workers.clear()
        for detached_worker in detached_workers:
            self._disconnect_worker_signals(detached_worker)
            self._disconnect_worker_cleanup(detached_worker)
            self._stop_worker(detached_worker)

    def _start_worker(
        self,
        audio: np.ndarray,
        model_size: str,
        device: str,
        compute_type: str,
    ) -> None:
        self._next_job_id += 1
        job_id = self._next_job_id
        worker = _TranscriptionWorker(audio, model_size, device, compute_type)
        worker._job_id = job_id
        worker._finished_slot = lambda text, job_id=job_id: self._on_worker_finished(
            job_id, text
        )
        worker._error_slot = lambda message, job_id=job_id: self._on_worker_error(
            job_id, message
        )
        self._worker = worker
        self._active_job_id = job_id
        worker.finished.connect(worker._finished_slot)
        worker.error.connect(worker._error_slot)
        worker.start()

    def _disconnect_worker_signals(self, worker: _TranscriptionWorker) -> None:
        for signal, slot in (
            (worker.finished, getattr(worker, "_finished_slot", None)),
            (worker.error, getattr(worker, "_error_slot", None)),
        ):
            if slot is None:
                continue
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    def _disconnect_worker_cleanup(self, worker: _TranscriptionWorker) -> None:
        cleanup_slot = getattr(worker, "_cleanup_slot", None)
        if cleanup_slot is None:
            return

        for signal in (worker.finished, worker.error):
            try:
                signal.disconnect(cleanup_slot)
            except (TypeError, RuntimeError):
                pass

    def _detach_worker(self, worker: _TranscriptionWorker) -> None:
        self._disconnect_worker_signals(worker)

        cleanup_slot = getattr(worker, "_cleanup_slot", None)
        if cleanup_slot is None:
            cleanup_slot = (
                lambda *_args, worker=worker: self._cleanup_detached_worker(worker)
            )
            worker._cleanup_slot = cleanup_slot
            worker.finished.connect(cleanup_slot)
            worker.error.connect(cleanup_slot)

        self._detached_workers.add(worker)

    def _cleanup_detached_worker(self, worker: _TranscriptionWorker) -> None:
        if worker not in self._detached_workers:
            return

        self._detached_workers.discard(worker)
        self._disconnect_worker_cleanup(worker)
        worker.wait(2000)
        worker.deleteLater()

    def _stop_worker(self, worker: _TranscriptionWorker) -> None:
        if worker.isRunning():
            _log.warning("Terminating transcription worker thread")
            worker.terminate()
            if not worker.wait(2000):
                _log.warning("Timed out waiting for transcription worker shutdown")
        else:
            worker.wait(2000)

        worker.deleteLater()

    def _on_worker_finished(self, job_id: int, text: str) -> None:
        if job_id != self._active_job_id:
            _log.info("Ignoring completed transcription from inactive job %s", job_id)
            return

        self._active_job_id = None
        self._last_audio = None
        self._last_params = None
        self.cleanup_worker()
        self.transcription_finished.emit(text)

    def _on_worker_error(self, job_id: int, message: str) -> None:
        if job_id != self._active_job_id:
            _log.info("Ignoring transcription error from inactive job %s", job_id)
            return

        self._active_job_id = None
        self.cleanup_worker()
        self.transcription_error.emit(message)
