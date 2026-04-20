# Spec — [Title]

> **Type:** Spec | Requirement | Maintenance extension
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `Not started`
> **Created:** YYYY-MM-DD
> **Depends on:** [Optional prior spec, release, or module state]

---

## Objective

Describe the concrete outcome this maintenance item should deliver. Keep it scoped to one coherent slice of value.

---

## Why Now

- [User request, bug report, operational gap, or follow-up reason]

---

## Out of Scope

- [What this item explicitly does not cover]

---

## Affected Areas

- Code / modules:
- Docs:
- Tests:
- Manual verification surface:

---

## Tasks

### Task 1 — [Name]

**Deliverable:** [File, behavior, workflow, or artifact produced]

- [ ] Step one
- [ ] Step two
- [ ] Step three

**Acceptance criterion:** [A concrete, verifiable outcome] (AC-1)

---

### Task 2 — [Name]

**Deliverable:** [What is produced]

- [ ] Step one
- [ ] Step two

**Acceptance criterion:** [A concrete, verifiable outcome] (AC-2)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | | |
| AC-2 | | |

---

## Validation Plan

- Automated checks:
- Manual checks:
- Evidence to capture in `specs/progress.status.md`:

---

## Risks and Notes

- Dependencies:
- Rollback or safety considerations:
- Open questions:

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. All acceptance criteria above are satisfied.
2. For every substantial code or behavior change, the corresponding tests are written or updated, passing, and referenced as evidence.
3. `specs/progress.status.md` records the validation summary, evidence, and next action.
