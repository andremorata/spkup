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
- Temporary playback muting during capture was added to Phase 8 on 2026-04-07 and is in scope for this phase only.
- Microphone input device selection (tray submenu + settings combo) and empty-transcription detection were added to Phase 8 on 2026-04-16 and are in scope for this phase only. See Task 8.9.
- Tray single-click recording toggle and redundant trigger suppression were added to Phase 8 on 2026-04-20 and are in scope for this phase only. See Task 8.10.

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

**Acceptance criterion:** Automated coverage is in place, but manual validation is still pending: `pytest tests/ -v` passes and manual hotkey use should support both hold and quick-tap toggle flows. (AC-8.0)

### Task 8.1 — Structured logging

**Deliverable:** `src/spkup/logging_setup.py`

- [x] `configure_logging() -> logging.Logger`: configures root logger with `RotatingFileHandler` to `%LOCALAPPDATA%/spkup/spkup.log` (max 5 MB, 3 backups) and a `StreamHandler` for stderr
- [x] Log format: `%(asctime)s %(levelname)-8s %(name)s — %(message)s`
- [x] Call `configure_logging()` at the top of `__main__.py` before anything else
- [x] Replace any remaining `print()` statements in the codebase with appropriate `logging` calls

**Acceptance criterion:** Implementation is complete, but manual runtime validation is still pending: `spkup.log` should be created after launch and contain startup log entries. (AC-8.1)

---

### Task 8.2 — Error handling

**Deliverable:** Updated `recorder.py`, `transcriber.py`, `app.py`

- [x] `recorder.py`: catch `sounddevice.PortAudioError` in `start()`; emit `recording_error` with human-readable message; log at `ERROR` level
- [ ] `transcriber.py`: catch `torch.cuda.OutOfMemoryError` (and generic `RuntimeError` containing "CUDA out of memory"); log warning; retry transcription with `device="cpu"`, `compute_type="int8"` — emit `transcription_finished` as normal if CPU retry succeeds
- [x] `app.py`: on `recording_error` or `transcription_error` show tray balloon with message; log at `ERROR`
- [ ] No unhandled exceptions should crash the process silently

**Acceptance criterion:** Manual validation is still required for the current implementation: unplug mic → error tray notification appears; CUDA OOM → CPU fallback produces text. (AC-8.2)

---

### Task 8.3 — Auto-start via Windows registry

**Deliverable:** `src/spkup/autostart.py`

- [ ] `enable_autostart(exe_path: str) -> None`: writes `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\spkup` with the path to the launcher
- [x] `disable_autostart() -> None`: deletes the registry key if it exists
- [x] `is_autostart_enabled() -> bool`: checks if the key exists
- [x] Tray context menu gains a checkable **Start on login** action that calls these functions
- [x] Unit tests: `tests/test_autostart.py` — mock `winreg`; test enable/disable/query

**Acceptance criterion:** Automated coverage is in place, but manual registry and tray validation are still pending: enable → key present in registry; disable → key absent; tray action reflects current state. (AC-8.3)

---

### Task 8.4 — First-run experience

**Deliverable:** Updated `src/spkup/app.py` and `src/spkup/settings_dialog.py`

- [x] On first launch (config file does not exist yet), open `SettingsDialog` automatically with a welcome banner: "Welcome to spkup. Choose a model and download it to get started."
- [x] Disable main hotkey listener until a model is confirmed downloaded
- [ ] After successful download, close the first-run dialog and show tray notification: "spkup is ready. Hold [hotkey] to record."

**Acceptance criterion:** Manual first-run validation is still pending: fresh install (no config.json, no cached model) → dialog opens automatically; after download → hotkey works. (AC-8.4)

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

**Acceptance criterion:** Implementation is complete and unit coverage exists, but manual verification is still pending for tray/window behavior: after 6 successful transcriptions, the recent-history window should show the latest 5 entries only; any entry should be copyable or deletable from the window without affecting the remaining entries. (AC-8.5)

---

### Task 8.6 — Temporary playback muting during capture

**Deliverable:** Updated `config.py`, `settings_dialog.py`, `playback_mute.py`, `app.py`, `tests/test_playback_mute.py`, and `tests/test_app_playback_mute.py`

- [x] Add a user-facing setting that temporarily mutes playback output while recording is active
- [x] Apply the temporary mute when capture starts and the setting is enabled
- [x] Restore the pre-capture mute state when recording stops
- [x] Cover both hold-to-record and quick-tap toggle recording paths
- [x] Ensure failure and app-quit paths restore the pre-capture mute state so the machine is not left muted

**Acceptance criterion:** Implementation and automated coverage are in place, but manual Windows validation is still pending: `pytest tests/test_playback_mute.py tests/test_app_playback_mute.py -q` passes and the full local suite rerun `.venv\Scripts\python -m pytest tests\ -q` exits 0. Manual validation is still required for the actual playback endpoint behavior: with the setting enabled, playback output should be muted only while capture is active; stopping capture should restore the exact pre-capture mute state; quick-tap toggle recording should follow the same mute and restore behavior; failure or app quit during active capture should not leave the machine muted. (AC-8.6)

### Task 8.7 — Reliable synthesized sound cues

**Deliverable:** `src/spkup/sound_cues.py`, updated `src/spkup/app.py`, `tests/test_sound_cues.py`

- [x] Replace `winsound.Beep()` cue playback with precomputed PCM cues played via `sounddevice.play(..., blocking=False)`
- [x] Precompute `start`, `transcribing`, and `done` cues at module import time with 5 ms fade envelopes
- [x] Expose `START_CUE_DURATION_MS` for the record-start mute delay path in `app.py`
- [x] Handle `sounddevice.PortAudioError` by logging a warning and skipping playback without crashing the app
- [x] Add unit coverage for cue generation, cue lengths, invalid cue names, and PortAudio playback failures

**Acceptance criterion:** `pytest tests/test_sound_cues.py -q` passes. Manual Windows validation is still required to confirm the cues remain audible when the output device was previously idle. (AC-8.7)

### Task 8.8 — Transcription resilience (watchdog, retry, error UX)

**Deliverable:** Updated `transcriber.py`, `app.py`, `overlay.py`, `config.py`, new `tests/test_transcription_resilience.py`

- [x] Add `transcription_timeout_seconds` (default 300) to `AppConfig`
- [x] Add `ERROR` overlay state (red "Failed" pill, 4s auto-hide)
- [x] Add audio retention in `Transcriber` for retry after failure/timeout
- [x] Add `retry_last(force_cpu=True)` method and `has_pending_retry` property
- [x] Add `cleanup_worker()` method for forcible worker termination
- [x] Add enhanced diagnostic logging with timing at model load, inference start/end
- [x] Add watchdog `QTimer` in `App` that detects hung transcription
- [x] Auto-retry on CPU when CUDA transcription times out
- [x] Show `OverlayState.ERROR` on transcription failure (not just hide)
- [x] Add "Retry last transcription" tray menu action
- [x] Unit and integration tests (15 new tests, 89/89 total pass)

**Acceptance criterion:** Automated test coverage is in place. Manual validation is pending: simulate a hung transcription (or set timeout very low) and verify the ERROR overlay appears, auto-retry fires on CPU, and the "Retry last transcription" tray action works. (AC-8.8)

---

### Task 8.9 — Microphone input selection + empty-transcription detection

Added 2026-04-16 as an explicit Phase 8 scope extension. Addresses two closely related gaps: (A) the app always records from the system default input, with no way for the user to pick a different mic, and (B) when a recording produces an empty transcription (wrong mic, mic muted at the OS level, mic unplugged), the app silently overwrites the clipboard with an empty string and shows a false DONE overlay — giving the user no signal that something went wrong.

**Deliverable:** New `src/spkup/audio_devices.py`; `config.py` gains `input_device` field; `recorder.py` gains `set_device()`; `app.py` wires the device through startup / settings / a new tray submenu, and rewrites `_on_transcription_finished` to detect "long recording → empty text"; `settings_dialog.py` gains a Microphone `QComboBox`; new `tests/test_audio_devices.py` + `tests/test_app_empty_transcription.py`; extended `tests/test_config.py` and `tests/test_recorder.py`.

- [x] Add `input_device: dict | None = None` to `AppConfig`; persist as `{"name": str, "hostapi": str}` so device identity survives reboot, reorder, and hostapi ambiguity. `None` means "system default"
- [x] Add `audio_devices.list_input_devices() / resolve_device(spec) / describe(spec) / spec_from_device(dev)` utilities; filter `max_input_channels > 0`; fall back to system default when the saved device is no longer present
- [x] Add `AudioRecorder.set_device(device)` — takes effect on the next `start()` call (sounddevice has no hot-swap)
- [x] `app.py`: pass resolved device to `AudioRecorder` at startup; add **Microphone** tray submenu with "System default" + per-device entries, rebuilt on `aboutToShow` so hotplug is reflected; re-apply device on settings save
- [x] `settings_dialog.py`: add **Microphone** `QComboBox` above the existing "Device" (GPU/CPU) combo on the General tab
- [x] Capture recording duration via a new slot on `recorder.recording_finished` (connected before the transcriber so it runs first)
- [x] Rework `_on_transcription_finished`: if stripped text is empty AND duration ≥ 5 s → log warning, show `OverlayState.ERROR`, show tray balloon "spkup — No speech detected" prompting the user to check/switch mic; if empty AND duration < 5 s → silent DONE overlay, no clipboard/history write; otherwise normal behaviour
- [x] Tests: 32 targeted (config round-trip for `input_device`, `audio_devices` resolve + enumerate + describe, recorder `set_device`, empty-transcription UX branches). Full suite: 133/133 pass via `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q`

**Acceptance criterion:** Automated test coverage is in place. Manual validation is pending: (1) open the tray Microphone submenu and confirm "System default" plus real devices are listed with the current one checked; change mic and confirm `config.json` now contains `"input_device": {"name": ..., "hostapi": ...}`. (2) Open Settings → Microphone, pick a different device, Save — same effect. (3) Hold the hotkey for ≥ 8 s with a muted or silent device; verify ERROR overlay + tray balloon "No speech detected — check your microphone"; confirm clipboard was NOT overwritten and history was NOT appended to. (4) Short (< 1 s) hotkey tap with no speech produces no warning and no history entry. (AC-8.9)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-8.1 | Log file created with entries | Check `%LOCALAPPDATA%/spkup/spkup.log` after launch |
| AC-8.2 | Error recovery works | Simulate no-mic and CUDA OOM; observe tray notifications |
| AC-8.3 | Auto-start registry key managed correctly | `pytest tests/test_autostart.py` + manual registry check |
| AC-8.4 | First-run dialog opens on fresh install | Delete config and model; relaunch; dialog appears |
| AC-8.5 | Recent-history window manages the last 5 session transcriptions | Perform 6 transcriptions; open tray action; verify copy and delete actions. Not manually validated in this session. |
| AC-8.6 | Playback output is muted only during active capture and the prior mute state is always restored | Enable the setting; verify hold and quick-tap capture mute behavior; stop capture and confirm the previous mute state returns; repeat with a forced failure or app quit during capture. |
| AC-8.7 | Sound cues use synthesized PCM playback instead of `winsound.Beep()` and fail safely when audio playback is unavailable | `pytest tests/test_sound_cues.py -q` passes; on Windows, verify cues remain audible even when the output device was idle before recording starts. |
| AC-8.8 | Transcription watchdog, automatic CPU retry, ERROR overlay, and manual retry tray action all function correctly | Set `transcription_timeout_seconds` to a low value; trigger a transcription; verify timeout detection, auto-CPU-retry, ERROR overlay on final failure, and tray retry action |
| AC-8.9 | User can pick the microphone from both tray and settings, and "long recording with no speech" surfaces a clear warning instead of a silent empty paste | Switch devices from tray and settings; verify `config.json` updates. Record ≥ 8 s on a muted/silent device → ERROR overlay + tray "No speech detected" balloon, no clipboard/history write. |
| AC-8.10 | Single left-click on the tray icon toggles recording through the same lifecycle as the hotkey, and redundant tray/hotkey re-triggers within 1 second after stop/cancel/error/finalize are ignored without blocking a legitimate stop while recording is active | On Windows: left-click tray icon once → RECORDING + start cue; left-click again → stop + transcribe. Right-click still opens the menu. Rapid repeated hotkey presses or tray clicks within 1 second after stop/cancel/error/finalize do not start extra recording/transcription work. Hold-to-record and quick-tap hotkey toggle still behave normally. |

### Task 8.10 — Tray click recording toggle + redundant trigger suppression

Added 2026-04-20 as an explicit Phase 8 scope extension. Addresses two closely related gaps: (A) the app can only start/stop capture from the keyboard even though it already lives in the system tray, and (B) rapid repeated trigger gestures immediately after a recording session can still drive invalid extra processing when the intent is clearly accidental retriggering.

**Deliverable:** Updated `src/spkup/app.py`; new `tests/test_app_trigger_guards.py`; refreshed `docs/01-architecture.md`, `docs/03-testing.md`, and `README.md`

- [x] Add single left-click tray activation using `QSystemTrayIcon.activated` so the tray icon toggles recording on/off
- [x] Keep right-click tray behavior unchanged so the context menu still opens normally
- [x] Route tray and hotkey start/stop requests through shared App-level helpers so both inputs use the same state machine
- [x] Add a fixed 1.0 s suppression window for redundant retriggers after stop/cancel/error/finalize without blocking a legitimate stop while recording is active or start-pending
- [x] Preserve existing side effects for start/stop: tray icon color, sound cues, overlay state, recorder start/stop, playback mute lifecycle, transcription watchdog, and retry-action state
- [x] Add automated app-level regression coverage for tray activation reasons, duplicate start/stop suppression, and the guarantee that hotkey hold and quick-tap toggle flows still use the existing lifecycle

**Automated validation:** `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\test_app_trigger_guards.py tests\test_hotkey.py tests\test_app_playback_mute.py tests\test_app_empty_transcription.py -q` passed 38/38. Full suite rerun: `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q` passed 145/145.

**Acceptance criterion:** Automated coverage is in place and the tray-toggle / trigger-guard behavior is implemented, but manual Windows validation is still required because tray activation is shell-dependent: left-click tray icon once → record; left-click again → stop/transcribe; right-click still opens the menu; rapid repeated hotkey presses or tray clicks within 1 second after stop/cancel/error/finalize do not start extra work; hold-to-record and quick-tap toggle still behave normally. (AC-8.10)
