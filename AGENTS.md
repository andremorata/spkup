# spkup — Contributor & Agent Guide

> This file is the source of truth for humans and AI agents working in this repo.
> `CLAUDE.md` and `.github/copilot-instructions.md` are symlinks to it — edit this file only.

## What spkup is

Push-to-talk speech-to-text desktop app. Hold a global hotkey (or single-click the
tray/menu-bar icon), speak, release — the transcription lands in the clipboard.
Inference runs locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper);
no cloud, no API key.

- Single-process Python 3.12 app built on PyQt6 (tray, overlay, settings, clipboard).
- Audio via `sounddevice` (PortAudio); hotkey via `pynput`; audio stays in memory as numpy arrays.
- **Windows 11 x64** is the GPU-accelerated production baseline (NVIDIA CUDA/cuDNN bundled).
- **macOS ARM64 / Apple Silicon** is CPU-oriented and additive — it must never regress the Windows baseline.

Architecture, threading model, and module responsibilities live in `docs/architecture.md`.
Read it before any structural change.

## Layout

```
src/spkup/        # application code (see docs/architecture.md for the module map)
spkup/            # repo-root import shim so `python -m spkup` resolves the local checkout
tests/            # pytest suite (mirrors src module names)
docs/             # architecture, testing, observability, packaging-release
spkup.spec        # PyInstaller spec — Windows
spkup-macos.spec  # PyInstaller spec — macOS ARM64
run.bat           # Windows launch helper
```

## Build / run / test

```bash
# dev install
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,build]"                  # Windows: pip install -r requirements.txt

# run
python -m spkup

# test (Qt code needs the offscreen platform)
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest tests/ -q
```

Package and release: see `docs/packaging-release.md`. The version contract is single-source:
`__version__` in `src/spkup/__init__.py` drives the `vX.Y.Z` git tag and the
`spkup-X.Y.Z-{windows-x64,macos-arm64}.zip` artifact names. Don't introduce a second version source.

## Threading rules (critical — get this wrong and the app crashes)

- **Never** call a `QWidget` / `QApplication` method from a non-Qt thread.
- `pynput` callbacks run on a background thread → cross to the main thread with
  `QMetaObject.invokeMethod(..., Qt.ConnectionType.QueuedConnection)`.
- `QThread` workers (transcription, model download, update check/download) return results
  **only** via `pyqtSignal`.

## Testing rules

- Write tests alongside the change, not after. A change isn't done until its tests pass.
- Pure logic (`config`, `hotkey` parsing, `recorder` lifecycle, `platform_support`,
  history, update selection, packaging validation) → unit tests.
- Qt painting, real audio I/O, and CUDA inference are verified manually — see
  `docs/testing.md` for the unit-vs-manual split and the per-module manual checklist.
- Exempt from new tests: docs, comments, renames, formatting, config-only tweaks.

## Keep docs in sync

When you change code, update the doc that owns that concern in the same session:

| Changed | Update |
| --- | --- |
| Config schema (`AppConfig`) | `docs/architecture.md` §Configuration |
| New module / threading boundary | `docs/architecture.md` (module map, threading model) |
| New architectural decision | `docs/architecture.md` §Architectural Decisions (or `docs/adr/` if substantial) |
| Platform path / artifact / capability | `docs/architecture.md`, `docs/testing.md`, `docs/packaging-release.md` |
| Logging behavior | `docs/observability.md` |
| User-facing behavior or setup | `README.md` and `CHANGELOG.md` |

## Confirm before

- Adding a dependency (`pyproject.toml` / `requirements.txt`).
- Changing the `AppConfig` schema or defaults.
- Touching threading boundaries or signal wiring in `app.py`.
- Changing the release version contract or platform support matrix.
- Deleting or rewriting a file with existing content.

## How work is tracked

GitHub Issues for tasks and bugs; a one-line entry in `CHANGELOG.md` per user-visible
change; `docs/adr/` for durable design decisions worth explaining later. Git history is
the record of how things were built — don't reconstruct it in tracking files.
