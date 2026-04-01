# Phase 3 — Audio Recording

> **Reference:** `specs/project-template.plan.md` — Phase 3
> **Depends on:** Phase 2 — Global Hotkey
> **Unlocks:** Phase 4 — Transcription Engine

---

## Objective

Implement an `AudioRecorder` that starts capturing microphone audio when told to, accumulates it in memory as a numpy array, and emits the completed recording when stopped. Audio must meet Whisper's requirements: 16 kHz, mono, float32, no disk I/O.

---

## Out of Scope

- Transcription (Phase 4)
- Visual feedback (Phase 5)
- Device selection UI (Phase 7)

---

## Dependencies

- Related docs: `specs/project-template.plan.md` — Working Assumptions (no WAV files)
- Phase 2 validated: `recording_started` / `recording_stopped` signals exist
- `sounddevice` and `numpy` installed in venv

---

## Tasks

### Task 3.1 — AudioRecorder class

**Deliverable:** `AudioRecorder(QObject)` in `src/spkup/recorder.py`

- [ ] Constructor accepts `device: int | None = None`, `max_seconds: int = 120`
- [ ] Uses `sounddevice.InputStream` at 16000 Hz, 1 channel, `dtype="float32"`
- [ ] `start()`: opens stream, resets chunk list, starts a `QTimer` safety cutoff at `max_seconds`
- [ ] Audio callback appends numpy chunks to `_chunks: list[np.ndarray]`
- [ ] `stop()`: cancels timer, closes stream, calls `np.concatenate(_chunks)`, emits `recording_finished`
- [ ] Safety timer expiry calls `stop()` automatically
- [ ] Signal: `recording_finished = pyqtSignal(object)` — payload is `np.ndarray` (float32, shape `(N,)`)
- [ ] Signal: `recording_error = pyqtSignal(str)` — emitted if no mic found or stream error

**Acceptance criterion:** `AudioRecorder` starts and stops cleanly; emits a non-empty float32 array. (AC-3.1)

---

### Task 3.2 — Unit tests

**Deliverable:** `tests/test_recorder.py`

- [ ] Test that `stop()` before `start()` does not crash
- [ ] Test that `recording_finished` is emitted after `start()` + `stop()` (use a mock `sounddevice.InputStream`)
- [ ] Test that the safety timer calls `stop()` after `max_seconds`
- [ ] Test that returned array dtype is `float32` and shape is `(N,)`

**Acceptance criterion:** `pytest tests/test_recorder.py` passes. (AC-3.2)

---

### Task 3.3 — Wire into App

**Deliverable:** Updated `src/spkup/app.py`

- [ ] Instantiate `AudioRecorder` in `App.__init__`
- [ ] Connect `HotkeyListener.recording_started` → `AudioRecorder.start()`
- [ ] Connect `HotkeyListener.recording_stopped` → `AudioRecorder.stop()`
- [ ] Connect `AudioRecorder.recording_finished` → stub slot that prints array shape
- [ ] Connect `AudioRecorder.recording_error` → stub slot that prints the error

**Acceptance criterion:** Hold hotkey, speak, release → stdout shows array shape (e.g. `(48000,)` for ~3 s). (AC-3.3)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-3.1 | Recorder produces float32 mono array | Inspect emitted array dtype and shape |
| AC-3.2 | Unit tests pass | `pytest tests/test_recorder.py` passes |
| AC-3.3 | End-to-end hotkey → capture works | Array shape printed to stdout on key release |
