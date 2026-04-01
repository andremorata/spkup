# Phase 4 — Transcription Engine

> **Reference:** `specs/project.plan.md` — Phase 4
> **Depends on:** Phase 3 — Audio Recording
> **Unlocks:** Phase 5 — Visual Overlay

---

## Objective

Implement a transcription worker that accepts a float32 numpy audio array, runs it through a faster-whisper model on a background QThread (never blocking the UI), and emits the resulting text. The model is lazy-loaded on first use. Model files are downloaded from HuggingFace and cached locally.

---

## Out of Scope

- Visual feedback during transcription (Phase 5)
- Model selection UI and in-app download progress (Phase 7)
- CPU fallback on OOM (Phase 8 — polish)

---

## Dependencies

- Related docs: `specs/project.plan.md` — Working Assumptions, Key Design Decisions
- Phase 3 validated: `recording_finished(np.ndarray)` signal exists
- `faster-whisper` installed in venv; CUDA driver present on host

---

## Tasks

### Task 4.1 — ModelManager

**Deliverable:** `src/spkup/model_manager.py`

- [ ] `model_cache_dir() -> Path`: returns `%LOCALAPPDATA%/spkup/models`, creates it if absent
- [ ] `is_downloaded(model_size: str) -> bool`: checks whether the model directory exists and is non-empty
- [ ] `model_path(model_size: str) -> Path`: returns the expected local path for the given model size
- [ ] No actual download logic in this phase (download UI is Phase 7); raise `ModelNotFoundError` if not on disk
- [ ] Unit tests: `tests/test_model_manager.py` — cache dir creation, path construction, `is_downloaded` with mock filesystem

**Acceptance criterion:** `pytest tests/test_model_manager.py` passes. (AC-4.1)

---

### Task 4.2 — TranscriptionWorker (QThread)

**Deliverable:** `_TranscriptionWorker(QThread)` (private) in `src/spkup/transcriber.py`

- [ ] Accepts `audio: np.ndarray` and `model_size: str`, `device: str`, `compute_type: str`
- [ ] On `run()`: instantiates `faster_whisper.WhisperModel` (lazy — only on first call) with local model path from `ModelManager`
- [ ] Transcribes with `language=None`, `vad_filter=True`, `beam_size=5`
- [ ] Joins segment texts, strips leading/trailing whitespace
- [ ] Emits `finished = pyqtSignal(str)` with the result
- [ ] Emits `error = pyqtSignal(str)` on any exception

**Acceptance criterion:** Worker transcribes a test audio array correctly (manual verification with a short recording). (AC-4.2)

---

### Task 4.3 — Transcriber facade (QObject)

**Deliverable:** `Transcriber(QObject)` in `src/spkup/transcriber.py`

- [ ] Constructor accepts `config: AppConfig`
- [ ] `transcribe(audio: np.ndarray)`: creates and starts a new `_TranscriptionWorker`; ignores call if a worker is already running (busy guard)
- [ ] Forwards worker `finished` → own `transcription_finished = pyqtSignal(str)`
- [ ] Forwards worker `error` → own `transcription_error = pyqtSignal(str)`
- [ ] Cleans up worker after completion (`deleteLater`)

**Acceptance criterion:** Multiple rapid calls to `transcribe()` do not stack workers. (AC-4.3)

---

### Task 4.4 — Wire into App

**Deliverable:** Updated `src/spkup/app.py`

- [ ] Instantiate `Transcriber` in `App.__init__`
- [ ] Connect `AudioRecorder.recording_finished` → `Transcriber.transcribe`
- [ ] Connect `Transcriber.transcription_finished` → stub slot that prints the transcribed text
- [ ] Connect `Transcriber.transcription_error` → stub slot that prints the error

**Acceptance criterion:** Full flow — hold hotkey, speak, release → transcribed text printed to stdout. (AC-4.4)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-4.1 | ModelManager tests pass | `pytest tests/test_model_manager.py` passes |
| AC-4.2 | Worker transcribes correctly | Manual test with short recording |
| AC-4.3 | Busy guard prevents stacked workers | Rapid calls do not queue; second call ignored |
| AC-4.4 | Full pipeline prints transcribed text | Hold hotkey → speak PT or EN → text in stdout |
