import os
from pathlib import Path
from unittest.mock import patch

import pytest
import sys

from PyQt6.QtWidgets import QApplication

from spkup.model_manager import (
    ModelNotFoundError,
    MODEL_APPROX_SIZES_MB,
    delete_model,
    format_model_size,
    is_downloaded,
    model_cache_dir,
    model_path,
)

# A single QApplication is required for QObject/QThread instantiation.
_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _isolated_model_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "spkup.model_manager.platform_model_cache_dir",
        lambda: tmp_path / "spkup" / "models",
    )


def test_model_cache_dir_created(tmp_path, monkeypatch):
    """model_cache_dir() creates the directory if it does not exist."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    d = model_cache_dir()
    assert d.exists()
    assert d.is_dir()
    assert d == tmp_path / "spkup" / "models"


def test_model_cache_dir_idempotent(tmp_path, monkeypatch):
    """model_cache_dir() does not raise if directory already exists."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    model_cache_dir()
    model_cache_dir()  # second call must not raise


def test_model_path_returns_expected(tmp_path, monkeypatch):
    """model_path() returns expected subdirectory under cache dir."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    p = model_path("base")
    assert p == tmp_path / "spkup" / "models" / "base"


def test_is_downloaded_false_when_missing(tmp_path, monkeypatch):
    """is_downloaded() returns False when directory does not exist."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert not is_downloaded("small")


def test_is_downloaded_false_when_empty_dir(tmp_path, monkeypatch):
    """is_downloaded() returns False when directory exists but is empty."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    model_path("tiny").mkdir(parents=True)
    assert not is_downloaded("tiny")


def test_is_downloaded_true_when_populated(tmp_path, monkeypatch):
    """is_downloaded() returns True when directory contains at least one file."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    p = model_path("large-v3")
    p.mkdir(parents=True)
    (p / "model.bin").write_bytes(b"fake-weights")
    assert is_downloaded("large-v3")


def test_model_not_found_error_is_file_not_found():
    """ModelNotFoundError is a subclass of FileNotFoundError."""
    err = ModelNotFoundError("missing")
    assert isinstance(err, FileNotFoundError)


def test_ensure_std_streams_replaces_none(monkeypatch):
    """_ensure_std_streams() replaces None stdout/stderr so tqdm cannot crash.

    Regression for the windowed PyInstaller build where sys.stdout and
    sys.stderr are None and huggingface_hub's tqdm progress bar raised
    'NoneType' object has no attribute 'write' during snapshot_download.
    """
    from spkup.__main__ import _ensure_std_streams

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    _ensure_std_streams()

    assert sys.stdout is not None
    assert sys.stderr is not None
    assert hasattr(sys.stdout, "write")
    assert hasattr(sys.stderr, "write")
    # Writing must not raise.
    sys.stdout.write("ok")
    sys.stderr.write("ok")


def test_model_download_worker_disables_progress_bars(tmp_path, monkeypatch):
    """_ModelDownloadWorker.run disables hf tqdm bars before downloading.

    With the windowed build's stderr=None, tqdm writes would crash the
    download. The worker must disable progress bars defensively.
    """
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from spkup.model_manager import _ModelDownloadWorker

    calls: dict[str, int] = {"disable": 0, "list": 0, "hf_hub_download": 0}

    import huggingface_hub
    import huggingface_hub.utils as hf_utils

    def fake_disable() -> None:
        calls["disable"] += 1

    class FakeApi:
        def list_repo_files(self, repo_id):  # type: ignore[no-untyped-def]
            calls["list"] += 1
            assert calls["disable"] >= 1, "progress bars must be disabled before listing"
            return ["config.json", "model.bin", "tokenizer.json"]

    def fake_hf_hub_download(**kwargs):  # type: ignore[no-untyped-def]
        calls["hf_hub_download"] += 1
        assert calls["disable"] >= 1, "progress bars must be disabled before download"
        return str(Path(kwargs["local_dir"]) / kwargs["filename"])

    monkeypatch.setattr(hf_utils, "disable_progress_bars", fake_disable)
    monkeypatch.setattr(huggingface_hub, "HfApi", FakeApi)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake_hf_hub_download)

    worker = _ModelDownloadWorker("medium")

    errors: list[str] = []
    finished: list[bool] = []
    progress_values: list[int] = []
    worker.error.connect(lambda msg: errors.append(msg))  # type: ignore[attr-defined]
    worker.finished.connect(lambda: finished.append(True))  # type: ignore[attr-defined]
    worker.progress.connect(lambda v: progress_values.append(v))  # type: ignore[attr-defined]

    worker.run()

    assert errors == [], f"download worker emitted error: {errors}"
    assert finished == [True]
    assert calls["disable"] == 1
    assert calls["list"] == 1
    assert calls["hf_hub_download"] == 3
    # Progress must be monotonically non-decreasing and reach 100.
    assert progress_values[0] <= progress_values[-1]
    assert progress_values[-1] == 100
    assert 100 not in progress_values[:-1], "100% must only be emitted once at the end"
    # More than just start and end values should be reported (real progress).
    assert len(progress_values) >= 4


def test_model_download_worker_falls_back_to_snapshot(tmp_path, monkeypatch):
    """If listing repo files fails, worker falls back to snapshot_download."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from spkup.model_manager import _ModelDownloadWorker

    calls: dict[str, int] = {"snapshot": 0}

    import huggingface_hub
    import huggingface_hub.utils as hf_utils

    class FailingApi:
        def list_repo_files(self, repo_id):  # type: ignore[no-untyped-def]
            raise RuntimeError("offline")

    def fake_snapshot(**kwargs):  # type: ignore[no-untyped-def]
        calls["snapshot"] += 1
        return str(kwargs["local_dir"])

    monkeypatch.setattr(hf_utils, "disable_progress_bars", lambda: None)
    monkeypatch.setattr(huggingface_hub, "HfApi", FailingApi)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot)

    worker = _ModelDownloadWorker("tiny")

    errors: list[str] = []
    finished: list[bool] = []
    worker.error.connect(lambda msg: errors.append(msg))  # type: ignore[attr-defined]
    worker.finished.connect(lambda: finished.append(True))  # type: ignore[attr-defined]

    worker.run()

    assert errors == []
    assert finished == [True]
    assert calls["snapshot"] == 1


# ---------- format_model_size ------------------------------------------------


def test_format_model_size_returns_mb_for_small_models():
    """format_model_size() returns a '~<n> MB' string for sub-GB models."""
    assert format_model_size("tiny") == "~75 MB"
    assert format_model_size("base") == "~145 MB"
    assert format_model_size("small") == "~465 MB"


def test_format_model_size_returns_gb_for_large_models():
    """format_model_size() returns a '~<n.n> GB' string for GB-scale models."""
    assert format_model_size("medium").endswith(" GB")
    assert format_model_size("large-v2").endswith(" GB")
    assert format_model_size("large-v3").endswith(" GB")


def test_format_model_size_empty_for_unknown():
    """format_model_size() returns '' for unknown model names."""
    assert format_model_size("unknown-model") == ""
    assert format_model_size("") == ""


def test_model_approx_sizes_covers_all_supported_models():
    """MODEL_APPROX_SIZES_MB must cover every model exposed in the Settings UI."""
    expected = {"tiny", "base", "small", "medium", "large-v2", "large-v3"}
    assert expected.issubset(MODEL_APPROX_SIZES_MB.keys())


# ---------- delete_model -----------------------------------------------------


def test_delete_model_removes_existing_directory(tmp_path, monkeypatch):
    """delete_model() removes a populated model directory and returns True."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    p = model_path("small")
    p.mkdir(parents=True)
    (p / "model.bin").write_bytes(b"weights")

    assert delete_model("small") is True
    assert not p.exists()
    assert not is_downloaded("small")


def test_delete_model_returns_false_when_missing(tmp_path, monkeypatch):
    """delete_model() returns False when the model is not downloaded."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert delete_model("medium") is False


def test_delete_model_leaves_siblings_untouched(tmp_path, monkeypatch):
    """delete_model() must only remove the targeted model directory."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    tiny = model_path("tiny")
    tiny.mkdir(parents=True)
    (tiny / "f.bin").write_bytes(b"x")
    base = model_path("base")
    base.mkdir(parents=True)
    (base / "f.bin").write_bytes(b"y")

    assert delete_model("tiny") is True

    assert not tiny.exists()
    assert base.exists()
    assert (base / "f.bin").exists()


def test_delete_model_refuses_path_outside_cache(tmp_path, monkeypatch):
    """delete_model() must refuse paths that resolve outside the cache dir."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # Create a sibling outside the cache that must NOT be deleted.
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "keep.txt").write_bytes(b"keep")

    with pytest.raises(ValueError):
        delete_model(os.path.join("..", "elsewhere"))

    assert outside.exists()
    assert (outside / "keep.txt").exists()
