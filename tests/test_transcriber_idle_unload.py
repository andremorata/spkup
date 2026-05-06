"""Tests for the Whisper model idle-unload feature.

Covers:
- Model is cached after first load.
- Cached model is reused on second call (no second WhisperModel instantiation).
- Idle timer starts after transcription completes.
- Idle timer fires → model is removed from cache.
- Setting model_idle_unload_minutes=0 disables the timer.
- update_config() refreshes the timer interval live.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from spkup.config import AppConfig
from spkup.transcriber import (
    Transcriber,
    _TranscriptionWorker,
    _get_cached_model,
    _set_cached_model,
    unload_cached_model,
)

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_whisper(model_dir: Path, created: list):
    """Return a fake WhisperModel class that tracks instantiations."""

    class FakeModel:
        def __init__(self, model_path: str, device: str, compute_type: str) -> None:
            created.append((model_path, device, compute_type))

        def transcribe(self, _audio, language=None, vad_filter=True, beam_size=5):
            return [SimpleNamespace(text="hello")], None

    return FakeModel


def _make_fake_module(model_dir: Path, created: list):
    return SimpleNamespace(WhisperModel=_make_fake_whisper(model_dir, created))


def _flush_events():
    QCoreApplication.processEvents()


# ---------------------------------------------------------------------------
# Cache unit tests (no QThread, test _TranscriptionWorker._run_transcription)
# ---------------------------------------------------------------------------

def _run_worker(model_dir: Path, fake_module):
    audio = np.zeros(1600, dtype=np.float32)
    worker = _TranscriptionWorker(audio, "large-v3", "cpu", "int8")
    with (
        patch("spkup.transcriber.is_downloaded", return_value=True),
        patch("spkup.transcriber.model_path", return_value=model_dir),
        patch.dict("sys.modules", {"faster_whisper": fake_module}),
    ):
        return worker._run_transcription()


def test_model_is_cached_after_first_load(tmp_path):
    unload_cached_model()
    model_dir = tmp_path / "large-v3"
    created: list = []
    fake_module = _make_fake_module(model_dir, created)
    cache_key = (str(model_dir), "cpu", "int8")

    assert _get_cached_model(cache_key) is None

    _run_worker(model_dir, fake_module)

    assert _get_cached_model(cache_key) is not None
    assert len(created) == 1


def test_cached_model_reused_on_second_call(tmp_path):
    unload_cached_model()
    model_dir = tmp_path / "large-v3"
    created: list = []
    fake_module = _make_fake_module(model_dir, created)

    _run_worker(model_dir, fake_module)
    _run_worker(model_dir, fake_module)

    # WhisperModel should only have been constructed once
    assert len(created) == 1


def test_unload_cached_model_clears_cache(tmp_path):
    model_dir = tmp_path / "large-v3"
    created: list = []
    fake_module = _make_fake_module(model_dir, created)
    cache_key = (str(model_dir), "cpu", "int8")

    _run_worker(model_dir, fake_module)
    assert _get_cached_model(cache_key) is not None

    unload_cached_model()

    assert _get_cached_model(cache_key) is None
    assert len(created) == 1


def test_model_reloaded_after_unload(tmp_path):
    unload_cached_model()
    model_dir = tmp_path / "large-v3"
    created: list = []
    fake_module = _make_fake_module(model_dir, created)

    _run_worker(model_dir, fake_module)
    unload_cached_model()
    _run_worker(model_dir, fake_module)

    assert len(created) == 2


# ---------------------------------------------------------------------------
# Transcriber idle timer tests
# ---------------------------------------------------------------------------

def _make_config(idle_minutes: int) -> AppConfig:
    return AppConfig(
        model_size="large-v3",
        device="cpu",
        compute_type="int8",
        model_idle_unload_minutes=idle_minutes,
    )


def _run_transcription_through_transcriber(transcriber: Transcriber, tmp_path: Path):
    """Run one full transcription cycle and wait for it to complete."""
    model_dir = tmp_path / "large-v3"
    created: list = []
    fake_module = _make_fake_module(model_dir, created)

    results: list[str] = []
    transcriber.transcription_finished.connect(results.append)

    audio = np.zeros(1600, dtype=np.float32)
    with (
        patch("spkup.transcriber.is_downloaded", return_value=True),
        patch("spkup.transcriber.model_path", return_value=model_dir),
        patch.dict("sys.modules", {"faster_whisper": fake_module}),
    ):
        transcriber.transcribe(audio)
        # Wait for the worker thread to finish (up to 5 s)
        if transcriber._worker is not None:
            transcriber._worker.wait(5000)
        _flush_events()

    return results, created


def test_idle_timer_not_started_when_disabled(tmp_path):
    unload_cached_model()
    config = _make_config(idle_minutes=0)
    t = Transcriber(config)

    _run_transcription_through_transcriber(t, tmp_path)

    assert not t._idle_unload_timer.isActive()
    t.cleanup_worker()


def test_idle_timer_started_after_transcription_when_enabled(tmp_path):
    unload_cached_model()
    config = _make_config(idle_minutes=5)
    t = Transcriber(config)

    _run_transcription_through_transcriber(t, tmp_path)

    assert t._idle_unload_timer.isActive()
    t._idle_unload_timer.stop()
    t.cleanup_worker()


def test_idle_timer_fires_and_clears_cache(tmp_path):
    unload_cached_model()
    config = _make_config(idle_minutes=5)
    t = Transcriber(config)
    model_dir = tmp_path / "large-v3"
    cache_key = (str(model_dir), "cpu", "int8")

    _run_transcription_through_transcriber(t, tmp_path)
    assert _get_cached_model(cache_key) is not None

    # Fire the timer manually (simulates idle timeout)
    t._idle_unload_timer.stop()
    t._on_idle_unload_timeout()

    assert _get_cached_model(cache_key) is None
    t.cleanup_worker()


def test_update_config_updates_timer_interval(tmp_path):
    unload_cached_model()
    config = _make_config(idle_minutes=10)
    t = Transcriber(config)

    _run_transcription_through_transcriber(t, tmp_path)
    assert t._idle_unload_timer.isActive()
    old_remaining = t._idle_unload_timer.remainingTime()

    new_config = _make_config(idle_minutes=30)
    t.update_config(new_config)

    # Timer should have been restarted with the new (longer) interval
    assert t._idle_unload_timer.isActive()
    new_remaining = t._idle_unload_timer.remainingTime()
    assert new_remaining > old_remaining

    t._idle_unload_timer.stop()
    t.cleanup_worker()


def test_update_config_disables_timer_when_set_to_zero(tmp_path):
    unload_cached_model()
    config = _make_config(idle_minutes=10)
    t = Transcriber(config)

    _run_transcription_through_transcriber(t, tmp_path)
    assert t._idle_unload_timer.isActive()

    t.update_config(_make_config(idle_minutes=0))

    assert not t._idle_unload_timer.isActive()
    t.cleanup_worker()
