# Phase 7 — Settings Dialog

> **Reference:** `specs/project-template.plan.md` — Phase 7
> **Depends on:** Phase 6 — Clipboard + Full Signal Wiring
> **Unlocks:** Phase 8 — Polish

---

## Objective

Replace the stub Settings menu item with a functional dialog that lets the user change the hotkey, select a Whisper model size, choose the compute device, and set the overlay corner. Changing the model size triggers a download if the model is not cached. All settings are persisted to `config.json` and active components are reinitialized after save.

---

## Out of Scope

- Auto-start on Windows login (Phase 8)
- First-run wizard (Phase 8)

---

## Dependencies

- Phase 6 validated: full end-to-end flow working
- `AppConfig.save()` working (Phase 1)
- `ModelManager` working (Phase 4)

---

## Tasks

### Task 7.1 — Hotkey capture widget

**Deliverable:** `HotkeyEdit(QLineEdit)` in `src/spkup/settings_dialog.py`

- [ ] Read-only line edit; displays current hotkey string (e.g. `"ctrl+shift+space"`)
- [ ] On focus + any key press: captures the pressed keys as a hotkey combo and updates display
- [ ] Validates via `parse_hotkey()`; shows red border if invalid, green if valid
- [ ] Emits `hotkey_changed = pyqtSignal(str)` when a valid combo is captured

**Acceptance criterion:** User can click the widget, press a new combo, and the field updates to the new string. (AC-7.1)

---

### Task 7.2 — Model download worker

**Deliverable:** `_ModelDownloadWorker(QThread)` in `src/spkup/model_manager.py`

- [ ] Accepts `model_size: str`
- [ ] Downloads model from HuggingFace using `faster_whisper.download_model()` to `model_cache_dir()`
- [ ] Emits `progress = pyqtSignal(int)` (0–100) and `finished = pyqtSignal()` and `error = pyqtSignal(str)`

**Acceptance criterion:** Worker downloads model to expected path; progress signal fires at least once. (AC-7.2)

---

### Task 7.3 — SettingsDialog

**Deliverable:** `SettingsDialog(QDialog)` in `src/spkup/settings_dialog.py`

- [ ] Sections: Hotkey, Model, Device, Overlay Position
- [ ] Hotkey: uses `HotkeyEdit`
- [ ] Model size: `QComboBox` with options `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`; shows download status badge (✓ cached / ↓ not downloaded)
- [ ] Device: `QComboBox` with `cuda` / `cpu`; auto-detects CUDA availability and disables cuda option if not present
- [ ] Compute type: `QComboBox` with `float16` / `int8` / `float32`; `int8` and `float32` shown when `cpu` selected
- [ ] Overlay position: `QComboBox` with the four corners
- [ ] **Download button**: appears next to model selector when selected model is not cached; clicking starts `_ModelDownloadWorker` and shows `QProgressDialog`
- [ ] **Save button**: validates all fields, calls `AppConfig.save()`, emits `settings_saved = pyqtSignal(AppConfig)`
- [ ] **Cancel button**: discards changes

**Acceptance criterion:** Dialog opens, all controls reflect current config, save persists changes to `config.json`. (AC-7.3)

---

### Task 7.4 — Reinitialize components on save

**Deliverable:** Updated `src/spkup/app.py`

- [ ] Connect `SettingsDialog.settings_saved` → `App._on_settings_saved(new_config: AppConfig)`
- [ ] `_on_settings_saved`: stop old `HotkeyListener`, create new one with updated hotkey; reinitialize `Transcriber` if model/device changed; reposition overlay if corner changed
- [ ] Replace tray "Settings" stub with `SettingsDialog` instantiation and `exec()`

**Acceptance criterion:** Change hotkey in dialog → new hotkey works without restart. (AC-7.4)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-7.1 | Hotkey capture widget works | Press new combo in widget; field updates |
| AC-7.2 | Download worker downloads model | Model appears in `%LOCALAPPDATA%/spkup/models` after download |
| AC-7.3 | Dialog opens and saves config | Open settings, change a value, save → `config.json` updated |
| AC-7.4 | Components reinitialize after save | Change hotkey → new hotkey active immediately |
