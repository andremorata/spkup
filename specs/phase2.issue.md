# Phase 2 — Global Hotkey (Press-and-Hold)

> **Reference:** `specs/project-template.plan.md` — Phase 2
> **Depends on:** Phase 1 — Project Setup + Core Skeleton
> **Unlocks:** Phase 3 — Audio Recording

---

## Objective

Implement a global hotkey listener that detects when the configured key combo is held down and emits `recording_started`, then emits `recording_stopped` when the trigger key is released. The listener must be safe to use from a non-Qt thread and must never flood the Qt event loop with repeated signals.

---

## Out of Scope

- Audio capture (Phase 3)
- Any overlay or visual feedback (Phase 5)
- Hotkey reconfiguration UI (Phase 7)

---

## Dependencies

- Related docs: `specs/project-template.plan.md` — Key Design Decisions (pynput)
- Phase 1 validated: `AppConfig.hotkey` field exists and loads correctly
- `pynput` installed in venv

---

## Tasks

### Task 2.1 — Hotkey string parser

**Deliverable:** `parse_hotkey(hotkey_str: str) -> tuple[set[str], str]` in `src/spkup/hotkey.py`

- [ ] Accept strings like `"ctrl+shift+space"`, `"alt+f1"`, `"ctrl+space"`
- [ ] Return `(modifiers: set[str], trigger: str)` — modifiers are lowercase (`"ctrl"`, `"shift"`, `"alt"`), trigger is the final key name
- [ ] Raise `ValueError` for empty string or no trigger key
- [ ] Unit tests: `tests/test_hotkey.py` — valid combos, single key, unknown modifier names, edge cases

**Acceptance criterion:** All unit tests in `tests/test_hotkey.py` pass. (AC-2.1)

---

### Task 2.2 — HotkeyListener class

**Deliverable:** `HotkeyListener(QObject)` in `src/spkup/hotkey.py`

- [ ] Constructor takes `hotkey_str: str`; calls `parse_hotkey` internally
- [ ] Uses `pynput.keyboard.Listener` (runs on its own thread)
- [ ] Tracks `_pressed_keys: set` of currently held key names
- [ ] `_is_active: bool` flag — prevents duplicate `recording_started` on key-repeat
- [ ] `on_press`: when all modifiers + trigger are held and `_is_active` is False → set flag → marshal `_emit_started` to Qt main thread via `QMetaObject.invokeMethod(..., Qt.ConnectionType.QueuedConnection)`
- [ ] `on_release`: when trigger key is released and `_is_active` is True → clear flag → marshal `_emit_stopped`
- [ ] Signals: `recording_started = pyqtSignal()`, `recording_stopped = pyqtSignal()`
- [ ] `start()` / `stop()` methods to manage the pynput listener lifecycle

**Acceptance criterion:** Manually verified — hold hotkey emits `recording_started` once; release emits `recording_stopped`; holding longer does not repeat. (AC-2.2)

---

### Task 2.3 — Wire into App

**Deliverable:** Updated `src/spkup/app.py`

- [ ] Instantiate `HotkeyListener` with `config.hotkey` in `App.__init__`
- [ ] Call `listener.start()` after tray is set up
- [ ] Connect `recording_started` / `recording_stopped` to stub slots that print to stdout for now
- [ ] Call `listener.stop()` on app quit

**Acceptance criterion:** Running `python -m spkup` and pressing the hotkey prints start/stop messages to stdout. (AC-2.3)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-2.1 | Parser handles all valid combo strings | `pytest tests/test_hotkey.py` passes |
| AC-2.2 | Listener emits signals correctly, no flooding | Hold/release hotkey; observe single signal per gesture |
| AC-2.3 | App wires listener on startup | `python -m spkup` prints start/stop on hotkey use |
