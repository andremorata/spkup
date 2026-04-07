# Project Progress Tracker

> Source of truth for high-level delivery status in projects created from this scaffold.

## Current Snapshot

- Active phase: Phase 8 — Polish
- Overall status: In progress
- Last updated: 2026-04-07
- Primary risks: PyQt6 system-tray behaviour differences across Windows builds; CUDA availability for faster-whisper at runtime

## Status Vocabulary

- `Not started`
- `In progress`
- `Blocked`
- `Completed (declared)`
- `Completed (validated)`

## Phase Board

| Phase | Scope | Status | Last Updated | Evidence / Notes | Next Action |
| --- | --- | --- | --- | --- | --- |
| 1 | Project setup + core skeleton | Completed (validated) | 2026-04-01 | Requirements install passed; editable install passed after hatchling backend fix; `pytest tests/test_config.py -v` passed (4/4); `python -m spkup` started successfully | Handoff to Phase 2 |
| 2 | Global hotkey (press-and-hold) | Completed (validated) | 2026-04-01 | `tests/test_hotkey.py` passes (10/10); `python -m spkup` confirmed single start on hold, single stop on release, no flooding | Handoff to Phase 3 |
| 3 | Audio recording | Completed (validated) | 2026-04-01 | `pytest tests/test_recorder.py` 4/4 passed; full suite 18/18 passed; `from spkup.app import App` imports cleanly; no linter errors in recorder.py, app.py, test_recorder.py | Handoff to Phase 4 |
| 4 | Transcription engine | Completed (validated) | 2026-04-01 | faster-whisper CUDA pipeline; model_manager.py, transcriber.py; full suite 28/28 passed | Handoff to Phase 5 |
| 5 | Visual overlay | Completed (validated) | 2026-04-01 | overlay.py; top-center/bottom-center positions; winsound audio cues; 28/28 passed | Handoff to Phase 6 |
| 6 | Clipboard + full signal wiring | Completed (validated) | 2026-04-01 | clipboard.py; full recording→transcription→clipboard pipeline wired in app.py; 28/28 passed | Handoff to Phase 7 |
| 7 | Settings dialog | Completed (validated) | 2026-04-01 | settings_dialog.py; model download worker; hotkey capture widget; overlay position selector; 28/28 passed | Handoff to Phase 8 |
| 8 | Polish + recent transcription history + temporary playback muting during capture | In progress | 2026-04-07 | Recent transcription history and playback muting are implemented. Task 8.6 adds `mute_playback_while_recording` config, `playback_mute.py`, a settings checkbox, and app lifecycle restore-on-stop/error/quit wiring. Automated validation exists in `tests/test_playback_mute.py` and `tests/test_app_playback_mute.py`; the latest local full-suite rerun `.venv\Scripts\python -m pytest tests\ -q` exited 0. Manual Windows validation is still pending for recent-history tray/window behavior and AC-8.6 playback-mute behavior. | Perform the remaining manual Windows validation for Phase 8, especially recent-history tray/window behavior and playback-mute behavior, then reassess Phase 8 status |
| 9 | Packaging + release readiness | Blocked | 2026-04-01 | Planned next phase only; blocked until Phase 8 validation is complete | Finish Phase 8 validation, then begin Phase 9 implementation |

## Validation Notes

To mark a phase as `Completed (validated)`, record:

1. Acceptance criteria satisfied.
2. Verification commands or checks performed.
3. Key files changed.
4. Date and short validation summary.

## Evidence Log

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
