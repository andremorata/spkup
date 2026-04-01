# Project Progress Tracker

> Source of truth for high-level delivery status in projects created from this scaffold.

## Current Snapshot

- Active phase: Phase 3 — Audio Recording
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
| 3 | Audio recording | In progress | 2026-04-01 | Issue: `specs/phase3.issue.md` | Implement tasks 3.1–3.3 |
| 4 | Transcription engine | Not started | | Issue: `specs/phase4.issue.md` | After Phase 3 validated |
| 5 | Visual overlay | Not started | | Issue: `specs/phase5.issue.md` | After Phase 4 validated |
| 6 | Clipboard + full signal wiring | Not started | | Issue: `specs/phase6.issue.md` | After Phase 5 validated |
| 7 | Settings dialog | Not started | | Issue: `specs/phase7.issue.md` | After Phase 6 validated |
| 8 | Polish | Not started | | Issue: `specs/phase8.issue.md` | After Phase 7 validated |

## Validation Notes

To mark a phase as `Completed (validated)`, record:

1. Acceptance criteria satisfied.
2. Verification commands or checks performed.
3. Key files changed.
4. Date and short validation summary.

## Evidence Log

- 2026-04-01: Phase 1 validated. Requirements install passed; editable install passed after hatchling backend fix; `pytest tests/test_config.py -v` passed (4/4); `python -m spkup` started successfully.
- 2026-04-01: Phase 2 validated. `tests/test_hotkey.py` passed 10/10; `python -m spkup` confirmed single start/stop per hotkey gesture, no repeat flooding.
