# Spec - Recording limit visibility in capture overlay

> **Type:** Maintenance extension
> **Reference:** `specs/project.plan.md` - Post-MVP maintenance workflow
> **Status:** `Completed (declared)`
> **Created:** 2026-05-20
> **Depends on:** Existing recording safety cutoff in `src/spkup/recorder.py`

---

## Objective

Make the recording time limit explicit while capture is in progress so the user can
see how much time is left before the app stops recording and submits the transcript.

---

## Why Now

- User feedback: recording currently stops at a predefined limit without clear
  visual warning, which makes the automatic transcription/copy flow feel abrupt.
- The current overlay shows only a static `Capturing` state even though the safety
  cutoff is already enforced by the recorder.

---

## Out of Scope

- Making the recording limit configurable in Settings.
- Changing the timeout outcome away from the current "stop, transcribe, copy"
  contract.
- Reworking transcription timeout, retry, or cancel behavior outside the recording
  phase.
- Adding a new modal confirmation step before clipboard copy.

---

## Affected Areas

- Code / modules:
  - `src/spkup/app.py`
  - `src/spkup/overlay.py`
  - `src/spkup/recorder.py`
- Docs:
  - `README.md`
  - `docs/01-architecture.md`
  - `docs/03-testing.md`
  - `specs/progress.status.md`
- Tests:
  - `tests/test_app_recording_countdown.py`
  - `tests/test_overlay.py`
- Manual verification surface:
  - Capture overlay during an active recording on Windows

---

## Tasks

### Task 1 - Track the recording countdown

**Deliverable:** App-level countdown lifecycle aligned with the existing recorder
limit.

- [x] Start countdown updates when recording actually begins.
- [x] Stop and clear countdown state on stop, error, cancel, cleanup, and timeout.
- [x] Keep the existing timeout outcome: stop recording, then continue into
      transcription/copy.

**Acceptance criterion:** The app exposes the remaining recording time throughout an
active capture session and clears it whenever capture ends. (AC-1)

---

### Task 2 - Render remaining time in the overlay

**Deliverable:** Recording overlay shows remaining time clearly enough that the limit
is not a surprise.

- [x] Extend the recording overlay state to render countdown information.
- [x] Make near-zero time visually distinct from the normal recording state.
- [x] Preserve existing non-recording overlay states.

**Acceptance criterion:** During `OverlayState.RECORDING`, the overlay visibly shows
the remaining time before submission and remains readable near zero. (AC-2)

---

### Task 3 - Lock behavior with regression coverage and docs

**Deliverable:** Automated coverage for countdown behavior and updated operational
documentation.

- [x] Add regression tests for countdown formatting/rendering helpers.
- [x] Add regression tests for App countdown lifecycle and timeout path.
- [x] Update README/docs/tracker notes to describe the new recording feedback.

**Acceptance criterion:** The countdown UX and timeout contract are documented and
covered by repeatable tests. (AC-3)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | Recording start arms a visible countdown tied to `max_recording_seconds`, and capture end clears it. | Automated App-level tests |
| AC-2 | The overlay shows the remaining time during `RECORDING`, including an urgent low-time presentation near zero. | Automated helper/widget tests + manual Windows check |
| AC-3 | The current timeout outcome remains "stop, transcribe, copy", but it is now signaled clearly in docs/tests/tracker. | Tests + docs review |

---

## Validation Plan

- Automated checks:
  - `pytest tests/test_app_recording_countdown.py tests/test_overlay.py -q`
  - `pytest tests -q`
- Manual checks:
  - Start recording and confirm the overlay shows a live countdown.
  - Let the countdown reach zero and confirm recording stops, transcription proceeds,
    and the transition is visually unsurprising.
  - Stop recording early and confirm the countdown disappears immediately.
- Evidence to capture in `specs/progress.status.md`:
  - Commands run
  - Key files changed
  - Manual Windows validation status

---

## Risks and Notes

- Dependencies: overlay rendering must stay compatible with the existing animation
  system and click-through widget setup.
- Rollback or safety considerations: the recorder safety timer remains the source of
  truth for the actual cutoff; the overlay countdown is informational and must not
  drift badly enough to mislead the user.
- Open questions: none; timeout still stops recording and continues into the current
  transcription/copy flow.

---

## Delivered Slice (2026-05-20)

Implementation summary:

- `src/spkup/overlay.py` now builds a recording countdown visual (`mm:ss`,
  progress, urgent flag), renders it in the capture overlay, and highlights the
  last 10 seconds with a more urgent presentation.
- Follow-up visibility tuning: after initial user feedback that the countdown was
  still hard to notice, the recording overlay was rebalanced so the remaining
  time becomes the dominant element (larger pill, stronger typography, explicit
  captioning for normal vs urgent state).
- Follow-up runtime fix: user verification initially kept showing the pre-change
  overlay because `python -m spkup` from the worktree root was resolving an
  editable install from another checkout. A repo-root `spkup` shim now routes
  local runs to this worktree's `src/spkup` sources so interactive verification
  matches the files being edited.
- `src/spkup/app.py` now owns the recording countdown lifecycle: start on live
  capture begin, refresh every 100 ms, and clear on stop, error, cleanup, and
  any transition away from capture.
- `src/spkup/recorder.py` keeps the safety cutoff as the source of truth and now
  exposes `set_max_seconds(...)` so future config changes can keep recorder and
  overlay timing aligned.
- The timeout outcome is unchanged by design: when the limit is reached,
  recording stops and the app continues into transcription/copy as before, but
  the user now sees the remaining time throughout capture.

Validation evidence:

- `pytest tests/test_overlay.py tests/test_app_recording_countdown.py tests/test_recorder.py -q`
- `pytest tests -q`

Manual Windows verification of the live overlay countdown and near-zero visual
urgency is still pending.

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. All acceptance criteria above are satisfied.
2. For every substantial code or behavior change, the corresponding tests are written
   or updated, passing, and referenced as evidence.
3. `specs/progress.status.md` records the validation summary, evidence, and next
   action.
