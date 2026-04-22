# Project Progress Tracker

> Source of truth for high-level delivery status, maintenance tracking, and historical MVP context.

## Current Snapshot

- Lifecycle mode: Maintenance
- Active work item: Manual cancellation of in-progress transcription (`specs/spec-transcription-manual-cancel.issue.md`)
- MVP baseline: Closed and frozen as historical reference
- Last updated: 2026-04-22
- Primary risks: PyQt6 system-tray behaviour differences across Windows builds; CUDA availability for faster-whisper at runtime

## Status Vocabulary

- `Not started`
- `In progress`
- `Blocked`
- `Completed (declared)`
- `Completed (validated)`
- `Closed (historical baseline)`

## Open Maintenance Board

| Work Item | File | Status | GitHub Issue | Last Updated | Notes |
| --- | --- | --- | --- | --- | --- |
| Manual Cancellation of In-Progress Transcription | `specs/spec-transcription-manual-cancel.issue.md` | Completed (declared) | TBD | 2026-04-22 | Hotkey-first slice shipped. Discard-only cancel via `App._cancel_active_transcription`; tray click during transcription is routed through the same entry point. Overlay cancel button remains future work. Manual Windows verification pending. |
| Nightly Release Automation | `specs/spec-nightly-release-automation.issue.md` | Completed (declared) | [#1](https://github.com/andremorata/spkup/issues/1) | 2026-04-20 | `.github/workflows/nightly.yml` created; `release.yml` guarded with `github.actor` check. Pending first live schedule run for validation. |

## Historical MVP Roadmap

| Phase | Scope | Status | Last Updated | Evidence / Notes | Next Action |
| --- | --- | --- | --- | --- | --- |
| 1 | Project setup + core skeleton | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 2 | Global hotkey (press-and-hold) | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 3 | Audio recording | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 4 | Transcription engine | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 5 | Visual overlay | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 6 | Clipboard + full signal wiring | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 7 | Settings dialog | Closed (historical baseline) | 2026-04-20 | Historical MVP phase record retained for reference. Original validation evidence remains below. | Do not extend; open a new spec if related follow-up work is needed |
| 8 | Polish + recent transcription history + temporary playback muting during capture + microphone input selection + tray click recording toggle + redundant trigger suppression | Closed (historical baseline) | 2026-04-20 | This phase accumulated several late-MVP enhancements. Remaining follow-up validation or enhancement work must now be reopened as a dedicated maintenance item instead of extending Phase 8. | Open a new spec / requirement for any follow-up validation or enhancement |
| 9 | Packaging + release readiness | Closed (historical baseline) | 2026-04-20 | Packaging, CI, versioning, and release automation landed during the original roadmap. Any future packaging or release-process work must now be tracked outside Phase 9. | Open a new spec / requirement for any release-process improvement or validation gap |

## Validation Notes

To mark a maintenance work item as `Completed (validated)`, record:

1. Acceptance criteria satisfied.
2. Verification commands or checks performed.
3. Key files changed.
4. Date and short validation summary.

## Evidence Log

- 2026-04-22: Manual Cancellation of In-Progress Transcription — hotkey-first slice implemented. `Transcriber.clear_retry_state()` added. `App._transcribing_active` state plus `App._cancel_active_transcription(source)` added as the single app-level cancel entry point. `_request_recording_start` now routes hotkey and tray start triggers received during transcription through cancel instead of starting a new recording. Retained audio is cleared on cancel so retry is not offered, the overlay returns to HIDDEN, the watchdog is stopped, and the existing 1-second trigger-suppression window is armed. No overlay affordance was added in this slice; a future overlay cancel button must call `_cancel_active_transcription`. Delivery classification: discard-only (late worker results are ignored via existing job-id logic; the inference thread is not hard-killed). New tests: `tests/test_app_transcription_cancel.py` (17). `tests/test_app_trigger_guards.py` stub updated to seed `_transcribing_active`. Automated validation: `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests/ -q` passed 162/162. Manual Windows verification of end-to-end cancel gesture, overlay transitions, and clean restart after cancel is still pending.
- 2026-04-22: Opened a new maintenance spec for manual cancellation of in-progress transcription: `specs/spec-transcription-manual-cancel.issue.md`. Recommendation recorded: implement hotkey-first cancellation during transcription only, while preserving existing watchdog, retry, error, history, clipboard, and trigger-guard flows and keeping a future overlay cancel button on the same App-level cancel entry point. This was a planning/spec update only; no implementation or validation was performed in this session.
- 2026-04-01: Phase 1 validated. Requirements install passed; editable install passed after hatchling backend fix; `pytest tests/test_config.py -v` passed (4/4); `python -m spkup` started successfully.
- 2026-04-01: Phase 2 validated. `tests/test_hotkey.py` passed 10/10; `python -m spkup` confirmed single start/stop per hotkey gesture, no repeat flooding.
- 2026-04-01: Phase 3 validated. `pytest tests/test_recorder.py` 4/4 passed; full suite 18/18 passed; `from spkup.app import App` imports cleanly; no diagnostics in recorder.py, app.py, or test_recorder.py.
- 2026-04-01: Phases 4–7 validated. faster-whisper CUDA pipeline, overlay, clipboard, settings dialog all implemented in one session; `python -m spkup` runs successfully; full suite 28/28 passed (commit 91d7c10). CUDA DLL fix applied (commit 45a227b). Overlay top/bottom-center + audio cues added (commit 7cbf627).
- 2026-04-01: Phase 8 in progress. logging_setup.py (RotatingFileHandler), autostart.py (winreg), test_autostart.py (5 tests) created. __main__.py updated. recorder/transcriber/settings_dialog/app.py updated with logging, PortAudioError handling, CUDA OOM CPU fallback, first-run UX, autostart tray menu. hotkey.py now supports quick-tap toggle recording in addition to hold-to-record, with tests covering both paths.
- 2026-04-01: Toggle recording mode validated. `.venv\Scripts\python -m pytest tests/ -v` passed 35/35 after adding two hotkey regression tests for hold-release and quick-tap lock/unlock behavior.
- 2026-04-01: Phase 8 scope extended. Recent transcription history was explicitly added to Phase 8 as a new in-progress task: keep the last 5 session transcriptions in memory, expose them via a tray action that opens a recent-history window, and support copy/delete per entry.
- 2026-04-01: Recent transcription history implemented. `transcription_history.py`, `transcription_history_window.py`, and `tests/test_transcription_history.py` added; `app.py` wires tray access plus session-scoped add/delete refresh. In-session full suite passed 42/42 via `.venv\Scripts\python -m pytest tests/ -v`. Editor diagnostics are clean for `app.py`, `transcription_history.py`, `transcription_history_window.py`, and `tests/test_transcription_history.py`. Manual verification of tray/window behavior was not performed in this session, so Phase 8 remains in progress.
- 2026-04-01: Phase 8 automated validation rerun recorded. `.venv\Scripts\python -m pytest tests/ -v` passed 42/42. No manual validation was performed in this run; Phase 8 remains in progress pending tray/window verification.
- 2026-04-01: Progress tracker updated to reflect planned Phase 9. Added a blocked Phase 9 row for packaging and release readiness, explicitly gated on Phase 8 validation. This was a planning/spec update only; no Phase 9 implementation or packaging validation was performed.
- 2026-04-07: Phase 8 scope extended. Added a planned Phase 8 feature for temporarily muting playback output during active capture, restoring the prior mute state when capture ends, covering the quick-tap toggle path, and ensuring failure/quit safety so the machine is not left muted. This was a planning/spec update only; no implementation or validation was performed in this session.
- 2026-04-07: Phase 8 / Task 8.6 implemented and automated validation recorded. `config.py` adds `mute_playback_while_recording: bool = False`; `playback_mute.py` implements `PlaybackMuteController` + `WindowsPlaybackMuteBackend`; `settings_dialog.py` adds the user-facing checkbox; `app.py` wires delayed mute on start cue plus restore on stop, recording error, and cleanup; `tests/test_playback_mute.py` and `tests/test_app_playback_mute.py` cover controller behavior and app lifecycle restore paths. Earlier in-session targeted tests passed 11/11 and the full suite passed 59/59; the latest local rerun `.venv\Scripts\python -m pytest tests\ -q` exited 0. Manual Windows validation of actual playback-mute behavior was not performed in this session, so Phase 8 remains in progress.
- 2026-04-09: Phase 8 / Task 8.7 implemented. `sound_cues.py` now synthesizes and precomputes the start, transcribing, and done PCM cues with 5 ms fades, `app.py` uses `sounddevice.play(...)` instead of `winsound.Beep()`, and `tests/test_sound_cues.py` covers cue generation and failure-safe playback behavior. Manual Windows validation is still required to confirm cue audibility when the output device starts in an idle state.
- 2026-04-09: Phase 8 / Task 8.7 automated validation recorded against the workspace source tree because the current venv imports `spkup` from `site-packages` by default. `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\test_sound_cues.py tests\test_app_playback_mute.py -q` passed (15/15), and `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q` passed (74/74).
- 2026-04-09: Phase 8 Task 8.8 implemented. Transcription resilience: watchdog timer (configurable `transcription_timeout_seconds`, default 300s), audio retention for retry, `OverlayState.ERROR` ("Failed" pill, 4s auto-hide), automatic CUDA→CPU fallback on timeout, "Retry last transcription" tray action, enhanced diagnostic logging with timing. 15 new tests added; full suite 89/89 passed.
- 2026-04-16: Phase 8 scope extended. Task 8.9 added: microphone input selection + empty-transcription detection. New `src/spkup/audio_devices.py` (device enumeration + `{name, hostapi}` spec resolution with graceful fallback to system default); `AppConfig.input_device: dict | None`; `AudioRecorder.set_device()`; tray **Microphone** submenu populated on `aboutToShow` (handles hotplug) plus settings-dialog **Microphone** `QComboBox`; recording-duration capture; `_on_transcription_finished` rewritten so that empty text + ≥ 5 s recording emits `OverlayState.ERROR` and a "spkup — No speech detected" tray balloon, while empty text + < 5 s is silent — in both cases the clipboard is no longer overwritten with empty and history is no longer spammed. New tests: `tests/test_audio_devices.py` (11), `tests/test_app_empty_transcription.py` (6), plus extensions in `tests/test_config.py` (+3) and `tests/test_recorder.py` (+2). `tests/test_transcription_resilience.py` stub extended with `_last_recording_duration`. Full suite 133/133 passed via `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q`. Manual Windows validation of AC-8.9 (tray/settings mic switching + warning on muted device) is still pending.
- 2026-04-20: Phase 8 scope extended. Task 8.10 added: tray single-click recording toggle + redundant trigger suppression. Planned implementation: wire `QSystemTrayIcon.activated` in `app.py`, route tray and hotkey requests through the same App-level start/stop helpers, and ignore redundant start requests for 1 second after stop/cancel/error/finalize without blocking a legitimate stop while recording is active. This entry records the scope addition only; implementation, automated validation, and manual Windows tray verification are still pending.
- 2026-04-20: Phase 8 / Task 8.10 implemented. `app.py` now wires `QSystemTrayIcon.activated` so single left-click toggles recording through the same App-level request helpers used by the hotkey. A shared 1-second suppression window now ignores redundant start retriggers after stop/cancel/error/finalize while still allowing a legitimate stop during active or pending recording. New `tests/test_app_trigger_guards.py` covers tray activation reasons, request gating, and suppression-window arming. Docs updated: `docs/01-architecture.md`, `docs/03-testing.md`, `README.md`. Automated validation passed: `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\test_app_trigger_guards.py tests\test_hotkey.py tests\test_app_playback_mute.py tests\test_app_empty_transcription.py -q` (38/38) and `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q` (145/145). Manual Windows tray validation remains pending.
- 2026-04-20: Project lifecycle updated to maintenance mode. The original MVP roadmap (`phase1` through `phase9`) is now treated as closed historical baseline. From this point forward, new functionality, extensions, and follow-up validation work must be tracked as new spec / requirement issues in `specs/` rather than by extending the original phases.
