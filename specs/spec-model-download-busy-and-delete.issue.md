# Spec — Model download busy indicator, size hints, and deletion

> **Type:** Maintenance
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `Not started`
> **Created:** 2026-04-23
> **Depends on:** `specs/spec-frozen-build-model-download-stream-fix.issue.md`

---

## Objective

Improve the Settings dialog model-management UX by:

1. Showing the approximate download size next to each Whisper model so
   users can pick deliberately before downloading.
2. Replacing the current determinate-but-frozen progress dialog with an
   indeterminate busy indicator, since `huggingface_hub.hf_hub_download`
   does not expose a byte-accurate progress callback that works reliably
   in a windowed PyInstaller build.
3. Allowing users to delete a previously-downloaded model from the
   Settings dialog so the local cache does not grow unbounded.

---

## Why Now

- Direct user feedback after the fix for the Medium-model download crash:
  the download dialog appears, stays at 5 %, and only closes when the
  download finishes. It looks frozen even though work is happening.
- Users also asked to be able to reclaim disk space from models they
  downloaded but no longer use. Today there is no way to remove a model
  from inside the app.

## Root Cause of the Frozen-Looking Progress

`huggingface_hub.hf_hub_download` has no public byte-level progress
callback. Its built-in progress bar writes to `sys.stderr` via `tqdm`,
which is disabled in the windowed build because `sys.stderr is None`.
Downloading file-by-file only gives coarse per-file jumps, and the big
model file dominates the total, so the bar effectively stalls on the
largest file. A busy indicator is a more honest representation.

---

## Out of Scope

- Byte-accurate progress via a custom `tqdm_class` or reimplementing the
  download loop with `requests` / `httpx`.
- Multi-select bulk delete.
- Background / scheduled downloads.
- Showing disk usage beyond the per-model static estimate.

---

## Affected Areas

- Code / modules: `src/spkup/model_manager.py`, `src/spkup/settings_dialog.py`
- Docs: `docs/04-delivery-workflow.md` (only if model management is documented)
- Tests: `tests/test_model_manager.py`
- Manual verification surface: Settings dialog → Model size

---

## Tasks

### Task 1 — Static approximate sizes per model

**Deliverable:** A module-level mapping in `model_manager.py` exposing
the approximate on-disk size for each supported Whisper model, plus a
helper to format it as a human-readable string.

- [ ] Add `MODEL_APPROX_SIZES_MB: dict[str, int]` covering the six
  supported sizes (tiny, base, small, medium, large-v2, large-v3).
- [ ] Add `format_model_size(model_size: str) -> str` returning e.g.
  `"~75 MB"` or `"~3.0 GB"`; returns an empty string for unknown sizes.
- [ ] Keep the mapping documented as an approximation, not an exact
  value (HF CDN weights vary by revision).

**Acceptance criterion:** `format_model_size("medium")` returns a
human-readable size string; unknown sizes return `""`. (AC-1)

---

### Task 2 — Delete-model helper

**Deliverable:** A safe, test-covered function to remove a downloaded
model directory from the local cache.

- [ ] Add `delete_model(model_size: str) -> bool` in `model_manager.py`.
- [ ] It must:
  - Resolve the target via `model_path(model_size)`.
  - Refuse to act if the target is not inside `model_cache_dir()`.
  - Return `False` (no-op) if the model is not downloaded.
  - `shutil.rmtree(..., ignore_errors=False)` the directory and return
    `True` on success.
  - Propagate `OSError` / `PermissionError` on real failures so the UI
    can surface a proper error dialog.

**Acceptance criterion:** `delete_model("base")` removes the directory
for `base`, leaves other models untouched, and refuses paths outside the
cache dir. (AC-2)

---

### Task 3 — Indeterminate busy indicator

**Deliverable:** The download dialog shows a marquee / busy
`QProgressBar` (range 0, 0) with a descriptive label that includes the
model size estimate, and closes when the worker finishes or errors.

- [ ] Replace the `QProgressDialog(..., 0, 100, ...)` configuration in
  `_on_download` with a `QProgressDialog(..., 0, 0, ...)` so the bar
  becomes indeterminate.
- [ ] Update the label text to include the approximate size, e.g.
  `Downloading medium (~1.5 GB)… This can take a while.`
- [ ] Drop the `progress` → `setValue` wiring (not meaningful for a
  busy indicator). Keep `canceled → worker.terminate` and the finished
  / error handlers as-is.
- [ ] Remove the `self._progress_dlg.setValue(100)` call on finish.

**Acceptance criterion:** Opening the download dialog shows an animated
busy bar from the moment it appears until the worker finishes or errors.
The dialog never displays a misleading stalled percentage. (AC-3)

---

### Task 4 — Model size in the combo and download button

**Deliverable:** Each entry in the model combo shows the approximate
size next to the name, regardless of download state. The **Download**
button tooltip also shows the estimated size.

- [ ] Update the combo population loop in `SettingsDialog.__init__` to
  render `f"{badge}  {m} ({format_model_size(m)})"`.
- [ ] In `_on_download_done` update the item text with the same format.
- [ ] Set a tooltip on `self._download_btn` describing what will be
  downloaded, including the size.

**Acceptance criterion:** Each model in the combo shows its approximate
size; the Download button tooltip mentions the estimated size. (AC-4)

---

### Task 5 — Delete button in the Settings dialog

**Deliverable:** A **Delete** button next to **Download** that is
visible only when the currently-selected model is downloaded. Clicking
it prompts for confirmation and, on OK, removes the model from the cache
and updates the UI.

- [ ] Add `self._delete_btn = QPushButton("Delete")` in the model row
  after the download button.
- [ ] `_delete_btn.setVisible(is_downloaded(config.model_size))` during
  init; inverse visibility of the download button.
- [ ] Wire `_delete_btn.clicked` to `_on_delete`:
  - Ask `QMessageBox.question(self, "Delete model", …, Yes | No)`; bail
    on No.
  - Call `delete_model(model_size)`; on exception surface
    `QMessageBox.critical(self, "Delete failed", str(exc))`.
  - On success: update the combo item text badge back to `↓`, show the
    download button, hide the delete button.
- [ ] Update `_on_model_changed`, `_on_download_done` to also toggle
  the delete button visibility consistently.

**Acceptance criterion:** After a successful download, a Delete button
appears. Clicking it with confirmation removes the model directory and
the UI returns to the pre-download state. Cancelling the confirmation
leaves the model on disk. (AC-5)

---

### Task 6 — Regression tests

**Deliverable:** Unit tests covering the new helpers.

- [ ] Add `test_format_model_size_*` covering known sizes and unknown
  fallback.
- [ ] Add `test_delete_model_*` covering:
  - Removes an existing model directory.
  - Returns `False` when the model is not downloaded.
  - Leaves sibling model directories untouched.
  - Refuses to act on paths outside the cache dir (guard).

**Acceptance criterion:** New tests pass. Full suite stays green. (AC-6)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | `format_model_size` returns readable strings and `""` for unknown | Unit test |
| AC-2 | `delete_model` removes only the target directory and refuses unsafe paths | Unit test |
| AC-3 | Download dialog shows an animated busy bar with a size-aware label | Manual verification in the compiled windowed build |
| AC-4 | Model combo and Download tooltip expose the approximate size | Visual check of Settings dialog |
| AC-5 | Delete button removes the model after confirmation and updates the UI | Manual verification |
| AC-6 | New and existing tests pass | `pytest tests/ -q` |

---

## Validation Plan

- Automated: `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests\ -q`
- Manual: rebuild the windowed PyInstaller artifact; open Settings;
  confirm (a) each model shows an approximate size, (b) downloading a
  not-yet-downloaded model shows a running busy bar that only closes
  on completion / error, (c) the Delete button appears after download
  and actually removes the folder under
  `%LOCALAPPDATA%\spkup\models\<model>`.
- Evidence to capture in `specs/progress.status.md`: test counts, files
  changed, and manual outcome per verified model size.

---

## Risks and Notes

- The `MODEL_APPROX_SIZES_MB` values are approximations. If HF ships a
  substantially larger revision in the future the label is still useful
  but may be off by 10–20 %. This is acceptable for UX intent.
- Deleting a model that is currently loaded by the transcriber would
  fail on Windows because files are open. This spec does not preemptively
  unload the model: if the user tries to delete the currently-loaded
  model, the `PermissionError` bubbles up as a "Delete failed" dialog.
  A future spec can add a proactive unload.
