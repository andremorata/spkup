import os
from pathlib import Path
from unittest.mock import patch

import pytest

from spkup.model_manager import (
    ModelNotFoundError,
    is_downloaded,
    model_cache_dir,
    model_path,
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
