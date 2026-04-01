# spkup — Project Plan

> Master planning document for spkup.
> Supersedes `PLAN.md` (deleted). Source of truth for phases, stack, and delivery sequencing.

---

## 1. Project Summary

- **Project name:** spkup
- **Problem statement:** Capture voice via a global push-to-talk hotkey, transcribe it locally with a Whisper model, and paste the result into the clipboard — always available from the system tray.
- **Success definition:** Hold a hotkey → speak → release → transcribed text is in the clipboard within a few seconds, with visual feedback via an on-screen overlay.
- **Primary users:** Single user (personal tool), Windows 11, RTX 4070 (8 GB VRAM).
- **Delivery constraints:** No server infrastructure. Local-first Windows desktop app. Packaging, CI/CD, versioning, and distribution are planned for Phase 9 and are not implemented yet.

---

## 2. Stack

| Layer | Choice | Status | Notes |
| --- | --- | --- | --- |
| GUI / tray | PyQt6 ≥ 6.6 | Confirmed | System tray, overlay, clipboard, signals |
| Inference | faster-whisper ≥ 1.0 (CTranslate2) | Confirmed | CUDA, float16, large-v3 |
| Audio capture | sounddevice ≥ 0.4 (PortAudio) | Confirmed | 16 kHz mono float32 |
| Hotkey | pynput ≥ 1.7 | Confirmed | Distinct press/release, no admin required |
| Audio buffer | numpy ≥ 1.26 | Confirmed | Arrays passed directly to faster-whisper |
| Language | Python 3.12 | Confirmed | Host install, venv |
| Dev environment | Host Windows 11, `.venv` | Confirmed | No dev container |
| Infrastructure | Local only | Confirmed | No cloud, no Docker |
| Observability | File logging | Confirmed | `%LOCALAPPDATA%/spkup/spkup.log` |
| Testing | pytest, TDD | Confirmed | Unit tests for core logic, written alongside implementation |
| Packaging | PyInstaller | Planned | Baseline frozen Windows build for Phase 9; not implemented yet |
| CI/CD | GitHub Actions | Planned | Phase 9 target for build, test, and release automation; no workflows yet |
| Versioning | `X.Y.Z` + Git tags `vX.Y.Z` | Planned | Planned release convention for Phase 9; not implemented yet |
| Distribution | GitHub Releases | Planned | Planned release channel for packaged builds; not configured yet |
| License | No constraints | Confirmed | Personal tool |

---

## 3. Working Assumptions

- Audio never touches disk — stays as numpy arrays in memory.
- `language=None` in faster-whisper for auto-detect; handles mixed PT+EN code-switching.
- Model is lazy-loaded on first transcription to avoid consuming VRAM at startup.
- `large-v3` with `float16` fits in 8 GB VRAM; fallback to CPU on OOM.
- Hotkey config persisted in `%APPDATA%/spkup/config.json`.
- Model cache stored in `%LOCALAPPDATA%/spkup/models`.

---

## 4. Signal Flow

```
Hotkey held       → recording_started  → Overlay(RECORDING) + Recorder.start()
Hotkey released   → recording_stopped  → Recorder.stop()
Quick tap         → recording_started  → Recorder stays active in toggle mode
Hotkey tapped again → recording_stopped → Recorder.stop()
                      → recording_finished(audio) → Overlay(TRANSCRIBING) + Transcriber.transcribe(audio)
                          → transcription_finished(text) → RecentHistory.push(text) + Clipboard.copy(text) + Overlay(DONE)
```

---

## 5. Delivery Phases

| Phase | Scope | Issue File |
| --- | --- | --- |
| 1 | Project setup + core skeleton | `specs/phase1.issue.md` |
| 2 | Global hotkey (press-and-hold) | `specs/phase2.issue.md` |
| 3 | Audio recording | `specs/phase3.issue.md` |
| 4 | Transcription engine | `specs/phase4.issue.md` |
| 5 | Visual overlay | `specs/phase5.issue.md` |
| 6 | Clipboard + full signal wiring | `specs/phase6.issue.md` |
| 7 | Settings dialog | `specs/phase7.issue.md` |
| 8 | Polish + recent transcription history | `specs/phase8.issue.md` |
| 9 | Planned packaging + GitHub CI/CD + versioning + releases | `specs/phase9.issue.md` |

---

## 6. Key Design Decisions

| Date | Decision | Notes |
| --- | --- | --- |
| 2026-04-01 | No WAV files | Audio stays as numpy arrays; passed directly to faster-whisper |
| 2026-04-01 | `language=None` | Auto-detect for best PT+EN code-switching support |
| 2026-04-01 | Lazy model load | Don't consume 3 GB VRAM until first use |
| 2026-04-01 | pynput over `keyboard` lib | Distinct on_press/on_release callbacks; no admin required |
| 2026-04-01 | QThread for transcription | Never block the UI thread during inference |
| 2026-04-01 | TDD for core modules | Tests written alongside config, hotkey, recorder, transcriber |
| 2026-04-01 | Planned Phase 9 release direction | PyInstaller baseline frozen Windows build; GitHub Actions for CI/release automation; version numbers `X.Y.Z` aligned to Git tags `vX.Y.Z`; GitHub Releases as the distribution channel. Planned only, not implemented yet |

---

## 7. Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| PyQt6 tray behaviour differences across Windows builds | Medium | Test on target machine only; personal tool | Open |
| CUDA OOM if model size changes | Medium | Catch `OutOfMemoryError`; fallback to CPU | Open |
| pynput requires no admin but may miss keys if focus is unusual | Low | Document known limitation; test common apps | Open |

---

## 8. Readiness Checklist

- [x] Stack documented and confirmed
- [x] Phases defined with issue files
- [x] Testing strategy agreed (TDD, pytest)
- [x] Observability approach agreed (file logging)
- [ ] Phase 1 validated
- [ ] Phase 2 validated
- [ ] Phase 3 validated
- [ ] Phase 4 validated
- [ ] Phase 5 validated
- [ ] Phase 6 validated
- [ ] Phase 7 validated
- [ ] Phase 8 validated
- [ ] Phase 9 validated
