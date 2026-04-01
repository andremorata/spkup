# Phase N — [Title]

> **Reference:** `specs/[project-plan-file].md` — Phase N
> **Depends on:** [Previous phase name, or "None — first phase"]
> **Unlocks:** [Next phase name, or "None — final phase"]

---

## Objective

Describe the concrete outcome this phase is meant to deliver. Keep it to one paragraph — if it requires more, the phase scope is likely too wide.

---

## Out of Scope

- [What this phase explicitly does not cover]

---

## Dependencies

- Related docs:
- Required environments or services:
- Upstream decisions that must be resolved first:

---

## Tasks

### Task N.1 — [Name]

**Deliverable:** [The file, module, endpoint, or artifact this task produces]

- [ ] Step one
  - Sub-detail if needed
- [ ] Step two
- [ ] Step three

**Acceptance criterion:** [A verifiable check — e.g., "command exits 0", "returns HTTP 200", "all unit tests pass"] (AC-N.1)

---

### Task N.2 — [Name]

**Deliverable:** [What is produced]

- [ ] Step one
- [ ] Step two

**Acceptance criterion:** [Verifiable check] (AC-N.2)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-N.1 | | |
| AC-N.2 | | |

---

## Risks and Notes

---

## Exit Gate

The phase is closed when all of the following are true:

1. All `AC-N.X` rows in the table above are satisfied.
2. For every substantial change in this phase — new feature, new module, non-trivial bug fix, or behavior-changing refactor — the corresponding tests are written, passing, and referenced below as evidence.
3. `progress.status.md` is updated with the validation summary, evidence (commands run, test output, commit references), and the next action.

Do not mark the phase as `Completed (validated)` until all three conditions are met.
