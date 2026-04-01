# AI Project Scaffold - Copilot Instructions

You are working inside a reusable project scaffold intended to bootstrap new software products with AI-agent support.

Your job is to help turn this scaffold into a concrete project without introducing assumptions that belong to a previous product.

**IMPORTANT**: THIS IS THE BASE INSTRUCTIONS FILE FOR IA AGENTS WORKING IN THIS REPOSITORY AND `CLAUDE.md` AND `.github/copilot-instructions.md` FILES ARE SYMLINKS TO THIS FILE. DO NOT EDIT THOSE FILES DIRECTLY. IF YOU WANT TO CHANGE THE INSTRUCTIONS, EDIT THIS FILE AND THE CHANGES WILL BE REFLECTED IN ALL SYMLINKS AUTOMATICALLY.

## Core Principles

- Treat this repository as a neutral foundation, not as an existing product.
- Prefer reusable patterns over domain-specific implementation shortcuts.
- Document decisions clearly when a project-specific choice is made.
- Keep architecture, delivery, and operational concerns aligned across code and docs.
- When a placeholder exists, either preserve it or replace it with an explicit project decision. Do not invent hidden defaults.
- Default to clean boundaries, testable code, and explicit verification.

## Bootstrap Mode

Bootstrap mode is active when this repository has not yet been converted into a concrete project. Recognize it by these signals:

- The project plan in `specs/` has placeholder or TBD values for name, stack, and phase scope.
- No source code directories exist (`backend/`, `frontend/`, `src/`, `infra/`, etc.).
- `progress.status.md` shows Phase 0 as "Not started".

### Kickoff Questionnaire

Before doing any Phase 0 implementation work, ask the user about each of the following topics that is not already answered in the plan. If the user skips a question, proceed with a reasonable default and document the assumption explicitly in `specs/` before writing code.

1. **Project identity** — What is the project name, the problem it solves, and who are the primary users?
2. **Tech stack** — What is the intended choice per layer: backend language and framework, frontend framework, database engine, authentication approach, background job processing, and package manager?
3. **Dev container** — Will the project use a dev container? If yes, what base OS and which runtimes or tools must be installed?
4. **Local development infrastructure** — Which services are needed locally via Docker Compose? Common candidates: database, email sandbox, blob or object storage, message broker. Are there others?
5. **User identity and roles** — Does the application have authenticated users? If yes, what roles are needed and what does each role permit or restrict?
6. **License and dependency constraints** — Are there known forbidden libraries, commercial license restrictions, or open-source policies the project must follow?
7. **Infrastructure target** — Which cloud provider, IaC tool (e.g. Bicep, Terraform, Pulumi), and hosting model (containers, serverless, VMs, PaaS) will be used?
8. **Observability** — What are the preferences for structured logging, APM, and alerting?
9. **Testing strategy** — Which test frameworks will be used per layer? Are there coverage requirements? Is the preference TDD, test-in-parallel, or test-after?

### After Collecting Answers

Document all responses in `specs/` — the project plan and the Phase 0 issue file — before writing any source code or infrastructure files. This ensures all subsequent agents and contributors start from a known, agreed baseline.

## Preferred Workflow

1. Read the relevant files in `docs/` and `specs/` before making structural changes.
2. Identify whether the task is scaffold-level or project-specific.
3. Preserve reusable guidance and remove stale assumptions from previous projects.
4. Update documentation whenever code, infrastructure, or workflows materially change.
5. After completing any meaningful work, review `docs/` for pages that may be stale or incomplete given the changes just made. Update them as part of the same task — do not defer documentation accuracy to a follow-up.
6. Leave the repository easier for the next human or agent to understand.

## Specs-Driven Execution

The `specs/` folder is the execution backbone of the project. Agents must treat it as the authoritative source for delivery sequencing and scope control.

### Required files in `specs/`

- `project-template.plan.md` or the project-specific plan file:
  the master plan for phases, scope, sequencing, and major delivery expectations
- `phase-template.issue.md` or the active phase issue files:
  the actionable breakdown for a single phase, milestone, or workstream
- `progress.status.md`:
  the source of truth for current status, validation state, evidence, and next actions

### Required agent behavior

Before doing substantial work:

1. Read the project plan in `specs/` to understand the intended roadmap.
2. Identify the active phase or the phase most directly related to the request.
3. Read the corresponding phase issue file before implementing changes.
4. Check `progress.status.md` to understand the current state, risks, and validation status.

While doing the work:

- Stay aligned with the current plan and phase scope unless the user explicitly changes direction.
- Do not silently implement work that belongs to a later phase if it changes scope, architecture, or delivery order in a meaningful way.
- If the requested change requires deviating from the plan, update the relevant `specs/` files as part of the task or clearly document the mismatch.
- Keep implementation, docs, and progress tracking synchronized.

### Handling Out-of-Scope Requests

When a user asks for something that is not covered by the current plan or the active phase, do not implement it silently. Follow this protocol:

1. **Identify the gap** — determine whether the request falls outside the active phase scope, outside the project plan entirely, or contradicts an existing decision.
2. **Confirm with the user** — briefly state that the request is not covered by the current plan or phase and ask whether they want it treated as a new addition.
3. **Update `specs/` before implementing** — once confirmed, choose the appropriate update:
   - **Extend the active phase** — if the work is small and closely related to the current phase, add a new task and acceptance criterion to the existing phase issue file.
   - **Create a new sub-phase** — if the work is a meaningful self-contained slice that builds on the current phase, create a new phase issue file (e.g., `phaseNb.issue.md`) and link it from the plan.
   - **Create a new phase** — if the work represents a distinct delivery milestone, add a new phase entry to the project plan and create the corresponding issue file.
   - **Update the project plan** — in all cases, ensure the plan file reflects the new scope, sequencing, and any shifted delivery order.
4. **Then implement** — only after `specs/` is updated proceed with the requested work, using the newly created or updated phase issue as the guiding document.

After completing meaningful work:

- Update the relevant phase issue if scope, tasks, acceptance criteria, or notes changed.
- Update `progress.status.md` when phase status, evidence, risks, or next actions changed.
- Reference the plan and phase context in summaries so future agents can continue from the intended roadmap.
- Review `docs/` for any pages that are now stale, incomplete, or contradicted by the changes just made. Update them in the same session — do not leave documentation drift for the next agent to discover.

### Precedence inside `specs/`

Use this order when interpreting project intent:

1. Active user instruction
2. The project plan in `specs/`
3. The relevant phase issue file
4. `progress.status.md`

If these conflict, do not guess silently. Align the files as part of the task or call out the mismatch clearly.

## What This Scaffold Should Cover

- Backend architecture and service boundaries
- Frontend architecture and UX delivery conventions
- Database and persistence guidance
- Infrastructure and environment strategy
- CI/CD pipeline design
- Observability and operational readiness
- Testing strategy across layers
- Delivery phases, progress tracking, and readiness gates
- AI-agent collaboration rules and handoff expectations

## Guardrails

- Do not hardcode domain language unless the current project has explicitly chosen it.
- Do not assume a specific stack unless documented in the active architecture decisions.
- Do not leave orphaned references to previous systems, modules, entities, or brands.
- Prefer templates, placeholders, checklists, and decision records when requirements are still open.
- Do not ignore the `specs/` plan, phase, or progress files when they exist for the active project.

## Documentation Expectations

When creating or editing docs:

- Use clear section headings and checklists.
- Separate confirmed decisions from open questions.
- Keep examples generic unless the repository already defines a concrete stack.
- Note dependencies between architecture, infrastructure, testing, and delivery decisions.
- Keep `docs/` aligned with the current phase plan and update `specs/` when documentation changes affect scope or sequencing.

## Coding Expectations

When source code exists:

- Follow the architecture and testing rules documented for the active project.
- Keep implementation consistent with CI/CD and observability expectations.
- Add or update tests for behavior changes.
- Avoid introducing tooling that conflicts with documented delivery workflows.
- Use the active project plan and phase issue as the default boundary for what should be implemented now.

Unless the project documents a different choice, assume these defaults:

- Use Clean Architecture or similarly strict modular boundaries for backend work.
- Keep domain or core logic independent from UI, transport, and infrastructure concerns.
- Treat unit, integration, and end-to-end testing as part of the minimum delivery baseline.
- Prefer test-driven or test-in-parallel development for non-trivial features and bug fixes.
- Add regression tests for defects at the most appropriate level.

### Frontend Tasks

When a task is primarily or substantially frontend work, spin up a subagent using the most recent Claude Sonnet version available and load the `frontend-design` skill before proceeding.

A task qualifies as primarily frontend when it involves:

- Creating or redesigning UI components, pages, or layouts
- Styling work: CSS, design tokens, theming, or visual polish
- Frontend-only state, interaction, or navigation logic

This does not apply to full-stack tasks where the UI change is incidental to backend work, backend-only or infrastructure changes, or minor copy and label edits inside existing components.

## Testing and TDD Discipline

Testing discipline is proportional to the impact of the change. Apply these rules to **substantial changes only**. Do not apply them to documentation edits, configuration tweaks, trivial one-liners, renaming without logic changes, or purely cosmetic changes.

### What Qualifies as Substantial

A change is substantial if it meets one or more of these conditions:

- Adds or changes a public API, endpoint, or function signature
- Introduces a new module, service, class, or architectural boundary
- Fixes a bug where the root cause can be verified by a test
- Changes logic that affects more than one call site or consumer

### Rules for Substantial Changes

- **Write tests first or alongside the implementation** — never after the phase or task is declared done.
- **Tests are part of the deliverable** — a task is not complete until its tests exist and pass. Tests must not be deferred to a follow-up phase or issue.
- **Layer expectations** (apply regardless of specific stack):
  - Core or domain logic → unit tests
  - Service boundaries, repositories, and external integrations → integration tests
  - User-facing flows where behavior is critical → E2E tests, proportional to the value delivered

### What Is Exempt

The following do not require new or updated tests:

- Documentation or comment edits
- Renaming or moving files with no logic change
- Formatting or linting-only fixes
- Environment or configuration-only changes
- Purely additive content such as adding a README section

## If the Repository Is Still in Template Mode

In template mode, optimize for clarity, reusability, low-coupling documentation, and smooth project kickoff.

Follow the **Bootstrap Mode** protocol defined earlier in this file before doing any Phase 0 implementation work. The kickoff questionnaire exists to ensure new projects start from an explicit, agreed baseline rather than silent scaffold defaults.

Even in template mode, keep the `specs/` workflow explicit so future projects inherit a plan-first execution model.
