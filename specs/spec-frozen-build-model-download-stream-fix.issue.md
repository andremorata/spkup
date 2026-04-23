# Spec — Fix model download crash in frozen (windowed) build

> **Type:** Maintenance
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `Completed (declared)`
> **Created:** 2026-04-23
> **Depends on:** Phase 9 packaging baseline (closed historical)

---

## Objective

Eliminate the `'NoneType' object has no attribute 'write'` crash that happens
when downloading a Whisper model (reproduced with Medium) from the compiled,
windowed spkup executable. Downloads must succeed from the frozen build,
matching the behaviour already observed when running spkup from a terminal.

---

## Why Now

- Real user bug report: downloading the Medium model from the compiled build
  surfaced a "Download failed — 'NoneType' object has no attribute 'write'"
  dialog. Tiny and Small had been downloaded previously, but from a dev
  terminal session, masking the root cause.

## Root Cause

PyInstaller builds with `console=False` (windowed) detach the process from
a console, so `sys.stdout` and `sys.stderr` are `None` at runtime.
`huggingface_hub.snapshot_download` uses `tqdm`, which writes progress to
`sys.stderr`. With `sys.stderr is None`, the first `tqdm` write raises
`AttributeError: 'NoneType' object has no attribute 'write'`, the thread
emits `error`, and the UI shows the "Download failed" dialog. Smaller
models may incidentally avoid the failure depending on how much progress
output tqdm produces before caching short-circuits it, which is why Tiny
and Small appeared to work.

---

## Out of Scope

- Redesigning the model download UX or replacing `huggingface_hub`.
- Adding a visual progress bar beyond the existing 5 / 100 % signal.
- Changing the PyInstaller build to a console build.

---

## Affected Areas

- Code / modules: `src/spkup/__main__.py`, `src/spkup/model_manager.py`
- Docs: none (behaviour fix, no contract change)
- Tests: `tests/test_model_manager.py`
- Manual verification surface: frozen build download of each model size

---

## Tasks

### Task 1 — Guard `sys.stdout` / `sys.stderr` in frozen builds

**Deliverable:** Startup bootstrap ensures `sys.stdout` and `sys.stderr`
are never `None` so third-party libraries that write to them do not crash.

- [x] Add `_ensure_std_streams()` helper in `src/spkup/__main__.py`.
- [x] Call it from `_bootstrap()` before `_add_windows_dll_dirs()` and
  before `configure_logging()`.
- [x] Fallback writes go to `os.devnull` to stay silent.

**Acceptance criterion:** After bootstrap, `sys.stdout` and `sys.stderr`
are writable file-like objects in both dev and frozen windowed builds. (AC-1)

---

### Task 2 — Disable `tqdm` progress bars in the download worker

**Deliverable:** Defensive disabling of `huggingface_hub` progress bars
inside `_ModelDownloadWorker.run` so downloads do not depend on a live
`stderr` stream.

- [x] Call `huggingface_hub.utils.disable_progress_bars()` before
  `snapshot_download`.
- [x] Suppress any error from the disable call so the worker still
  attempts the download if the API changes.

**Acceptance criterion:** `_ModelDownloadWorker.run` does not rely on
`sys.stderr` being writable for a successful download. (AC-2)

---

### Task 3 — Regression test

**Deliverable:** Automated test that pins the fixed behaviour.

- [x] Add a test that monkeypatches `huggingface_hub.snapshot_download`
  to assert it is called, and that `disable_progress_bars()` is invoked
  prior to it.
- [x] Add a test confirming `_ensure_std_streams()` replaces `None`
  streams with writable file-like objects.

**Acceptance criterion:** New tests pass and cover both the stream guard
and the progress-bar disabling path. (AC-3)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | `sys.stdout` / `sys.stderr` are writable after bootstrap in frozen windowed builds | Unit test forces both streams to `None`, runs `_ensure_std_streams()`, asserts both have `.write` |
| AC-2 | Download worker does not crash when `sys.stderr is None` | Unit test runs `_ModelDownloadWorker.run` with `sys.stderr = None` and a mocked `snapshot_download`, asserts no error emitted and `disable_progress_bars` was called |
| AC-3 | New regression tests pass | `pytest tests/test_model_manager.py -q` |

---

## Validation Plan

- Automated checks: `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q`
- Manual checks: Build the windowed PyInstaller artifact and download
  Medium and Large-v3 end to end from the compiled binary; confirm the
  "Download failed" dialog no longer appears and the model folder is
  populated.
- Evidence to capture in `specs/progress.status.md`: test run result,
  files changed, and (when done) manual download outcome per model size.

---

## Risks and Notes

- `huggingface_hub.utils.disable_progress_bars` has been stable across
  recent versions; the call is wrapped in `try/except` so a future rename
  will not regress downloads.
- Redirecting the missing streams to `os.devnull` means any stray
  `print(...)` from third-party code is silently dropped in the frozen
  build. This matches the pre-existing windowed-build expectation and is
  preferable to crashing.
