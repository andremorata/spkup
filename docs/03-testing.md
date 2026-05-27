# spkup — Testing Strategy

> Quality approach for a personal desktop tool: TDD for core logic, repeatable automated checks locally and in CI where practical, and manual verification for UI and hardware integration.

---

## 1. Philosophy

Validation starts locally and is reinforced by CI for checks that are practical to automate outside a live Windows desktop session. The test suite exists for two reasons:

1. **Prevent regressions** — core logic is easy to break silently; tests catch that instantly.
2. **Drive design** — writing tests first for pure logic (parsing, config, state machines) produces cleaner interfaces.

Testing effort is proportional to testability. Pure logic gets automated tests that run locally and in CI. Hardware-dependent or Qt-dependent code still gets manual verification on the target Windows and macOS machines.

---

## 2. Framework and Layout

| Area | Tooling |
| --- | --- |
| Test runner | pytest |
| Mocking | `unittest.mock` (stdlib) |
| Qt event loop in tests | Not used — Qt-dependent code is tested manually |
| Test directory | `tests/` at project root |

Run tests:

```bash
cd e:\spkup
.venv\Scripts\activate
pytest
```

---

## 3. What Gets Unit Tests

| Module | Test file | What to test |
| --- | --- | --- |
| `config.py` | `tests/test_config.py` | Load defaults, round-trip save/load, unknown keys ignored, missing file creates defaults |
| `hotkey.py` (parser) | `tests/test_hotkey.py` | Valid combos, single key, modifier ordering, invalid strings raise `ValueError` |
| `recorder.py` | `tests/test_recorder.py` | Stop before start is safe, `recording_finished` emitted, safety timer fires, dtype is float32 |
| `model_manager.py` | `tests/test_model_manager.py` | Cache dir creation, path construction, `is_downloaded` with mock filesystem |
| `clipboard.py` | `tests/test_clipboard.py` | `setText` called with correct string (mock `QApplication.clipboard()`) |
| `platform_support.py` | `tests/test_platform_support.py` | Platform tags, paths, feature capabilities, and artifact names |
| platform-sensitive imports | `tests/test_platform_imports.py` | Config, logging, model manager, autostart, updater, and playback modules import on macOS without Windows-only env/modules |
| `autostart.py` | `tests/test_autostart.py` | Enable/disable/query with mocked `winreg`; unsupported-platform behavior |
| `playback_mute.py` | `tests/test_playback_mute.py` | Snapshot/restore behavior, already-muted path, backend failure handling, restore retry, re-entry guard |
| `app.py` (playback-mute lifecycle) | `tests/test_app_playback_mute.py` | Begin-recording mute path, delayed-start no-op path, stop/error/cleanup restore behavior with mocked Qt-heavy dependencies |
| `app.py` (tray toggle + trigger guards) | `tests/test_app_trigger_guards.py` | Tray activation reasons, shared start/stop request gating, redundant trigger suppression after cancel/error/finalize, legitimate stop while active |
| `app.py` (manual transcription cancel) | `tests/test_app_transcription_cancel.py` | Hotkey/tray start triggers during the transcribing state route through the single `_cancel_active_transcription` entry point; canceled jobs skip clipboard/history, hide the overlay, disable retry, and arm the suppression window; `_transcribing_active` stays consistent across finished/error/timeout/auto-retry/manual-retry paths |
| `app.py` (recording countdown) | `tests/test_app_recording_countdown.py` | Countdown start/refresh/clear lifecycle, handoff into transcribing, and recording-error cleanup |
| `overlay.py` | `tests/test_overlay.py` | Countdown visual formatting, low-time urgency flag, progress clamping, and countdown cleanup on hide |
| `transcription_history.py` | `tests/test_transcription_history.py` | Add/list ordering, keep only last 5 entries, delete behavior, Unicode text, duplicate entries remain distinct |

These are the checks that are suitable for repeatable automated execution. They are run locally with `pytest`, and the same class of checks should remain compatible with CI.

---

## 4. What CI Can Cover

CI covers the automated checks above:

- Pure Python unit tests under `tests/`
- Mocked behavior for config, hotkey parsing, recorder lifecycle, platform path management, model path management, clipboard integration, Windows autostart registry calls, playback-mute controller and app lifecycle rules, update asset selection, and transcription history rules
- Regression tests for defects that can be reproduced without a live Qt desktop session, real audio devices, or GPU execution
- Windows frozen-bundle packaging validation for critical CUDA/cuDNN DLLs via `python -m spkup.packaging_validation dist\spkup`
- macOS ARM64 CI packaging validation that asserts the runner and packaged executable are arm64

For release preparation, these same tests remain the required automated baseline before cutting a version. A release candidate is not ready if `pytest` is failing locally, even if CI is green.

The current local automated baseline includes playback-mute coverage in `tests/test_playback_mute.py` and `tests/test_app_playback_mute.py`. The latest full local suite rerun in this workspace used `.venv\Scripts\python -m pytest tests\ -q` and exited 0.

---

## 5. What Still Requires Manual Validation

These modules involve Qt widget painting, hardware I/O, or CUDA inference — none of which are practical to unit test:

| Module | Manual check |
| --- | --- |
| `overlay.py` | Visual inspection: recording overlay shows a live remaining-time countdown, low-time state is clearly visible, other states still show correct colours/labels, and DONE still auto-hides |
| `app.py` (tray) | Tray icon appears; single left-click toggles recording; right-click shows menu; **Recent transcriptions** opens the history window; Quit exits |
| `hotkey.py` (listener) | Windows and macOS: hold hotkey emits started once; release emits stopped; no flooding. macOS requires Accessibility/Input Monitoring permission. |
| `recorder.py` (stream) | Windows and macOS: hold hotkey, speak, release → non-empty array shape printed to stdout. macOS requires Microphone permission. |
| `transcriber.py` | Audio captured → text transcribed correctly in PT and EN; Windows validates CUDA path, macOS validates CPU path |
| `settings_dialog.py` | Dialog opens; hotkey capture works; save writes to `config.json` |
| `playback_mute.py` + recording flow | On Windows, enabling **Mute playback while recording** mutes only during active capture, restores the exact prior mute state on stop, restores after recording error or app quit, and behaves the same for hold-to-record and quick-tap toggle flows. On macOS the control is unavailable. |
| `transcription_history_window.py` | Window shows newest-first session entries; copy/delete act on the selected entry; close/reopen preserves session history while the app stays running |
| `app.py` (trigger suppression) | On Windows, rapid repeated tray clicks or hotkey retriggers within 1 second after stop/cancel/error/finalize do not start extra recording/transcription work, and a legitimate stop while recording is active is never blocked |
| `app.py` (manual transcription cancel) | During the transcribing state, pressing the hotkey or left-clicking the tray icon cancels the in-progress transcription; the overlay hides, nothing is copied to the clipboard or added to history, and a new recording can be started after the 1-second suppression window. Outside the transcribing state the gesture behaves as before. |

---

## 6. TDD Rules

These apply to every module in the "unit tests" table above:

1. Write the failing test **before** or **alongside** the implementation — never after the phase, spec, or task is declared done.
2. A task is not complete until its tests exist and pass.
3. Bug fixes must include a regression test at the unit level where practical.

---

## 7. Mocking Conventions

- Use `unittest.mock.patch` for filesystem operations (`pathlib.Path.open`, `os.replace`)
- Use `unittest.mock.MagicMock` for `sounddevice.InputStream` and `winreg` calls
- Do **not** instantiate `QApplication` in unit tests — mock `QApplication.clipboard()` at the call site

---

## 8. Acceptance Criteria by Work Item

Each active spec issue lists specific acceptance criteria. In historical MVP records this may be a phase file (`specs/phaseN.issue.md`); in maintenance mode it should normally be a spec or requirement issue. A work item is `Completed (validated)` when:

- All unit tests in scope pass (`pytest` exits 0)
- Automated checks in scope have been run locally; when matching CI or release automation exists, the same checks should also pass there
- All manual checks described in the issue pass
- `specs/progress.status.md` is updated with evidence

For release-related work specifically, the minimum local release-validation baseline is:

- `pytest`
- Windows: `python -m spkup.packaging_validation dist\spkup` after building a frozen bundle
- macOS: `file dist/spkup.app/Contents/MacOS/spkup` must report `arm64`
- Manual Windows smoke check of the runnable app build under the current source version
- Manual macOS ARM64 smoke check of the source run and packaged `.app`, including permissions
- Verification that the source version in `src/spkup/__init__.py` matches the intended Git tag `vX.Y.Z`
