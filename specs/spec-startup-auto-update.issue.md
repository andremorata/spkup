# Spec — Startup Auto-Update

> **Type:** Maintenance extension
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `Completed (declared)`
> **Created:** 2026-05-20
> **Depends on:** `specs/spec-nightly-release-automation.issue.md`

---

## Objective

Add a startup update check to the Spkup desktop app so installed Windows builds can discover newer GitHub Releases, ask the user for confirmation, download the matching release artifact, and apply the update through an automated staged flow.

---

## Why Now

- Nightly release automation is already producing release artifacts.
- Client-side auto-update delivery was explicitly out of scope for the nightly release spec.
- The app should make those releases discoverable from startup while preserving a settings toggle so the user can opt out.

---

## Out of Scope

- Code signing.
- Cryptographic signature verification.
- Installer UX beyond the existing ZIP/PyInstaller artifact.
- Background periodic checks after startup.
- Silent download or silent install without user confirmation.
- Cross-platform update support.

---

## Affected Areas

- Code / modules: `src/spkup/config.py`, `src/spkup/app.py`, `src/spkup/settings_dialog.py`, new update-check / update-apply modules.
- Docs: `README.md`, `docs/01-architecture.md`, `docs/06-packaging-release.md`.
- Tests: config migration, release selection, update check outcomes, updater command construction, and app/settings wiring.
- Manual verification surface: frozen Windows build startup, update prompt, download, staged replacement, restart, and disabled-toggle startup.

---

## Tasks

### Task 1 — Configuration and settings

**Deliverable:** persisted opt-out startup update configuration.

- [x] Add an `AppConfig` field that enables startup update checks by default.
- [x] Preserve backward-compatible load behavior for existing `config.json` files.
- [x] Add a Settings checkbox that can disable startup update checks.

**Acceptance criterion:** Existing configs load with update checks enabled unless the user explicitly saves them disabled. (AC-1)

---

### Task 2 — Release discovery

**Deliverable:** non-blocking GitHub Releases checker.

- [x] Query GitHub Releases for `andremorata/spkup`.
- [x] Ignore draft releases.
- [x] Treat normal releases as the primary channel; tolerate older pre-releases that may still exist in release history.
- [x] Compare semantic `vX.Y.Z` tags against the running `spkup.__version__`.
- [x] Select the matching `spkup-X.Y.Z-windows-x64.zip` asset.
- [x] Surface network/API/asset problems explicitly without disrupting normal startup.

**Acceptance criterion:** The checker reports update available, no update, or unavailable states without blocking the Qt main thread. (AC-2)

---

### Task 3 — Startup UX

**Deliverable:** startup prompt and user-controlled update action.

- [x] Start the checker during app startup only when the config toggle is enabled.
- [x] Ask for confirmation before downloading or applying an update.
- [x] Keep the app usable when update checks fail or find no update.

**Acceptance criterion:** No update bytes are downloaded until the user confirms the available update prompt. (AC-3)

---

### Task 4 — Staged Windows updater

**Deliverable:** automated apply path for frozen Windows builds.

- [x] Download the selected ZIP to a staging directory.
- [x] Validate that the ZIP contains `spkup.exe` inside the expected release bundle.
- [x] Launch a helper process that waits for the current app process to exit.
- [x] Extract the release bundle to a sibling directory, preserve a backup where practical, and restart the new `spkup.exe`.
- [x] No-op with a clear message when running from source.

**Acceptance criterion:** A frozen Windows build can stage an update without trying to overwrite its own running executable. (AC-4)

---

### Task 5 — Documentation and evidence

**Deliverable:** aligned maintenance docs and progress tracker.

- [x] Document the new runtime update path.
- [x] Document the limitations around unsigned ZIP updates.
- [x] Record automated validation evidence in `specs/progress.status.md`.

**Acceptance criterion:** The project plan, progress tracker, architecture docs, and release runbook describe how startup auto-update works. (AC-5)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | Startup update checks are enabled by default and can be disabled in Settings. | Config and settings tests. |
| AC-2 | Release discovery is non-blocking and distinguishes update available, no update, and unavailable outcomes. | Unit tests for release selection and worker behavior. |
| AC-3 | The app asks before downloading or applying an update. | App-level tests and manual startup check. |
| AC-4 | Frozen builds stage updates through a helper process after Spkup exits. | Updater command tests and manual frozen-build smoke test. |
| AC-5 | Docs and progress tracking are aligned with the new feature. | Review changed docs/specs. |

---

## Validation Plan

- Automated checks: targeted pytest files for config, update checker/updater, app startup wiring, and settings dialog integration; then full pytest suite.
- Manual checks: frozen Windows build startup with update available; disabled toggle; no-update startup; source-run update attempt.
- Evidence to capture in `specs/progress.status.md`: commands run, changed files, and any manual verification still pending.

---

## Risks and Notes

- Dependencies: GitHub Releases API availability and the existing `spkup-X.Y.Z-windows-x64.zip` artifact naming contract.
- Rollback or safety considerations: the updater should preserve the current bundle as a backup before replacing or switching the runtime directory where practical.
- Open questions: future work may add code signing, checksum artifacts, or channel selection if stable and nightly distribution diverge.

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. All acceptance criteria above are satisfied.
2. For every substantial code or behavior change, the corresponding tests are written or updated, passing, and referenced as evidence.
3. `specs/progress.status.md` records the validation summary, evidence, and next action.
