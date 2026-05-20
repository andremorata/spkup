# Spec — Nightly Stable Releases

> **Type:** Maintenance extension
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `Completed (declared)`
> **Created:** 2026-05-20
> **Depends on:** `specs/spec-nightly-release-automation.issue.md`

---

## Objective

Change the scheduled nightly automation so every successful nightly build publishes a normal GitHub Release instead of a GitHub pre-release.

---

## Why Now

- Startup auto-update now consumes GitHub Releases.
- The app is a personal Windows utility where frequent release versions are acceptable.
- Treating nightly artifacts as normal releases reduces channel ambiguity for the update checker.

---

## Out of Scope

- Changing the daily schedule.
- Changing version bump semantics.
- Changing artifact naming.
- Adding code signing or checksum verification.

---

## Affected Areas

- Code / workflows: `.github/workflows/nightly.yml`
- Docs: `docs/06-packaging-release.md`
- Specs/progress: `specs/spec-nightly-release-automation.issue.md`, `specs/progress.status.md`
- Tests: no Python runtime behavior changes.

---

## Tasks

### Task 1 — Publish scheduled builds as normal releases

**Deliverable:** nightly workflow release publication uses normal GitHub Releases.

- [x] Rename the publish step from pre-release language to release language.
- [x] Set `prerelease: false`.
- [x] Keep generated release notes and the existing Windows ZIP artifact.
- [x] Keep the bot-tag guard in `release.yml` unchanged so the tag push does not publish a duplicate release.

**Acceptance criterion:** A successful scheduled nightly run creates a normal GitHub Release for the bumped `vX.Y.Z` tag. (AC-1)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | `nightly.yml` publishes normal releases, not pre-releases. | Inspect workflow `softprops/action-gh-release` inputs. |

---

## Validation Plan

- Automated checks: workflow diff review; Python tests are not required because runtime code is unchanged.
- Manual checks: next scheduled or manually-dispatched nightly run should produce a release where GitHub does not show the pre-release badge.
- Evidence to capture in `specs/progress.status.md`: changed workflow input and docs/spec alignment.

---

## Risks and Notes

- The app may now auto-update more frequently because scheduled builds are considered normal releases.
- Existing older pre-releases remain on GitHub history but future scheduled releases should be normal releases.

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. The nightly workflow is configured with `prerelease: false`.
2. Documentation no longer describes the scheduled release as a pre-release-only channel.
3. `specs/progress.status.md` records the validation summary and next action.
