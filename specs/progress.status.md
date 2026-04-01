# Project Progress Tracker

> Source of truth for high-level delivery status in projects created from this scaffold.

## Current Snapshot

- Active phase: Phase 9 — Packaging + release readiness
- Overall status: In progress
- Last updated: 2026-04-01
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
| 8 | Polish | Completed (validated) | 2026-04-01 | logging_setup.py, autostart.py, test_autostart.py created; recorder/transcriber/app/settings_dialog updated; CUDA OOM fallback; first-run UX; hotkey toggle mode added for quick-tap lock/unlock recording; recent transcription history implemented in app.py, transcription_history.py, and transcription_history_window.py; automated validation already recorded with `.venv\Scripts\python -m pytest tests/ -v` passing 42/42; user-confirmed remaining manual Phase 8 checks passed on 2026-04-01 | Handoff to Phase 9 |
| 9 | Packaging + release readiness | Not started | 2026-04-01 | Phase unblocked after Phase 8 validation; ready to begin when scheduled | Begin Phase 9 when ready |

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
- 2026-04-01: Remaining manual Phase 8 validation checks passed. Automated validation had already been recorded with `.venv\Scripts\python -m pytest tests/ -v` passing 42/42, and user-confirmed manual Phase 8 checks now complete; Phase 8 is validated and Phase 9 is unblocked.
