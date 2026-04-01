# Phase 6 — Clipboard + Full Signal Wiring

> **Reference:** `specs/project-template.plan.md` — Phase 6
> **Depends on:** Phase 5 — Visual Overlay
> **Unlocks:** Phase 7 — Settings Dialog

---

## Objective

Copy the transcribed text to the system clipboard and optionally show a tray notification with a preview. Clean up all stub slots from previous phases and replace them with the real signal wiring so the end-to-end flow is fully functional.

---

## Out of Scope

- Settings dialog (Phase 7)
- Error handling polish (Phase 8)

---

## Dependencies

- Phase 5 validated: overlay transitions working
- All previous stub connections in `app.py` still present

---

## Tasks

### Task 6.1 — Clipboard module

**Deliverable:** `src/spkup/clipboard.py`

- [ ] `copy_to_clipboard(text: str) -> None`: calls `QApplication.clipboard().setText(text)` — handles Unicode correctly
- [ ] Unit test: `tests/test_clipboard.py` — mock `QApplication.clipboard()`, assert `setText` called with correct string

**Acceptance criterion:** `pytest tests/test_clipboard.py` passes. (AC-6.1)

---

### Task 6.2 — Tray notification

**Deliverable:** Updated `src/spkup/app.py`

- [ ] After `copy_to_clipboard`, call `tray.showMessage("spkup", preview, QSystemTrayIcon.MessageIcon.Information, 2000)` where `preview` is the first 80 characters of the transcription
- [ ] Only show notification if `QSystemTrayIcon.supportsMessages()` returns True

**Acceptance criterion:** A system notification appears with text preview after transcription. (AC-6.2)

---

### Task 6.3 — Final signal wiring

**Deliverable:** Clean `src/spkup/app.py` with all stub slots removed

- [ ] Remove all `print()`-based stub slots added in Phases 2–4
- [ ] `Transcriber.transcription_finished` → `copy_to_clipboard(text)` + `overlay.show_state(DONE)` + tray notification
- [ ] `Transcriber.transcription_error` → `overlay.show_state(HIDDEN)` + tray error notification
- [ ] `AudioRecorder.recording_error` → `overlay.show_state(HIDDEN)` + tray error notification
- [ ] Ensure signal connections are not duplicated (remove old stubs first, then add final ones)

**Acceptance criterion:** Complete flow — hotkey → record → transcribe → clipboard → overlay DONE → tray notification — no print statements remain. (AC-6.3)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-6.1 | Clipboard module test passes | `pytest tests/test_clipboard.py` passes |
| AC-6.2 | Tray notification shows preview | Notification visible after transcription |
| AC-6.3 | Full end-to-end flow works cleanly | Hold hotkey → speak → text in clipboard; no stubs in `app.py` |
