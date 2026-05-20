# spec: Nightly Release Automation

> Maintenance work item — opened 2026-04-20.
> Amended 2026-05-20 by `specs/spec-nightly-stable-releases.issue.md`: scheduled builds now publish normal GitHub Releases instead of pre-releases.
> Do not extend the original MVP phase files (phase1–phase9) for this work.

---

## Problem Statement

The developer releases new versions of spkup manually today: bump the version in
`src/spkup/__init__.py`, create an annotated tag, and push — which fires `release.yml`.
This works but requires deliberate daily attention. Because the app is a personal tool
used daily, useful improvements land frequently and often go unreleased for days.

The developer wants a zero-touch release cadence: every evening the CI should check
whether new commits have landed since the last release and, if so, automatically build,
package, and publish a new release to GitHub — without the developer doing anything.
When nothing has changed, the check should cost nothing and produce zero noise.

---

## Solution

A new scheduled GitHub Actions workflow (`nightly.yml`) runs at 8 PM UTC every day.

1. **Early-exit gate** — compares the most recent `v*` git tag against HEAD. If they
   point to the same commit, the run exits cleanly with no output.
2. **Version resolver / bumper** — reads `__version__` from `src/spkup/__init__.py`,
   decides whether a bump is needed (handles orphaned-bump recovery), increments the
   patch component, commits with `[skip ci]`, and pushes to main.
3. **Test gate** — runs the full pytest suite; aborts the release if any test fails.
4. **Build and package** — runs PyInstaller and produces `spkup-X.Y.Z-windows-x64.zip`
   using the same steps as the existing `release.yml`.
5. **Tag and publish** — creates a `vX.Y.Z` annotated tag and publishes a GitHub
   Release with auto-generated release notes and the title `spkup vX.Y.Z`.

The existing `ci.yml` and `release.yml` workflows are not modified.

---

## User Stories

1. As a developer, I want the nightly workflow to run automatically at 8 PM UTC every day, so that I never have to remember to cut a release.
2. As a developer, I want the nightly workflow to detect whether there are new commits since the last release tag, so that no release is cut when nothing has changed.
3. As a developer, I want the workflow to exit silently and successfully when there are no new commits, so the daily schedule produces zero noise or notifications.
4. As a developer, I want the patch version to be automatically bumped in `__init__.py` and committed back to main when a nightly release is triggered, so that each release has a unique, semantically versioned identity.
5. As a developer, I want the version bump commit to include `[skip ci]` in the message, so that pushing it to main does not trigger the regular CI workflow in a feedback loop.
6. As a developer, I want the `github-actions[bot]` identity to be used for version bump commits, so that bot-made commits are clearly distinguishable from developer commits in git history.
7. As a developer, I want the nightly build to run the full test suite before publishing, so that a broken build is never distributed.
8. As a developer, I want the workflow to abort and fail visibly if tests fail (without publishing anything), so I am notified when nightly quality gates break.
9. As a developer, I want the nightly release to be published as a normal GitHub Release, so the desktop app can consume frequent releases through startup auto-update without channel ambiguity.
10. As a developer, I want the GitHub release title to match the normal release format (e.g., `spkup v0.1.3`), so scheduled and hand-cut releases share one release surface.
11. As a developer, I want release notes to be auto-generated from commits since the previous release tag, so I can review what changed without writing notes manually.
12. As a developer, I want the nightly artifact to follow the same naming convention as stable releases (`spkup-X.Y.Z-windows-x64.zip`), so that testing nightly builds follows the same process.
13. As a developer, I want to continue cutting stable releases manually by pushing a `v*` tag, with `release.yml` working exactly as today, so I retain full control over stable releases.
14. As a developer, I want the workflow to recover gracefully if a previous run bumped the version but failed before tagging, so that the version is not double-incremented on the next run.
15. As a developer, I want the entire new functionality contained in a single new workflow file, so that the change is minimal and easy to review or revert.

---

## Implementation Decisions

### New workflow file
- A single new file `.github/workflows/nightly.yml` is created.
- Trigger: `schedule` only — `cron: '0 20 * * *'` (20:00 UTC daily). No `push` trigger.
- Runner: `windows-latest` (matches the existing build environment).
- Required permissions: `contents: write` (for pushing version bump commits and tags).

### Early-exit gate (step 1 — lightweight)
- Checkout with `fetch-depth: 0` to get full tag history.
- Resolve the latest `v*` tag: `git describe --tags --abbrev=0 --match 'v*'`.
- Check for new commits: `git log <latest-tag>..HEAD --oneline`.
- If the output is empty → set `has_changes=false` as a step output and skip all
  subsequent steps via `if: steps.<id>.outputs.has_changes == 'true'`. Run exits `0`.

### Version resolver / bumper (step 2)
- Read `__version__` from `src/spkup/__init__.py`.
- Check whether the git tag `v{__version__}` already exists locally or on the remote.
  - If the tag **does NOT exist**: the previous nightly bumped the version but failed
    before tagging. Reuse the current `__version__` (no additional bump).
  - If the tag **DOES exist**: compute `new_version` = `X.Y.(Z+1)`, overwrite
    `src/spkup/__init__.py`, configure git identity as `github-actions[bot]`, commit
    with message `chore: bump version to X.Y.(Z+1) [skip ci]`, and push to main.
- Output `version` and `tag_name` (e.g., `v0.1.3`) for downstream steps.

### Test gate (step 3)
- Install project in editable mode plus dev/build extras.
- Run `python -m pytest tests/ -v`.
- Any test failure causes the workflow to fail and exit immediately; no artifact is
  built and no tag is created.
- The version bump commit (if already pushed) remains on main; it is intentionally
  reused as-is on the next successful nightly run (see recovery logic above).

### Build and package (step 4)
- Identical logic to the existing `release.yml` build steps:
  - `python -m pip install ".[build]"`
  - `python -m PyInstaller --clean spkup.spec`
  - Rename `dist/spkup` → `dist/spkup-X.Y.Z-windows-x64`
  - `Compress-Archive` to create `dist/spkup-X.Y.Z-windows-x64.zip`

### Tag and publish (step 5)
- Create an annotated tag on HEAD: `git tag -a vX.Y.Z -m "Release vX.Y.Z (nightly)"`.
- Push the tag: `git push origin vX.Y.Z`.
- Publish via `softprops/action-gh-release@v2` with:
  - `prerelease: false`
  - `generate_release_notes: true`
  - `name: spkup vX.Y.Z`
  - `tag_name: vX.Y.Z`
  - `files: dist/spkup-X.Y.Z-windows-x64.zip`

### Unchanged workflows
- `ci.yml` — not modified.
- `release.yml` — not modified; manual stable release process continues to work
  identically by pushing a `v*` tag.

---

## Testing Decisions

**What makes a good test for this feature:**
- Tests verify observable outcomes (release was/was not published, version was/was not
  bumped) rather than internal step details of the YAML.
- Workflow YAML logic cannot be unit-tested directly; rely on integration-level
  validation via `workflow_dispatch` or a test branch.

**Manual validation plan:**
1. Add a temporary `workflow_dispatch` trigger to `nightly.yml` on a test branch.
2. Confirm early-exit case: ensure the latest tag points to HEAD → trigger manually →
   verify workflow completes successfully with no release published.
3. Confirm trigger case: push a commit past the latest tag → trigger manually → verify
   version bump commit appears on main with `[skip ci]`, a new `vX.Y.Z` release
   appears on GitHub Releases, and the ZIP artifact is attached.
4. Confirm recovery case: simulate an orphaned bump (manually bump `__init__.py` and
   push without tagging) → trigger manually → verify no double-bump, correct tag, and
   successful release.
5. Remove the `workflow_dispatch` trigger before merging.

**Prior art in the codebase:**
- `ci.yml` and `release.yml` serve as reference for install, test, and packaging step
  patterns. The nightly workflow reuses identical step bodies where possible.

---

## Acceptance Criteria

- [ ] A single new file `.github/workflows/nightly.yml` is added; no other workflow files are modified.
- [ ] When HEAD equals the latest `v*` tag commit, the workflow exits `0` with no release and no output.
- [ ] When HEAD is ahead of the latest `v*` tag, the workflow bumps the patch version in `src/spkup/__init__.py`, commits with `[skip ci]`, and pushes to main.
- [ ] The version bump commit message matches `chore: bump version to X.Y.Z [skip ci]` and is authored by `github-actions[bot]`.
- [ ] Tests run before any artifact is built or tag is created.
- [ ] If tests fail, no version tag is created and no release is published (version bump commit may remain on main).
- [ ] A GitHub Release titled `spkup vX.Y.Z` is published with `prerelease: false`.
- [ ] The release includes the ZIP artifact `spkup-X.Y.Z-windows-x64.zip`.
- [ ] Release notes are auto-generated from commits since the previous tag.
- [ ] If `__version__` in `__init__.py` does not yet have a corresponding git tag, no additional patch bump is applied (orphaned-bump recovery).
- [ ] `release.yml` is not modified; pushing a manual `v*` tag still publishes a stable release.

---

## Out of Scope

- Code signing of the Windows artifact.
- Auto-update delivery to installed clients.
- Multi-platform builds (macOS, Linux).
- Notifications (Slack, email, webhook) on nightly success or failure.
- `workflow_dispatch` manual trigger in the final merged workflow.
- Semantic versioning with minor or major auto-bumps.
- Changelog file generation or commit.
- Retry logic on transient GitHub API or network failures.
- Running PyInstaller on a non-Windows runner (incompatible by design).

---

## Further Notes

- The workflow fires every day including weekends; this is intentional for a personal tool with frequent daily use.
- Version bump commits will appear in git log between code commits; they are identifiable by the `[skip ci]` marker and `chore: bump version to` prefix.
- If a developer manually cuts a stable release that advances the minor or major version (e.g., 0.2.0), the nightly will correctly read the new tag as its baseline and start incrementing patch from 0.2.1 onwards.
- The `generate_release_notes: true` option in `softprops/action-gh-release` instructs GitHub to auto-generate notes between the previous tag and the newly created one; this requires no additional setup beyond what already exists.
