# spkup — Delivery Workflow

> How work moves from spec to validated implementation, phase by phase.

---

## 1. Principles

- One phase at a time. Do not start Phase N+1 until Phase N is validated.
- Every phase has an issue file in `specs/` that defines tasks and acceptance criteria before implementation begins.
- Local validation remains required for every phase on the developer machine.
- A phase is not done when code is written — it is done when acceptance criteria are verified and `progress.status.md` reflects that.

---

## 2. Phase Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────────────────┐
│  Not started │────▶│  In progress │────▶│  Completed   │────▶│  Completed (validated)│
│              │     │              │     │  (declared)  │     │                       │
└──────────────┘     └──────────────┘     └──────────────┘     └───────────────────────┘
         ▲                                       │ fails verification
         └───────────────────────────────────────┘
```

**In progress:** Implementation underway. Issue file tasks are being ticked off.

**Completed (declared):** All tasks done; required local checks performed.

**Completed (validated):** All acceptance criteria explicitly verified; evidence recorded in `progress.status.md` from automated checks and/or manual validation, depending on the phase.

---

## 3. Starting a Phase

1. Read the phase issue file (`specs/phaseN.issue.md`) in full.
2. Confirm all dependencies from previous phases are validated.
3. Update `progress.status.md`: set phase status to `In progress`.
4. Work through tasks in order; tick checkboxes in the issue file as each step completes.

---

## 4. Completing a Phase

Before declaring a phase complete:

- [ ] All issue file tasks are ticked
- [ ] All required local automated checks for this phase pass (`pytest` exits 0 today; automated pipeline evidence applies once implemented for the relevant phase)
- [ ] All required manual checks from the issue file have been performed locally
- [ ] All acceptance criteria in the issue file's AC table are met
- [ ] No stub print statements or placeholder slots remain in the code

Update `progress.status.md`:
- Set status to `Completed (validated)`
- Record evidence (automated output and/or manual observation notes)
- Set the next phase as the new active phase

---

## 5. Phase Map

| Phase | Issue file | Scope |
| --- | --- | --- |
| 1 | `specs/phase1.issue.md` | Project files, config, tray skeleton |
| 2 | `specs/phase2.issue.md` | Global hotkey listener |
| 3 | `specs/phase3.issue.md` | Audio recording |
| 4 | `specs/phase4.issue.md` | Transcription engine + model manager |
| 5 | `specs/phase5.issue.md` | Visual overlay |
| 6 | `specs/phase6.issue.md` | Clipboard + full signal wiring |
| 7 | `specs/phase7.issue.md` | Settings dialog + in-app model download |
| 8 | `specs/phase8.issue.md` | Logging, error handling, auto-start, first-run |
| 9 | `specs/phase9.issue.md` | Planned packaging, CI/release automation, versioning, distribution |

---

## 6. Local Validation and Planned Automation

Today, validation is performed locally on the developer machine. That includes running the required tests and completing any manual checks defined by the active phase issue.

Phase 9 is planned to add packaging plus CI/release automation so the same checks can run repeatably in an automated pipeline. That automation does not exist yet, so this workflow still treats local validation as the source of truth for current phases.
