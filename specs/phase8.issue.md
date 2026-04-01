# Phase 8 — Polish

> **Reference:** `specs/project-template.plan.md` — Phase 8
> **Depends on:** Phase 7 — Settings Dialog
> **Unlocks:** None — final phase

---

## Objective

Harden the application for daily use: structured file logging, graceful error recovery (no mic, CUDA OOM), auto-start via Windows registry, and a first-run experience that guides the user through model selection and initial setup.

---

## Out of Scope

- Feature additions beyond the original plan
- Distribution / packaging

---

## Dependencies

- Phase 7 validated: full feature set working
- `winreg` (stdlib) available on Windows

---

## Tasks

### Task 8.1 — Structured logging

**Deliverable:** `src/spkup/logging_setup.py`

- [ ] `configure_logging() -> logging.Logger`: configures root logger with `RotatingFileHandler` to `%LOCALAPPDATA%/spkup/spkup.log` (max 5 MB, 3 backups) and a `StreamHandler` for stderr
- [ ] Log format: `%(asctime)s %(levelname)-8s %(name)s — %(message)s`
- [ ] Call `configure_logging()` at the top of `__main__.py` before anything else
- [ ] Replace any remaining `print()` statements in the codebase with appropriate `logging` calls

**Acceptance criterion:** `spkup.log` is created after launch and contains startup log entries. (AC-8.1)

---

### Task 8.2 — Error handling

**Deliverable:** Updated `recorder.py`, `transcriber.py`, `app.py`

- [ ] `recorder.py`: catch `sounddevice.PortAudioError` in `start()`; emit `recording_error` with human-readable message; log at `ERROR` level
- [ ] `transcriber.py`: catch `torch.cuda.OutOfMemoryError` (and generic `RuntimeError` containing "CUDA out of memory"); log warning; retry transcription with `device="cpu"`, `compute_type="int8"` — emit `transcription_finished` as normal if CPU retry succeeds
- [ ] `app.py`: on `recording_error` or `transcription_error` show tray balloon with message; log at `ERROR`
- [ ] No unhandled exceptions should crash the process silently

**Acceptance criterion:** Unplug mic → error tray notification appears; CUDA OOM → CPU fallback produces text. (AC-8.2)

---

### Task 8.3 — Auto-start via Windows registry

**Deliverable:** `src/spkup/autostart.py`

- [ ] `enable_autostart(exe_path: str) -> None`: writes `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\spkup` with the path to the launcher
- [ ] `disable_autostart() -> None`: deletes the registry key if it exists
- [ ] `is_autostart_enabled() -> bool`: checks if the key exists
- [ ] Tray context menu gains a checkable **Start on login** action that calls these functions
- [ ] Unit tests: `tests/test_autostart.py` — mock `winreg`; test enable/disable/query

**Acceptance criterion:** Enable → key present in registry; disable → key absent; tray action reflects current state. (AC-8.3)

---

### Task 8.4 — First-run experience

**Deliverable:** Updated `src/spkup/app.py` and `src/spkup/settings_dialog.py`

- [ ] On first launch (config file does not exist yet), open `SettingsDialog` automatically with a welcome banner: "Welcome to spkup. Choose a model and download it to get started."
- [ ] Disable main hotkey listener until a model is confirmed downloaded
- [ ] After successful download, close the first-run dialog and show tray notification: "spkup is ready. Hold [hotkey] to record."

**Acceptance criterion:** Fresh install (no config.json, no cached model) → dialog opens automatically; after download → hotkey works. (AC-8.4)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-8.1 | Log file created with entries | Check `%LOCALAPPDATA%/spkup/spkup.log` after launch |
| AC-8.2 | Error recovery works | Simulate no-mic and CUDA OOM; observe tray notifications |
| AC-8.3 | Auto-start registry key managed correctly | `pytest tests/test_autostart.py` + manual registry check |
| AC-8.4 | First-run dialog opens on fresh install | Delete config and model; relaunch; dialog appears |
