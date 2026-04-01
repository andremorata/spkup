# Phase 1 — Project Setup + Core Skeleton

> **Reference:** `specs/spkup.plan.md` — Phase 1
> **Depends on:** None — first phase
> **Unlocks:** Phase 2 — Global Hotkey

---

## Objective

Establish the runnable project skeleton: package layout, dependency declaration, configuration persistence, and a working system-tray `QApplication`. After this phase, `python -m spkup` launches the app, a tray icon appears, and the Settings / Quit menu items exist (Settings opens a stub dialog; Quit exits cleanly).

---

## Out of Scope

- Hotkey listener (Phase 2)
- Audio recording (Phase 3)
- Transcription (Phase 4)
- Overlay widget (Phase 5)
- Production-ready settings dialog (Phase 7)
- Any model download logic (Phase 4 / 7)

---

## Dependencies

- Related docs: `PLAN.md` — Phase 1 section
- Required environments: Python 3.12 venv, `PyQt6` installed
- Upstream decisions: Stack confirmed in `specs/spkup.plan.md`

---

## Tasks

### Task 1.1 — Project files

**Deliverable:** `pyproject.toml`, `requirements.txt`, `run.bat`, updated `.gitignore`

- [ ] Create `pyproject.toml` with hatchling build, all five dependencies declared
- [ ] Create `requirements.txt` (flat pin list for direct `pip install -r`)
- [ ] Create `run.bat` that activates `.venv` and runs `python -m spkup`
- [ ] Append Python-specific entries to `.gitignore` (`__pycache__/`, `.venv/`, `*.log`, `*.egg-info/`)

**Acceptance criterion:** `pip install -r requirements.txt` succeeds in a fresh venv. (AC-1.1)

---

### Task 1.2 — Package skeleton

**Deliverable:** `src/spkup/__init__.py`, `src/spkup/__main__.py`

- [ ] Create `src/spkup/__init__.py` (module marker, version string)
- [ ] Create `src/spkup/__main__.py` calling `App().run()`

**Acceptance criterion:** `python -m spkup` is invokable (may crash if PyQt6 not yet wired). (AC-1.2)

---

### Task 1.3 — Config module

**Deliverable:** `src/spkup/config.py`

- [ ] `AppConfig` dataclass with fields: `hotkey`, `model_size`, `device`, `compute_type`, `overlay_position`, `max_recording_seconds`
- [ ] Sensible defaults: `hotkey="ctrl+shift+space"`, `model_size="large-v3"`, `device="cuda"`, `compute_type="float16"`, `overlay_position="bottom-right"`, `max_recording_seconds=120`
- [ ] `load() -> AppConfig` reads from `%APPDATA%/spkup/config.json`; creates file with defaults on first run
- [ ] `save(config: AppConfig)` writes to same path atomically (write temp → rename)
- [ ] Unit tests: `tests/test_config.py` — load defaults, round-trip save/load, unknown keys ignored

**Acceptance criterion:** All unit tests in `tests/test_config.py` pass with `pytest`. (AC-1.3)

---

### Task 1.4 — App skeleton + tray icon

**Deliverable:** `src/spkup/app.py`, `src/spkup/resources/tray.png`

- [ ] `App` class: creates `QApplication`, `QSystemTrayIcon` with a placeholder icon
- [ ] Context menu: **Settings** (stub — shows `QMessageBox`) and **Quit**
- [ ] Quit action calls `QApplication.quit()` cleanly
- [ ] `App.run()` calls `app.exec()` and returns its exit code
- [ ] Tray tooltip: "spkup — Push to Talk"

**Acceptance criterion:** `python -m spkup` shows tray icon; right-click reveals Settings and Quit; Quit exits. (AC-1.4)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
|---|---|---|
| AC-1.1 | All dependencies install cleanly | `pip install -r requirements.txt` exits 0 in fresh venv |
| AC-1.2 | Package is runnable | `python -m spkup` is invokable |
| AC-1.3 | Config load/save round-trips correctly | `pytest tests/test_config.py` passes |
| AC-1.4 | Tray app launches and quits | Tray icon visible; Quit exits process |
