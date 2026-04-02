# Phase 9 — Packaging, GitHub CI/CD, Versioning, and Releases

> **Reference:** `specs/project.plan.md` — Phase 9
> **Depends on:** Phase 8 validated
> **Unlocks:** None — final phase

---

## Objective

Implement the packaging and release automation milestone for `spkup`: establish a repeatable Windows frozen-build baseline with PyInstaller, add GitHub Actions workflows for validation and release automation, define the project versioning policy, and publish Windows artifacts through GitHub Releases. The local implementation work is in place, but the phase is not complete until external GitHub validation and manual frozen-app validation are performed.

---

## Out of Scope

- Code signing for executables or installers
- Auto-update mechanisms
- Cross-platform packaging for macOS or Linux
- Server or cloud distribution channels beyond GitHub Releases

---

## Dependencies

- Phase 8 validated: desktop app behavior is stable enough to package and distribute
- Windows build environment suitable for PyInstaller-based frozen builds
- GitHub repository with Actions and Releases available for CI and distribution

---

## Tasks

### Task 9.1 — Windows packaging baseline

**Deliverable:** PyInstaller-based Windows frozen build definition and documented local packaging command

- [x] Add a baseline PyInstaller build configuration for the current Windows desktop app entry point
- [x] Ensure the frozen build includes the resources and runtime files required for launch on a clean Windows machine
- [x] Define the output artifact shape for the first supported Windows package baseline
- [ ] Verify the packaged build launches and preserves the core user flow: tray startup, hotkey capture, transcription, overlay, and clipboard result

**Acceptance criterion:** A repeatable local packaging command produces a runnable Windows frozen artifact from a clean checkout, and manual validation confirms the packaged app can complete the primary transcription flow. (AC-9.1)

---

### Task 9.2 — GitHub CI for repeatable validation on PR/push

**Deliverable:** GitHub Actions CI workflow for repeatable validation on pull requests and pushes

- [x] Add a GitHub Actions workflow that runs on pull requests and pushes to the main development branch
- [x] Run the project test suite in CI with the repository's supported Python version
- [x] Include packaging-oriented validation that catches regressions relevant to the Windows frozen-build baseline
- [x] Make CI results the repeatable validation baseline for future packaging and release work

**Acceptance criterion:** Pull requests and pushes trigger a GitHub Actions workflow that completes repeatable validation successfully and fails predictably when tests or packaging validation break. (AC-9.2)

---

### Task 9.3 — Versioning and tag/release policy

**Deliverable:** Enforced release versioning convention for source, Git tags, and release artifacts

- [x] Define the project source version format as `X.Y.Z`
- [x] Align release tags to the Git convention `vX.Y.Z`
- [x] Ensure the packaged artifact version and release naming strategy derive from the same source version
- [x] Define the operator workflow for preparing a release version, creating the corresponding tag, and avoiding version/tag drift

**Acceptance criterion:** For a candidate release, the application source version, the Git tag, and the generated release artifact naming all align as `X.Y.Z` and `vX.Y.Z` without manual one-off adjustments. (AC-9.3)

---

### Task 9.4 — Release workflow to publish Windows artifacts to GitHub Releases

**Deliverable:** GitHub Actions release workflow that publishes Windows artifacts to GitHub Releases

- [x] Add a GitHub Actions release workflow triggered by the approved release tag convention
- [x] Build the Windows PyInstaller artifact in the release workflow
- [x] Publish the generated Windows artifact to the matching GitHub Release
- [x] Ensure the release workflow is repeatable and tied to the defined version/tag policy

**Acceptance criterion:** Creating a release tag in the `vX.Y.Z` format triggers automation that builds the Windows artifact and publishes it to the matching GitHub Release without manual artifact upload. (AC-9.4)

---

## Acceptance Criteria

| ID | Criterion | How To Verify | Current Status |
| --- | --- | --- | --- |
| AC-9.1 | PyInstaller baseline produces a runnable Windows frozen build | Run the documented packaging command from a clean checkout on Windows; launch the produced artifact and complete the primary transcription flow | Packaging build passes locally; manual frozen-app flow validation is still pending |
| AC-9.2 | GitHub Actions provides repeatable validation on PR/push | Open a pull request or push a branch change; verify the CI workflow runs tests and packaging-oriented validation successfully | Workflow is implemented locally, but no GitHub remote is configured so Actions has not been exercised |
| AC-9.3 | Source version, Git tags, and release naming follow one policy | Prepare a candidate release and verify `X.Y.Z` source version maps directly to `vX.Y.Z` tag and artifact naming | Implemented and validated locally |
| AC-9.4 | GitHub Releases is the automated distribution channel for Windows artifacts | Create a `vX.Y.Z` tag in a test release scenario and verify GitHub Actions publishes the Windows artifact to the matching GitHub Release | Release workflow is implemented locally, but no GitHub remote is configured so GitHub Releases automation has not been exercised |

---

## Risks and Notes

- PyInstaller packaging may require explicit handling for PyQt6 resources, runtime hooks, or model/runtime dependencies that behave differently in a frozen build than in local development.
- GitHub-hosted Windows runners may expose environment-specific packaging differences that do not appear in a local workstation build.
- This phase remains open because two validations are still outstanding: GitHub Actions and Releases cannot be exercised without a GitHub remote, and the packaged Windows app still needs manual primary-flow validation.

---

## Implementation Notes

- 2026-04-01: Local Phase 9 implementation is in place for the versioning contract, packaging baseline, CI workflow, and release workflow.
- 2026-04-01: Local validation passed: `pytest` 48/48, `py_compile` clean, PyInstaller build succeeded, and workflow files were reviewed as sane.
- 2026-04-01: Phase 9 is not complete. Remaining blockers are external/manual: configure a GitHub remote so Actions and Releases can be exercised, then manually validate the frozen Windows app primary flow.

---

## Exit Gate

The phase is closed when all of the following are true:

1. All `AC-9.X` rows in the table above are satisfied.
2. For every substantial change in this phase — packaging configuration, CI workflow, versioning enforcement, or release automation — the corresponding validation is implemented, passing, and referenced below as evidence.
3. `progress.status.md` is updated with the validation summary, evidence (commands run, workflow runs, release links, commit references), and the next action.

Do not mark the phase as `Completed (validated)` until all three conditions are met.
