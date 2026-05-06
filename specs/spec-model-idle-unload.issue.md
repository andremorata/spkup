# Spec — Model Idle Auto-Unload

> **Type:** Spec
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `In progress`
> **Created:** 2026-05-06
> **Depends on:** —

---

## Objective

Allow users to configure an inactivity timeout (in minutes) after which the loaded
faster-whisper model is automatically unloaded from RAM. Setting the value to 0 (the
default) preserves current behaviour — the model stays in memory indefinitely after
its first load. Model instances are cached between transcriptions so reloading only
occurs when the cache was cleared or on the first run.

---

## Why Now

- User-reported: after the first capture the model occupies a significant amount of
  RAM and there is no way to reclaim it short of quitting the app.

---

## Out of Scope

- Proactive memory usage telemetry or display.
- Manually triggered "unload model now" action.
- Per-model memory size estimates in the UI.

---

## Affected Areas

- Code / modules: `config.py`, `transcriber.py`, `settings_dialog.py`, `app.py`
- Docs: none
- Tests: `tests/test_transcriber_idle_unload.py` (new)
- Manual verification surface: Settings → General → "Unload model after … minutes"

---

## Tasks

### Task 1 — Config field

**Deliverable:** `AppConfig.model_idle_unload_minutes: int = 0`

- [x] Add field to `AppConfig` dataclass.

**Acceptance criterion:** Field is persisted to and loaded from `config.json`. (AC-1)

---

### Task 2 — Model cache + idle timer in Transcriber

**Deliverable:** Module-level model cache; `Transcriber` idle timer that calls
`unload_cached_model()` after the configured number of minutes of inactivity.

- [x] Add module-level `_model_cache` dict (keyed by `(model_path, device, compute_type)`)
  and a `threading.Lock`.
- [x] Reuse the cached model in `_TranscriptionWorker` when available.
- [x] Cache the model after a successful load.
- [x] Expose `unload_cached_model()` at module level.
- [x] Add `QTimer _idle_unload_timer` to `Transcriber`; start/restart it after each
  completed or failed transcription; clear it when a new transcription starts.
- [x] Timer fires → `unload_cached_model()`.
- [x] `update_config(config)` method to refresh the timer interval when settings change.

**Acceptance criterion:** After N minutes of no transcription activity the model is
removed from the cache. The next transcription reloads the model from disk. (AC-2)

---

### Task 3 — Settings dialog spinbox

**Deliverable:** Spinbox in the General tab of `SettingsDialog`.

- [x] Add `QSpinBox` (range 0–240, suffix " min", special-value text "Never (0)") to
  General tab, below the "Mute playback" checkbox.
- [x] Wire its `valueChanged` signal to `self._config.model_idle_unload_minutes`.

**Acceptance criterion:** Value is shown correctly on dialog open and saved on "Save". (AC-3)

---

### Task 4 — App wiring

**Deliverable:** `app.py` calls `self._transcriber.update_config(new_config)` when
settings change so the running timer is updated without rebuilding the transcriber.

- [x] Call `update_config` in `_on_settings_saved`.

**Acceptance criterion:** Changing the timeout in settings takes effect immediately
without restarting the app. (AC-4)

---

## Acceptance Criteria

| ID   | Criterion                                                                    | How To Verify                                                   |
| ---- | ---------------------------------------------------------------------------- | --------------------------------------------------------------- |
| AC-1 | `model_idle_unload_minutes` survives a save/load round-trip.                 | Unit test or manual inspection of `config.json`.                |
| AC-2 | Cached model is cleared after the timer fires; next call reloads from disk.  | Unit test mocking `WhisperModel` and advancing the timer.       |
| AC-3 | Spinbox shows saved value on dialog open; value is persisted on Save.        | Manual UI check.                                                |
| AC-4 | Adjusting timeout via Settings takes effect for the next idle period.        | Manual: change setting, do a transcription, observe log output. |

---

## Validation Plan

- Automated checks: `tests/test_transcriber_idle_unload.py`
- Manual checks: open Settings, set timeout to 1 min, record, wait, observe that the
  next recording triggers a model reload message in the log.
- Evidence to capture in `specs/progress.status.md`: test run output.

---

## Risks and Notes

- Dependencies: `PyQt6.QtCore.QTimer` (already in use).
- Rollback: field defaults to 0 so existing configs are unaffected.
- Thread safety: cache is only written from worker threads when no other worker is
  running (busy-guard) and only cleared from the main thread timer; a `threading.Lock`
  guards concurrent access.

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. All acceptance criteria above are satisfied.
2. Tests are written, passing, and referenced as evidence.
3. `specs/progress.status.md` records the validation summary, evidence, and next action.
