# spec: Manual Cancellation of In-Progress Transcription

> Maintenance work item - opened 2026-04-22.
> Status: **Completed (declared)** — hotkey-first slice shipped 2026-04-22.
> Do not extend the original MVP phase files (phase1-phase9) for this work.

---

## Problem Statement

spkup currently treats the transcription phase as fire-and-wait. Once audio capture
ends and the app enters the transcribing state, the user cannot manually cancel the
in-progress transcription. That is acceptable on the happy path, but it becomes
costly when model load is slow, inference stalls, the wrong recording was made, or
the user simply wants to abort and try again immediately.

User request: permitir cancelar manualmente uma transcricao em andamento / allow
manual cancellation of an in-progress transcription.

This is a post-MVP behavior change and must be tracked as a new maintenance item,
not as an extension of historical Phase 8 transcription-resilience work.

## Proposed Solution

Add a single app-level cancellation entry point for the transcription phase and route
the first interaction through the existing hotkey surface. Cancellation is available
only while transcription is in progress. It is not available during live audio
capture.

The app-level cancel entry point becomes the contract for all future cancel
affordances. A later overlay cancel button may be added, but it must call the same
app-level method rather than duplicating state or worker teardown logic.

## Interaction Options Considered

### Option A - Hotkey-first

- Reuse an interaction surface the user already has in muscle memory.
- Keeps the first slice narrow because it can stay mostly within App-level state,
  hotkey routing, and transcription lifecycle handling.
- Lets the repo validate cancellation semantics before committing to overlay UI
  changes.

### Option B - Overlay cancel button first

- More discoverable for a future broader audience.
- Requires additional overlay affordance work, interaction design, and UI-state
  handling in the first slice.
- Risks coupling the first implementation to overlay behavior before the underlying
  cancellation contract is stable.

### Recommendation

Implement hotkey-first in the first maintenance slice, while shaping the
architecture so a future overlay cancel button can reuse the same app-level cancel
entry point.

## Recommended First Slice

- Detect cancel requests only when the app is already transcribing.
- Route the request through a single App-level cancel helper.
- Treat cancel as a neutral discard of the active transcription result.
- Return the overlay and app state to idle without writing clipboard/history.
- Reuse existing trigger-guard boundaries so the cancel gesture does not bounce the
  app back into recording.
- Leave overlay-button work for a later maintenance item.

## Explicit Behavior on Cancel

- Cancellation is available only during transcription. It is not available during
  live audio capture.
- When cancellation is accepted, the active transcription result is discarded even if
  the worker later finishes.
- A canceled transcription must not write to the clipboard.
- A canceled transcription must not append to recent transcription history.
- A canceled transcription must return the overlay to the idle/hidden state rather
  than DONE or ERROR.
- A canceled transcription must leave the app ready for a later fresh recording; the
  cancel gesture itself must not reactivate recording because of hotkey release
  handling, tray activation handling, or trigger-guard regressions.
- Existing watchdog timeout, automatic fallback, manual retry, empty-transcription,
  and failure/error flows must keep working for non-cancel cases.
- Manual cancel is a neutral exit, not a failure state. It must not trigger timeout
  handling, retry UI, or error signaling just because the user canceled.
- A future overlay cancel button must call the same app-level cancel entry point used
  by the hotkey path.

## Acceptance Criteria

- [x] While the app is transcribing, the chosen cancel interaction invokes a single
      app-level cancel entry point.
- [x] While the app is recording audio, the same interaction does nothing
      cancellation-specific and capture behavior remains unchanged.
- [x] After a cancel, no clipboard write occurs and no transcription-history entry is
      created for the canceled job.
- [x] After a cancel, the overlay returns to idle/hidden state and the user can start
      a fresh recording with the normal workflow.
- [x] After a cancel, the cancel gesture does not re-enter recording because of
      hotkey release handling, tray activation handling, or other trigger-guard
      regressions.
- [x] Existing timeout/watchdog, automatic CUDA-to-CPU fallback, manual retry from
      the tray, empty-transcription handling, and error-overlay behavior remain
      unchanged for non-cancel paths.
- [x] The architecture leaves a single app-level cancel entry point that a future
      overlay cancel button can call without duplicating cancellation logic.

## Delivered Slice (2026-04-22)

Implementation summary:

- `Transcriber.clear_retry_state()` added so a user-initiated cancel can drop the
  retained audio/params without touching worker lifecycle helpers.
- `App._transcribing_active` added as the single source of truth for the
  transcribing state; set true when audio capture finishes and recording
  transitions to transcription, reset on finished/error/timeout-terminal/cancel,
  and preserved across CUDA→CPU auto-retry and manual retry.
- `App._cancel_active_transcription(source)` added as the single app-level cancel
  entry point. It stops the watchdog, calls `Transcriber.cancel_active()` to
  discard the active worker (late results are ignored by existing job-id logic),
  calls `Transcriber.clear_retry_state()` so the canceled audio is not offered
  for manual retry, hides the overlay, disables the retry action, resets the
  CUDA-retry flag, and arms the existing 1-second trigger-suppression window so
  the cancel gesture does not bounce straight back into recording.
- `App._request_recording_start` now routes any start trigger (hotkey or tray)
  received while transcribing through `_cancel_active_transcription` instead of
  starting a new recording. Recording-state requests outside transcription are
  unchanged.
- No overlay affordance was added in this slice. A future overlay cancel button
  must call `App._cancel_active_transcription` rather than duplicating teardown.

Delivery classification: **discard-only cancel**. The low-level faster-whisper
worker is not hard-killed; it is detached so any late result or error is
dropped, and the UI/app side-effect contract (no clipboard, no history, idle
overlay, ready for new recording) is honored. A future maintenance item can
upgrade to true worker-stop semantics while keeping the same app-level entry
point.

Tests added in `tests/test_app_transcription_cancel.py`:

- cancel-during-transcribing discards the worker, hides the overlay, disables
  retry, and arms the suppression window
- cancel outside transcribing is a no-op
- cancel does not copy to clipboard or append to history
- start triggers from hotkey and tray are both routed to cancel while
  transcribing, and a fresh start still works after the suppression window
- `_transcribing_active` is cleared on finished/error/timeout-terminal and
  preserved across CUDA→CPU auto-retry and manual retry
- `Transcriber.clear_retry_state()` disables `has_pending_retry`

Validation evidence:

- `$env:PYTHONPATH='src'; .\.venv\Scripts\python -m pytest tests/ -q` — 162
  passed, 0 failed.

## Out of Scope

- Canceling or pausing live audio capture.
- Adding new settings UI for cancel behavior.
- Shipping the overlay cancel button in this maintenance item.
- Reworking the broader transcription worker architecture beyond what is needed for
  safe cancellation.
- Changing watchdog timeout defaults, retry policy, or error copy unless required by
  implementation.

## Implementation Notes

- Prefer explicit App-level state and job ownership over worker-thread side effects.
- Treat cancel as discard-active-result semantics even if low-level inference cannot
  be hard-killed immediately; the UI and side-effect contract matters first.
- The cancel entry point should own three concerns: mark the active job canceled,
  restore UI/application state to idle, and coordinate the redundant-start
  protections needed to avoid unintended re-recording.
- If worker teardown cannot be synchronous, use job tokens, generation IDs, or
  canceled flags so late completions are ignored safely.
- Any future overlay cancel button should be a thin UI layer over the same App-level
  cancel helper.
- Logging should distinguish manual cancel from timeout/error so operational evidence
  stays readable.

## Testing Notes

- Add or update focused tests around App-level trigger guards and transcription
  lifecycle handling rather than relying only on end-to-end UI checks.
- Cover at least:
  - cancel accepted during transcribing
  - cancel ignored outside transcribing
  - late worker completion after cancel is ignored
  - no clipboard/history side effects on cancel
  - no unintended recording restart on hotkey release or tray event after cancel
  - existing timeout, retry, and error flows still pass unchanged
- Manual verification should confirm overlay state transitions and that a fresh
  recording can be started after cancel.

## Risks

- If cancellation only hides the UI but does not ignore late worker results,
  clipboard/history corruption can still occur.
- Hotkey release timing may reopen recording immediately after cancel unless the
  existing trigger-guard boundary is reused carefully.
- A too-coupled implementation could make the later overlay button duplicate logic or
  diverge from the hotkey path.
- If worker cancellation semantics are unclear, the first slice may need a discard-
  only strategy before true hard-stop behavior.

## Validation Plan

- Automated checks:
  - targeted pytest coverage for app cancel lifecycle and trigger guards
  - full regression run for transcription resilience, history, empty-transcription,
    and trigger-guard slices after implementation
- Manual checks:
  - start recording, release to transcribing, cancel via hotkey, confirm overlay
    hides, clipboard/history stay unchanged, and a new recording can be started
    normally
  - verify cancellation is unavailable during audio capture
  - verify timeout, manual retry, and error paths still behave as before when cancel
    is not used
- Evidence to capture in `specs/progress.status.md`:
  - commands run
  - key files changed
  - whether the delivered slice is discard-only or true worker-stop
  - confirmation that the overlay button remains future work using the same entry
    point
