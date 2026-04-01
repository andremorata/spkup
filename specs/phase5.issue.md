# Phase 5 — Visual Overlay

> **Reference:** `specs/project.plan.md` — Phase 5
> **Depends on:** Phase 4 — Transcription Engine
> **Unlocks:** Phase 6 — Clipboard + Full Signal Wiring

---

## Objective

Implement a frameless, always-on-top, click-through overlay widget that displays recording state using colour-coded animated pills. The widget has three visible states (RECORDING, TRANSCRIBING, DONE) and auto-hides after DONE. It must not steal focus or intercept mouse events from the user's active window.

---

## Out of Scope

- Overlay position configuration UI (Phase 7)
- Clipboard integration (Phase 6)

---

## Dependencies

- Related docs: `specs/project.plan.md` — Phase 5 description
- Phase 4 validated: `transcription_finished` signal exists
- `PyQt6` installed

---

## Tasks

### Task 5.1 — OverlayState enum

**Deliverable:** `OverlayState` enum in `src/spkup/overlay.py`

- [ ] Values: `HIDDEN`, `RECORDING`, `TRANSCRIBING`, `DONE`

---

### Task 5.2 — OverlayWidget

**Deliverable:** `OverlayWidget(QWidget)` in `src/spkup/overlay.py`

- [ ] Window flags: `Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput`
- [ ] `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)`
- [ ] `setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)`
- [ ] `paintEvent`: draw a rounded-rect pill using `QPainter`; colour depends on current state:
  - `RECORDING`: red `#E53935`, label `"● REC"`
  - `TRANSCRIBING`: amber `#FB8C00`, label `"… thinking"`
  - `DONE`: green `#43A047`, label `"✓"`
- [ ] `show_state(state: OverlayState)`: transitions to the given state; auto-hides after 1.5 s when state is `DONE` (via `QTimer.singleShot`)
- [ ] `QPropertyAnimation` on a custom `opacity` property for pulse effect during `RECORDING`
- [ ] Position: anchored to configured corner of the primary screen (`overlay_position` from config: `"bottom-right"`, `"bottom-left"`, `"top-right"`, `"top-left"`)
- [ ] `_reposition()`: computes screen geometry and moves widget; called on construction and on screen change

**Acceptance criterion:** Overlay appears in correct corner, shows correct colours, hides after DONE. (AC-5.1)

---

### Task 5.3 — Wire into App

**Deliverable:** Updated `src/spkup/app.py`

- [ ] Instantiate `OverlayWidget` in `App.__init__`
- [ ] Connect `HotkeyListener.recording_started` → `lambda: overlay.show_state(OverlayState.RECORDING)`
- [ ] Connect `HotkeyListener.recording_stopped` → `lambda: overlay.show_state(OverlayState.TRANSCRIBING)`
- [ ] Connect `Transcriber.transcription_finished` → `lambda _: overlay.show_state(OverlayState.DONE)`
- [ ] Connect `Transcriber.transcription_error` → `lambda _: overlay.show_state(OverlayState.HIDDEN)`

**Acceptance criterion:** Full visual flow — red pill on hold, amber on release, green flash on transcription complete. (AC-5.2)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-5.1 | Overlay renders correctly | Visual inspection: three states display correct colours and labels |
| AC-5.2 | Overlay tracks full signal flow | Hold/speak/release — three state transitions observed visually |
