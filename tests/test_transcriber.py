from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from PyQt6.QtWidgets import QApplication

from spkup.config import AppConfig
from spkup.transcriber import Transcriber, _TranscriptionWorker, _should_fallback_to_cpu

# A single QApplication is required for QObject/QThread instantiation.
_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def test_should_fallback_to_cpu_for_missing_cuda_library() -> None:
    exc = RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")

    assert _should_fallback_to_cpu("cuda", exc) is True


def test_should_not_fallback_to_cpu_when_already_on_cpu() -> None:
    exc = RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")

    assert _should_fallback_to_cpu("cpu", exc) is False


def test_transcription_falls_back_to_cpu_when_cuda_runtime_missing() -> None:
    audio = np.zeros(1600, dtype=np.float32)
    worker = _TranscriptionWorker(audio, "large-v3", "cuda", "float16")
    model_dir = Path("C:/models/large-v3")
    created_models: list[tuple[str, str, str]] = []

    class FakeModel:
        def __init__(self, model_path: str, device: str, compute_type: str) -> None:
            created_models.append((model_path, device, compute_type))
            if device == "cuda":
                raise RuntimeError(
                    "Library cublas64_12.dll is not found or cannot be loaded"
                )

        def transcribe(self, _audio, language=None, vad_filter=True, beam_size=5):
            return [SimpleNamespace(text="fallback works")], None

    fake_module = SimpleNamespace(WhisperModel=FakeModel)

    with patch("spkup.transcriber.is_downloaded", return_value=True), patch(
        "spkup.transcriber.model_path", return_value=model_dir
    ), patch.dict("sys.modules", {"faster_whisper": fake_module}):
        assert worker._run_transcription() == "fallback works"

    assert created_models == [
        (str(model_dir), "cuda", "float16"),
        (str(model_dir), "cpu", "int8"),
    ]


def test_transcription_raises_for_non_fallback_errors() -> None:
    audio = np.zeros(1600, dtype=np.float32)
    worker = _TranscriptionWorker(audio, "large-v3", "cuda", "float16")

    class FakeModel:
        def __init__(self, model_path: str, device: str, compute_type: str) -> None:
            raise RuntimeError("model weights are corrupted")

    fake_module = SimpleNamespace(WhisperModel=FakeModel)

    with patch("spkup.transcriber.is_downloaded", return_value=True), patch(
        "spkup.transcriber.model_path", return_value=Path("C:/models/large-v3")
    ), patch.dict("sys.modules", {"faster_whisper": fake_module}):
        try:
            worker._run_transcription()
        except RuntimeError as exc:
            assert str(exc) == "model weights are corrupted"
        else:
            raise AssertionError("expected RuntimeError")


# ---------------------------------------------------------------------------
# Transcriber facade — retry infrastructure
# ---------------------------------------------------------------------------


def test_has_pending_retry_false_initially() -> None:
    """A fresh Transcriber has no retained audio."""
    t = Transcriber(AppConfig())
    assert t.has_pending_retry is False


def test_retry_last_returns_false_when_no_audio() -> None:
    """retry_last() returns False when no audio has been retained."""
    t = Transcriber(AppConfig())
    assert t.retry_last() is False


def test_audio_retained_after_transcribe_start() -> None:
    """Calling transcribe() stores the audio so has_pending_retry becomes True."""
    audio = np.zeros(1600, dtype=np.float32)
    t = Transcriber(AppConfig())

    with patch("spkup.transcriber._TranscriptionWorker") as MockWorker:
        mock_instance = MockWorker.return_value
        mock_instance.isRunning.return_value = False
        t.transcribe(audio)

    assert t.has_pending_retry is True
    assert t._last_audio is audio


def test_audio_cleared_on_success() -> None:
    """_on_worker_finished clears the retained audio; has_pending_retry becomes False."""
    t = Transcriber(AppConfig())
    emitted: list[str] = []
    t.transcription_finished.connect(emitted.append)
    t._last_audio = np.zeros(100, dtype=np.float32)
    t._last_params = {"model_size": "large-v3", "device": "cuda", "compute_type": "int8"}
    t._active_job_id = 1
    t._worker = None

    t._on_worker_finished(1, "hello")

    assert t.has_pending_retry is False
    assert t._last_audio is None
    assert emitted == ["hello"]


def test_audio_retained_on_error() -> None:
    """_on_worker_error does NOT clear retained audio so a retry is still possible."""
    t = Transcriber(AppConfig())
    emitted: list[str] = []
    t.transcription_error.connect(emitted.append)
    audio = np.zeros(100, dtype=np.float32)
    t._last_audio = audio
    t._last_params = {"model_size": "large-v3", "device": "cuda", "compute_type": "int8"}
    t._active_job_id = 1
    t._worker = None

    t._on_worker_error(1, "cuda timeout")

    assert t.has_pending_retry is True
    assert emitted == ["cuda timeout"]


def test_cancel_active_returns_false_without_running_worker() -> None:
    t = Transcriber(AppConfig())

    assert t.cancel_active() is False


def test_cancel_active_discards_late_success() -> None:
    t = Transcriber(AppConfig())
    emitted: list[str] = []
    t.transcription_finished.connect(emitted.append)
    t._last_audio = np.zeros(100, dtype=np.float32)
    t._last_params = {"model_size": "large-v3", "device": "cuda", "compute_type": "int8"}
    worker = MagicMock()
    worker.isRunning.return_value = True
    t._worker = worker
    t._active_job_id = 7

    assert t.cancel_active() is True

    t._on_worker_finished(7, "late result")

    assert emitted == []
    assert t.has_pending_retry is True
    assert t._worker is None


def test_cancel_active_discards_late_error() -> None:
    t = Transcriber(AppConfig())
    emitted: list[str] = []
    t.transcription_error.connect(emitted.append)
    t._last_audio = np.zeros(100, dtype=np.float32)
    t._last_params = {"model_size": "large-v3", "device": "cuda", "compute_type": "int8"}
    worker = MagicMock()
    worker.isRunning.return_value = True
    t._worker = worker
    t._active_job_id = 7

    assert t.cancel_active() is True

    t._on_worker_error(7, "late error")

    assert emitted == []
    assert t.has_pending_retry is True
    assert t._worker is None


def test_retry_last_basic() -> None:
    """retry_last() returns True when audio is retained and starts a new worker."""
    audio = np.zeros(1600, dtype=np.float32)
    t = Transcriber(AppConfig())
    t._last_audio = audio
    t._last_params = {"model_size": "large-v3", "device": "cuda", "compute_type": "int8"}

    with patch.object(t, "_start_worker") as mock_start:
        result = t.retry_last()

    assert result is True
    mock_start.assert_called_once_with(audio, "large-v3", "cuda", "int8")


def test_retry_last_force_cpu() -> None:
    """retry_last(force_cpu=True) overrides device/compute_type to cpu/int8."""
    audio = np.zeros(1600, dtype=np.float32)
    t = Transcriber(AppConfig())
    t._last_audio = audio
    t._last_params = {"model_size": "large-v3", "device": "cuda", "compute_type": "float16"}

    with patch.object(t, "_start_worker") as mock_start:
        result = t.retry_last(force_cpu=True)

    assert result is True
    mock_start.assert_called_once_with(audio, "large-v3", "cpu", "int8")


def test_cleanup_worker() -> None:
    """cleanup_worker() terminates a running worker and sets _worker to None."""
    t = Transcriber(AppConfig())
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    mock_worker.wait.return_value = True
    t._worker = mock_worker

    t.cleanup_worker()

    mock_worker.terminate.assert_called_once()
    assert t._worker is None
