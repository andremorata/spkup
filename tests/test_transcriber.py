from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from spkup.transcriber import _TranscriptionWorker, _should_fallback_to_cpu


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
