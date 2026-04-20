# spkup — Delivery Workflow

> How work moves from spec to validated implementation in maintenance mode.

---

## 1. Current Mode

- The original MVP roadmap in `specs/phase1.issue.md` through `specs/phase9.issue.md` is now historical baseline material.
- As of 2026-04-20, `spkup` is in maintenance mode.
- Do not extend the original MVP phase files with new scope.
- Every new non-trivial change should start as a dedicated spec or requirement issue in `specs/`.
- Local validation remains required on the developer machine, even when matching CI or release automation exists.

---

## 2. Work Item Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────────────────┐
│  Not started │────▶│  In progress │────▶│  Completed   │────▶│  Completed (validated)│
│              │     │              │     │  (declared)  │     │                       │
└──────────────┘     └──────────────┘     └──────────────┘     └───────────────────────┘
         ▲                                       │ fails verification
         └───────────────────────────────────────┘
```

**In progress:** Implementation underway. Issue-file tasks are being ticked off.

**Completed (declared):** All tasks done; required local checks performed.

**Completed (validated):** All acceptance criteria explicitly verified; evidence recorded in `progress.status.md` from automated checks and/or manual validation, depending on the work item.

---

## 3. Starting New Work

1. Read `specs/project.plan.md` and `specs/progress.status.md`.
2. Check whether the request already belongs to an open maintenance item in `specs/`.
3. If not, create a new issue file from `specs/spec-template.issue.md`, using a descriptive filename such as `specs/spec-tray-hotkey-debounce.issue.md`.
4. Update `specs/project.plan.md` or `specs/progress.status.md` to record the new work item before implementation begins.
5. Work through tasks in order; tick checkboxes in the issue file as each step completes.

---

## 4. Completing a Work Item

Before declaring a work item complete:

- [ ] All issue file tasks are ticked
- [ ] All required local automated checks for this work item pass (`pytest` exits 0 today; matching CI or release automation evidence applies when relevant)
- [ ] All required manual checks from the issue file have been performed locally
- [ ] All acceptance criteria in the issue file's AC table are met
- [ ] No stub print statements or placeholder slots remain in the code

Update `progress.status.md`:
- Set status to `Completed (validated)`
- Record evidence (automated output and/or manual observation notes)
- Set the next action or next maintenance item

For release/versioning work, the repo follows one contract:

- Source version format: `X.Y.Z`
- Source of truth: `src/spkup/__init__.py`
- Git tag format: `vX.Y.Z`
- Release artifact names: derived directly from the same `X.Y.Z` value

The detailed operator workflow for preparing and cutting a release is documented in [docs/06-packaging-release.md](docs/06-packaging-release.md).

---

## 5. Historical MVP Roadmap

| Phase | Issue file | Scope |
| --- | --- | --- |
| 1 | `specs/phase1.issue.md` | Project files, config, tray skeleton |
| 2 | `specs/phase2.issue.md` | Global hotkey listener |
| 3 | `specs/phase3.issue.md` | Audio recording |
| 4 | `specs/phase4.issue.md` | Transcription engine + model manager |
| 5 | `specs/phase5.issue.md` | Visual overlay |
| 6 | `specs/phase6.issue.md` | Clipboard + full signal wiring |
| 7 | `specs/phase7.issue.md` | Settings dialog + in-app model download |
| 8 | `specs/phase8.issue.md` | Polish work accumulated during the original MVP build-out |
| 9 | `specs/phase9.issue.md` | Packaging, CI/release automation, versioning, distribution baseline |

---

## 6. Maintenance Intake Rules

- Create a new spec / requirement for any feature, bug-fix bundle, packaging enhancement, release-process improvement, or behavior-changing refactor that is more than a trivial edit.
- Only extend an existing maintenance item when the new request is clearly part of the same approved slice of work.
- Do not reopen the original MVP by appending tasks to `phase1` through `phase9`.
- If a request changes priorities or delivery order, update `specs/project.plan.md` and `specs/progress.status.md` in the same session.

## 7. Local Validation and Automation

Validation is still performed locally on the developer machine. That includes running the tests and completing any manual checks defined by the active work item.

The repository also has CI and release automation for the release flow. Those automations complement local validation, but they do not replace the requirement to record evidence in `specs/progress.status.md`.
