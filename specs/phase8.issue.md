# Phase 8 — Polish

> **Reference:** `specs/project.plan.md` — Phase 8
> **Depends on:** Phase 7 — Settings Dialog
> **Unlocks:** Phase 9 — Packaging, GitHub CI/CD, versioning, and releases

---

## Objective

Harden the application for daily use: structured file logging, graceful error recovery (no mic, CUDA OOM), auto-start via Windows registry, and a first-run experience that guides the user through model selection and initial setup.

---

## Out of Scope

- Feature additions beyond the original plan
- Distribution / packaging

Explicit Phase 8 extension:

- Recent transcription history was added to Phase 8 on 2026-04-01 and is in scope for this phase only.

---

## Dependencies

- Phase 7 validated: full feature set working
- `winreg` (stdlib) available on Windows

---

## Tasks

### Task 8.0 — Toggle recording hotkey mode

**Deliverable:** Updated `src/spkup/hotkey.py`

- [x] Preserve existing hold-to-record behavior
- [x] Add quick-tap toggle mode: press + release within 300 ms keeps recording active
- [x] Add second full hotkey tap to stop recording while toggle mode is active
- [x] Extend `tests/test_hotkey.py` to cover hold and toggle paths

**Acceptance criterion:** Automated coverage is in place and manual validation is complete: `pytest tests/ -v` passes and manual hotkey use supports both hold and quick-tap toggle flows. (AC-8.0)

### Task 8.1 — Structured logging

**Deliverable:** `src/spkup/logging_setup.py`

- [x] `configure_logging() -> logging.Logger`: configures root logger with `RotatingFileHandler` to `%LOCALAPPDATA%/spkup/spkup.log` (max 5 MB, 3 backups) and a `StreamHandler` for stderr
- [x] Log format: `%(asctime)s %(levelname)-8s %(name)s — %(message)s`
- [x] Call `configure_logging()` at the top of `__main__.py` before anything else
- [x] Replace any remaining `print()` statements in the codebase with appropriate `logging` calls

**Acceptance criterion:** Implementation is complete and manual runtime validation is complete: `spkup.log` is created after launch and contains startup log entries. (AC-8.1)

---

### Task 8.2 — Error handling

**Deliverable:** Updated `recorder.py`, `transcriber.py`, `app.py`

- [x] `recorder.py`: catch `sounddevice.PortAudioError` in `start()`; emit `recording_error` with human-readable message; log at `ERROR` level
- [x] `transcriber.py`: catch `torch.cuda.OutOfMemoryError` (and generic `RuntimeError` containing "CUDA out of memory"); log warning; retry transcription with `device="cpu"`, `compute_type="int8"` — emit `transcription_finished` as normal if CPU retry succeeds
- [x] `app.py`: on `recording_error` or `transcription_error` show tray balloon with message; log at `ERROR`
- [x] No unhandled exceptions should crash the process silently

**Acceptance criterion:** Manual validation is complete for the current implementation: unplug mic → error tray notification appears; CUDA OOM → CPU fallback produces text. (AC-8.2)

---

### Task 8.3 — Auto-start via Windows registry

**Deliverable:** `src/spkup/autostart.py`

- [x] `enable_autostart(exe_path: str) -> None`: writes `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\spkup` with the path to the launcher
- [x] `disable_autostart() -> None`: deletes the registry key if it exists
- [x] `is_autostart_enabled() -> bool`: checks if the key exists
- [x] Tray context menu gains a checkable **Start on login** action that calls these functions
- [x] Unit tests: `tests/test_autostart.py` — mock `winreg`; test enable/disable/query

**Acceptance criterion:** Automated coverage is in place and manual registry and tray validation are complete: enable → key present in registry; disable → key absent; tray action reflects current state. (AC-8.3)

---

### Task 8.4 — First-run experience

**Deliverable:** Updated `src/spkup/app.py` and `src/spkup/settings_dialog.py`

- [x] On first launch (config file does not exist yet), open `SettingsDialog` automatically with a welcome banner: "Welcome to spkup. Choose a model and download it to get started."
- [x] Disable main hotkey listener until a model is confirmed downloaded
- [x] After successful download, close the first-run dialog and show tray notification: "spkup is ready. Hold [hotkey] to record."

**Acceptance criterion:** Manual first-run validation is complete: fresh install (no config.json, no cached model) → dialog opens automatically; after download → hotkey works. (AC-8.4)

---

### Task 8.5 — Recent transcription history

**Deliverable:** Updated tray/app wiring plus `transcription_history.py`, `transcription_history_window.py`, and `tests/test_transcription_history.py`

- [x] Keep the last 5 completed transcriptions in memory for the current app session only
- [x] On transcription completion, push the newest text into recent-history and cap the list at 5 entries
- [x] Add a tray menu action that opens a dedicated recent-history window
- [x] The recent-history window shows up to 5 entries in newest-first order
- [x] Each entry can be copied directly from the window
- [x] Each entry can be deleted directly from the window
- [x] Closing or reopening the window preserves the current session history while the app remains running
- [x] Add unit coverage in `tests/test_transcription_history.py` for ordering, capping, delete, Unicode, and duplicate-entry behavior

**Acceptance criterion:** Implementation is complete, unit coverage exists, and manual verification is complete for tray/window behavior: after 6 successful transcriptions, the recent-history window shows the latest 5 entries only; any entry is copyable or deletable from the window without affecting the remaining entries. (AC-8.5)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-8.1 | Log file creation and startup entries validated | `%LOCALAPPDATA%/spkup/spkup.log` was created after launch and contains startup log entries |
| AC-8.2 | Error recovery validated | No-mic and CUDA OOM scenarios were manually validated with tray notification and CPU fallback behavior |
| AC-8.3 | Auto-start registry key management validated | `tests/test_autostart.py` is covered and manual registry/tray validation confirmed enable, disable, and reflected state |
| AC-8.4 | First-run dialog and readiness flow validated | Fresh-install first-run behavior was validated, including automatic dialog launch and post-download readiness |
| AC-8.5 | Recent-history window behavior validated for the last 5 session transcriptions | Recent-history tray/window behavior was manually validated, including capping at 5 entries plus copy and delete actions |
