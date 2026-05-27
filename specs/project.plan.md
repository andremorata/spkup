# spkup — Project Plan

> Master planning document for spkup.
> Supersedes `PLAN.md` (deleted). Source of truth for stack, historical MVP phases, and post-MVP delivery sequencing.

---

## 1. Project Summary

- **Project name:** spkup
- **Problem statement:** Capture voice via a global push-to-talk hotkey, transcribe it locally with a Whisper model, and paste the result into the clipboard — always available from the system tray.
- **Success definition:** Hold a hotkey → speak → release → transcribed text is in the clipboard within a few seconds, with visual feedback via an on-screen overlay.
- **Primary users:** Single user (personal tool), Windows 11, RTX 4070 (8 GB VRAM).
- **Lifecycle mode:** Maintenance mode as of 2026-04-20. The original MVP build-out is considered complete and frozen as historical baseline.
- **Delivery constraints:** No server infrastructure. Current production baseline is a local-first Windows desktop app. macOS ARM64 support is planned as a post-MVP maintenance extension. Packaging, CI/CD, versioning, and distribution are part of the current baseline.
- **Change policy:** New non-trivial work must be tracked as a new spec or requirement in `specs/`; do not extend `phase1` through `phase9`.

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
| Packaging | PyInstaller | Implemented | Windows frozen-build baseline exists; future refinements should be tracked as maintenance items |
| CI/CD | GitHub Actions | Implemented | CI and tagged-release workflows exist |
| Versioning | `X.Y.Z` + Git tags `vX.Y.Z` | Implemented | Source version in `src/spkup/__init__.py`; release tags align to source version |
| Distribution | GitHub Releases | Implemented | Tagged release workflow publishes the Windows artifact |
| Target platforms | Windows 11 x64; macOS ARM64 | Windows implemented; macOS implementation in validation | macOS ARM64 support is tracked in `specs/spec-macos-arm64-support.issue.md` |
| License | No constraints | Confirmed | Personal tool |

---

## 3. Working Assumptions

- Audio never touches disk — stays as numpy arrays in memory.
- `language=None` in faster-whisper for auto-detect; handles mixed PT+EN code-switching.
- Model is lazy-loaded on first transcription to avoid consuming VRAM at startup.
- `large-v3` with `float16` fits in 8 GB VRAM; fallback to CPU on OOM.
- Hotkey config persists in `%APPDATA%/spkup/config.json` on Windows and `~/Library/Application Support/spkup/config.json` on macOS.
- Model cache is stored in `%LOCALAPPDATA%/spkup/models` on Windows and `~/Library/Caches/spkup/models` on macOS.

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

## 5. Original MVP Delivery Phases

| Phase | Scope | Issue File |
| --- | --- | --- |
| 1 | Project setup + core skeleton | `specs/phase1.issue.md` |
| 2 | Global hotkey (press-and-hold) | `specs/phase2.issue.md` |
| 3 | Audio recording | `specs/phase3.issue.md` |
| 4 | Transcription engine | `specs/phase4.issue.md` |
| 5 | Visual overlay | `specs/phase5.issue.md` |
| 6 | Clipboard + full signal wiring | `specs/phase6.issue.md` |
| 7 | Settings dialog | `specs/phase7.issue.md` |
| 8 | Polish + recent transcription history + temporary playback muting during capture + microphone input selection + tray click recording toggle + redundant trigger suppression | `specs/phase8.issue.md` |
| 9 | Packaging + GitHub CI/CD + versioning + releases | `specs/phase9.issue.md` |

---

## 6. Post-MVP Maintenance Workflow

- The phase files above are historical records of how the MVP was built. They are kept for traceability, not as the place for new scope.
- Every new incremental feature, bug-fix bundle, packaging improvement, release-process change, or behavior-changing refactor should start as a dedicated issue file in `specs/`, normally from `specs/spec-template.issue.md`.
- If a new request materially changes roadmap priorities, update this plan and `specs/progress.status.md` before implementation.
- Historical references may still point to the original phases, but new work must not be added to them.

---

## 7. Key Design Decisions

| Date | Decision | Notes |
| --- | --- | --- |
| 2026-04-01 | No WAV files | Audio stays as numpy arrays; passed directly to faster-whisper |
| 2026-04-01 | `language=None` | Auto-detect for best PT+EN code-switching support |
| 2026-04-01 | Lazy model load | Don't consume 3 GB VRAM until first use |
| 2026-04-01 | pynput over `keyboard` lib | Distinct on_press/on_release callbacks; no admin required |
| 2026-04-01 | QThread for transcription | Never block the UI thread during inference |
| 2026-04-01 | TDD for core modules | Tests written alongside config, hotkey, recorder, transcriber |
| 2026-04-01 | Release contract baseline | PyInstaller Windows build, GitHub Actions CI/release automation, `X.Y.Z` source version aligned to `vX.Y.Z` tags, and GitHub Releases as the distribution channel |
| 2026-04-20 | Maintenance mode | Original MVP phases frozen as historical baseline; all new work enters through new spec / requirement issues |

---

## 8. Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| PyQt6 tray behaviour differences across Windows builds | Medium | Test on target machine only; personal tool | Open |
| CUDA OOM if model size changes | Medium | Catch `OutOfMemoryError`; fallback to CPU | Open |
| Transcription hangs on cold boot / CUDA init | Medium | Watchdog timer (300s default); auto-retry on CPU; manual retry via tray | Mitigated |
| pynput requires no admin but may miss keys if focus is unusual | Low | Document known limitation; test common apps | Open |
| macOS permissions and unsigned app distribution | Medium | Document Accessibility/Input Monitoring and Microphone permissions; defer signing/notarization to a separate item | Planned |

---

## 9. Current Checklist

- [x] Stack documented and confirmed
- [x] Historical MVP phases recorded for traceability
- [x] Testing strategy agreed (TDD, pytest)
- [x] Observability approach agreed (file logging)
- [x] Maintenance mode decision documented
- [x] Post-MVP spec / requirement workflow defined
- [x] Nightly release automation maintenance item opened in `specs/`
- [x] Nightly automation now publishes normal GitHub Releases for frequent app updates
- [x] Manual cancellation of in-progress transcription maintenance item opened in `specs/`
- [x] Recording-limit visibility maintenance item opened in `specs/`
- [x] Recording overlay shows remaining capture time before the existing safety cutoff
- [x] Manual cancellation of in-progress transcription delivered as a hotkey-first slice with a shared app-level cancel entry point ready for a future overlay button
- [x] Startup auto-update maintenance item opened in `specs/`
- [x] macOS ARM64 support maintenance item opened in `specs/`
- [x] macOS ARM64 implementation path added; validation remains open before support is marked complete
