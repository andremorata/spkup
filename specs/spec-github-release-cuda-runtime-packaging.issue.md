# Spec — GitHub Release CUDA Runtime Packaging

> **Type:** Maintenance extension
> **Reference:** `specs/project.plan.md` — Post-MVP maintenance workflow
> **Status:** `Completed (declared)`
> **Created:** 2026-05-21
> **Depends on:** Phase 9 frozen Windows packaging baseline

---

## Objective

Ensure GitHub-built Windows release bundles include the CUDA/cuDNN runtime DLLs required for `faster-whisper` GPU transcription, matching locally built bundles on the target Windows RTX machine.

---

## Why Now

- User reported that the installed GitHub release at `C:\Users\andre\.apps\spkup` transcribes too slowly, while the freshly built local bundle at `E:\spkup\dist\spkup` performs normally.
- Runtime logs showed the GitHub bundle falling back to CPU because `cublas64_12.dll` was missing.
- Bundle inspection showed the GitHub-installed app had only 3 relevant CTranslate2/CUDA DLLs, while the local build had 17 including NVIDIA cuBLAS/cuDNN/NVRTC DLLs.

---

## Out of Scope

- Changing transcription model defaults or inference quality settings.
- Adding a CPU-only release channel.
- Code signing or installer UX changes.

---

## Affected Areas

- Code / modules: `src/spkup/packaging_validation.py`
- Packaging: `pyproject.toml`, `requirements.txt`, `.github/workflows/*.yml`
- Docs: `README.md`, `docs/03-testing.md`, `docs/06-packaging-release.md`
- Tests: `tests/test_packaging_validation.py`
- Manual verification surface: downloaded GitHub release bundle on Windows with CUDA-capable hardware

---

## Tasks

### Task 1 — Package GPU runtime dependencies

**Deliverable:** Release and nightly workflows install the Windows GPU runtime dependency extra before PyInstaller runs.

- [x] Add a GPU optional dependency for CUDA/cuDNN wheel runtime libraries.
- [x] Install the GPU extra in CI, release, and nightly packaging jobs.
- [x] Keep local requirements aligned for reproducible Windows builds.

**Acceptance criterion:** A GitHub Actions packaging environment has NVIDIA runtime wheels available before `spkup.spec` collects binaries. (AC-1)

---

### Task 2 — Fail packaging when CUDA DLLs are missing

**Deliverable:** Automated validation checks the frozen bundle for critical CUDA/cuDNN DLLs before ZIP publication.

- [x] Add a pure-Python bundle validator.
- [x] Cover the validator with tests.
- [x] Run the validator in CI, release, and nightly workflows after PyInstaller and before archive publication.

**Acceptance criterion:** CPU-only or incomplete CUDA bundles fail before they can be uploaded as release artifacts. (AC-2)

---

### Task 3 — Document the release contract

**Deliverable:** Docs explain that release artifacts are GPU-capable and how to validate the runtime DLL contract.

- [x] Update packaging and testing docs.
- [x] Update progress evidence after validation.

**Acceptance criterion:** Future release operators and agents can see the GPU runtime packaging requirement and validation command. (AC-3)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | Packaging jobs install GPU runtime wheels before PyInstaller. | Inspect `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `.github/workflows/nightly.yml`. |
| AC-2 | Incomplete frozen bundles fail packaging validation. | `python -m pytest tests\test_packaging_validation.py -q` |
| AC-3 | Release docs describe the GPU runtime packaging contract. | Review updated docs and progress tracker. |

---

## Validation Plan

- Automated checks: targeted packaging-validation tests, full pytest suite, local `python -m spkup.packaging_validation E:\spkup\dist\spkup`.
- Manual checks: install next GitHub release and confirm logs do not show CUDA missing-DLL fallback.
- Evidence to capture in `specs/progress.status.md`: failing symptom, root cause, changed files, test commands.

---

## Risks and Notes

- Dependencies: NVIDIA CUDA/cuDNN wheels substantially increase release artifact size.
- Rollback or safety considerations: workflow-only rollback restores previous smaller artifact but reintroduces CPU fallback risk.
- Open questions: none.

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. All acceptance criteria above are satisfied.
2. For every substantial code or behavior change, the corresponding tests are written or updated, passing, and referenced as evidence.
3. `specs/progress.status.md` records the validation summary, evidence, and next action.
