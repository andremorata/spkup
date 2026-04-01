from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class ModelNotFoundError(FileNotFoundError):
    """Raised when a model has not been downloaded to the local cache."""


def model_cache_dir() -> Path:
    """Return (and create if needed) the local models cache directory."""
    d = Path(os.environ["LOCALAPPDATA"]) / "spkup" / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def model_path(model_size: str) -> Path:
    """Return the expected local directory for the given model size."""
    return model_cache_dir() / model_size


def is_downloaded(model_size: str) -> bool:
    """Return True if the model directory exists and contains files."""
    p = model_path(model_size)
    if not p.exists() or not p.is_dir():
        return False
    return any(p.iterdir())


class _ModelDownloadWorker(QThread):
    """Downloads a faster-whisper model to the local cache in a background thread."""

    progress = pyqtSignal(int)   # 0–100
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, model_size: str) -> None:
        super().__init__()
        self._model_size = model_size

    def run(self) -> None:
        try:
            target = model_path(self._model_size)
            target.mkdir(parents=True, exist_ok=True)
            self.progress.emit(5)

            import huggingface_hub

            repo_id = f"Systran/faster-whisper-{self._model_size}"
            huggingface_hub.snapshot_download(
                repo_id=repo_id,
                local_dir=str(target),
            )
            self.progress.emit(100)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
