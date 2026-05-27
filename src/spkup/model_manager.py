from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from spkup.platform_support import model_cache_dir as platform_model_cache_dir


# Approximate on-disk sizes for the CT2-converted Systran faster-whisper
# variants, in megabytes. Used purely for user-facing UI hints — do not
# rely on these values for correctness. Real sizes depend on the current
# Hugging Face revision and may drift by ±10-20 %.
MODEL_APPROX_SIZES_MB: dict[str, int] = {
    "tiny": 75,
    "base": 145,
    "small": 465,
    "medium": 1500,
    "large-v2": 3000,
    "large-v3": 3000,
}


def format_model_size(model_size: str) -> str:
    """Return a human-readable approximate size like "~1.5 GB" or "~75 MB".

    Returns an empty string when the model is not in the known mapping.
    """
    mb = MODEL_APPROX_SIZES_MB.get(model_size)
    if mb is None:
        return ""
    if mb >= 1024:
        return f"~{mb / 1024:.1f} GB"
    return f"~{mb} MB"


class ModelNotFoundError(FileNotFoundError):
    """Raised when a model has not been downloaded to the local cache."""


def model_cache_dir() -> Path:
    """Return (and create if needed) the local models cache directory."""
    d = platform_model_cache_dir()
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


def delete_model(model_size: str) -> bool:
    """Remove a downloaded model from the local cache.

    Returns True if a directory was actually removed, False if the model
    was not present. Raises on real filesystem errors (e.g. the model is
    currently loaded and its files are locked on Windows).

    Refuses to act if the resolved target is not inside ``model_cache_dir``.
    """
    target = model_path(model_size)
    try:
        cache_root = model_cache_dir().resolve()
        resolved = target.resolve()
    except OSError:
        raise

    # Guard against any caller passing a model_size that resolves outside
    # the cache directory (e.g. "..", absolute path).
    try:
        resolved.relative_to(cache_root)
    except ValueError as exc:
        raise ValueError(
            f"refusing to delete path outside the model cache: {resolved}"
        ) from exc

    if not resolved.exists() or not resolved.is_dir():
        return False

    shutil.rmtree(resolved)
    return True


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
            self.progress.emit(1)

            import huggingface_hub

            # Progress bars use tqdm which writes to sys.stderr. In the
            # PyInstaller windowed build stderr can be unavailable, which
            # previously crashed downloads with
            # "'NoneType' object has no attribute 'write'". We surface
            # progress via the Qt signal instead, so disable tqdm entirely.
            try:
                huggingface_hub.utils.disable_progress_bars()
            except Exception:
                pass

            repo_id = f"Systran/faster-whisper-{self._model_size}"

            # Download file-by-file so we can report real progress to the UI.
            # snapshot_download does not expose per-file callbacks, and with
            # tqdm disabled the built-in progress bar is unavailable.
            try:
                api = huggingface_hub.HfApi()
                files = list(api.list_repo_files(repo_id=repo_id))
            except Exception:
                files = []

            if not files:
                # Fall back to snapshot_download if listing the repo fails.
                huggingface_hub.snapshot_download(
                    repo_id=repo_id,
                    local_dir=str(target),
                )
                self.progress.emit(100)
                self.finished.emit()
                return

            total = len(files)
            # Reserve 0–5% for the listing step, 5–99% for file downloads.
            self.progress.emit(5)
            for idx, filename in enumerate(files, start=1):
                huggingface_hub.hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=str(target),
                )
                pct = 5 + int((idx / total) * 94)
                if pct >= 100:
                    pct = 99
                self.progress.emit(pct)

            self.progress.emit(100)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
