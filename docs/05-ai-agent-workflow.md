# spkup — AI Agent Workflow

> Rules for AI agents working in this repository.

---

## 1. Read Before Working

Before doing any substantial work, read:

1. `specs/project.plan.md` — confirmed stack, assumptions, historical MVP baseline, maintenance workflow
2. The active maintenance issue file in `specs/` — normally a spec or requirement issue; use historical phase files only for reference
3. `specs/progress.status.md` — current maintenance status and what's validated
4. `docs/01-architecture.md` — component diagram, threading model, module responsibilities

---

## 2. Scope Rules

- The original `phase1` through `phase9` files are historical MVP records. Do not append new scope to them.
- Work within the active maintenance item. Do not implement new functionality without updating `specs/` first.
- If a request is out of scope for the current maintenance item, say so and ask whether to open a new spec / requirement or explicitly expand the current one.
- Never silently invent new modules, dependencies, or architectural patterns not documented in `docs/01-architecture.md`.

---

## 3. Threading Safety (Critical)

- **Never** call any `QWidget` or `QApplication` method from a non-Qt thread.
- pynput callbacks run on a background thread. Always use `QMetaObject.invokeMethod` with `Qt.ConnectionType.QueuedConnection` to cross to the main thread.
- QThread workers must communicate results **only** via `pyqtSignal`.

---

## 4. Testing Rules

- Unit tests are written **alongside** implementation, not after.
- See `docs/03-testing.md` for the full list of what gets tests vs. manual verification.
- Do not skip tests for a module that is in the "unit tests" category just because it feels obvious.

---

## 5. What Requires Confirmation

Ask before:
- Adding a new dependency to `requirements.txt` or `pyproject.toml`
- Deleting any file that already has content
- Changing the config schema (`AppConfig` fields or defaults)
- Modifying threading boundaries or signal connections in `app.py`
- Touching the Windows registry or filesystem outside the documented paths
- Expanding the supported platform matrix beyond Windows x64 and macOS ARM64

---

## 6. After Completing Work

- Tick the completed tasks in the relevant maintenance issue file.
- Update `specs/progress.status.md` with work-item status, evidence, and next action.
- If docs become stale due to implementation decisions, update them in the same session.
- Brief summary of what changed, what was tested (or manually verified), and any remaining risks.

---

## 7. Module Ownership Map

| What changed | Always update |
| --- | --- |
| Config schema | `docs/01-architecture.md` §6, `specs/project.plan.md` Working Assumptions |
| New module added | `docs/01-architecture.md` Module Responsibilities table + Repository Layout |
| Platform path, artifact, or capability behavior | `docs/01-architecture.md`, `docs/03-testing.md`, `docs/06-packaging-release.md`, active spec |
| Threading boundary changed | `docs/01-architecture.md` §5 Threading Model |
| New architectural decision | `docs/01-architecture.md` §7 Architectural Decisions |
| Maintenance item completed | `specs/progress.status.md` |
