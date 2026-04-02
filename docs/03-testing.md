# spkup — Testing Strategy

> Quality approach for a personal desktop tool: TDD for core logic, manual verification for UI and hardware integration.

---

## 1. Philosophy

Validation is currently local. CI is not implemented yet, but Phase 9 will add repeatable automated checks in CI for the parts of the application that are practical to verify outside a Windows desktop session. The test suite exists for two reasons:

1. **Prevent regressions** — core logic is easy to break silently; tests catch that instantly.
2. **Drive design** — writing tests first for pure logic (parsing, config, state machines) produces cleaner interfaces.

Testing effort is proportional to testability. Pure logic gets automated tests that currently run locally and are intended to run in CI once Phase 9 lands. Hardware-dependent or Qt-dependent code gets manual verification on the target Windows machine.

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
| `autostart.py` | `tests/test_autostart.py` | Enable/disable/query with mocked `winreg` |
| `transcription_history.py` | `tests/test_transcription_history.py` | Add/list ordering, keep only last 5 entries, delete behavior, Unicode text, duplicate entries remain distinct |

These are the checks that are suitable for repeatable automated execution. Today they are run locally with `pytest`; Phase 9 is planned to run the same class of checks in CI.

---

## 4. What CI Can Cover

CI is not in place yet, but the intended CI scope is the automated checks above:

- Pure Python unit tests under `tests/`
- Mocked behavior for config, hotkey parsing, recorder lifecycle, model path management, clipboard integration, Windows autostart registry calls, and transcription history rules
- Regression tests for defects that can be reproduced without a live Qt desktop session, real audio devices, or GPU execution

For release preparation, these same tests remain the required automated baseline before cutting a version. A release candidate is not ready if `pytest` is failing locally, even though CI automation for that gate has not been implemented yet.

---

## 5. What Still Requires Manual Validation

These modules involve Qt widget painting, hardware I/O, or CUDA inference — none of which are practical to unit test:

| Module | Manual check |
| --- | --- |
| `overlay.py` | Visual inspection: three states show correct colours and labels; auto-hides after DONE |
| `app.py` (tray) | Tray icon appears; right-click shows menu; **Recent transcriptions** opens the history window; Quit exits |
| `hotkey.py` (listener) | Hold hotkey emits started once; release emits stopped; no flooding |
| `recorder.py` (stream) | Hold hotkey, speak, release → non-empty array shape printed to stdout |
| `transcriber.py` | Audio captured → text transcribed correctly in PT and EN |
| `settings_dialog.py` | Dialog opens; hotkey capture works; save writes to `config.json` |
| `transcription_history_window.py` | Window shows newest-first session entries; copy/delete act on the selected entry; close/reopen preserves session history while the app stays running |

---

## 6. TDD Rules

These apply to every module in the "unit tests" table above:

1. Write the failing test **before** or **alongside** the implementation — never after the phase is declared done.
2. A task is not complete until its tests exist and pass.
3. Bug fixes must include a regression test at the unit level where practical.

---

## 7. Mocking Conventions

- Use `unittest.mock.patch` for filesystem operations (`pathlib.Path.open`, `os.replace`)
- Use `unittest.mock.MagicMock` for `sounddevice.InputStream` and `winreg` calls
- Do **not** instantiate `QApplication` in unit tests — mock `QApplication.clipboard()` at the call site

---

## 8. Acceptance Criteria by Phase

Each phase issue file (`specs/phaseN.issue.md`) lists specific acceptance criteria. A phase is `Completed (validated)` when:

- All unit tests in scope pass (`pytest` exits 0)
- Automated checks in scope have been run locally; once Phase 9 lands, the same checks should also pass in CI
- All manual checks described in the issue pass
- `specs/progress.status.md` is updated with evidence

For Phase 9 release work specifically, the minimum local release-validation baseline is:

- `pytest`
- Manual Windows smoke check of the runnable app build under the current source version
- Verification that the source version in `src/spkup/__init__.py` matches the intended Git tag `vX.Y.Z`
