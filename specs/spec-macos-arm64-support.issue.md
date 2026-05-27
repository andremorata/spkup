# Spec - macOS ARM64 Support

> **Type:** Maintenance extension
> **Reference:** `specs/project.plan.md` - Post-MVP maintenance workflow
> **Status:** `In progress`
> **Created:** 2026-05-21
> **Depends on:** Phase 9 frozen Windows packaging baseline; current Windows release and update contracts

---

## Objective

Introduce first-class Apple Silicon macOS support while preserving the existing Windows 11 x64 baseline.

The intended initial support contract is:

- Development and runtime target: macOS 14+ on ARM64 / Apple Silicon, Python 3.12.
- Release artifact: `spkup-X.Y.Z-macos-arm64.zip`, containing `spkup.app` inside a versioned top-level folder.
- Runtime behavior: tray/menu-bar app, global push-to-talk trigger, microphone capture, local faster-whisper transcription, clipboard output, settings, model download/delete, logs, and graceful feature gating for Windows-only integrations.
- Release behavior: Windows artifacts and update flow remain unchanged; macOS artifacts are published alongside Windows artifacts once validated.

---

## Why Now

- User requested planning for supporting macOS ARM64.
- The current codebase and release docs are Windows-first: artifact naming, GitHub Actions jobs, update asset selection, autostart, config paths, model cache paths, CUDA packaging validation, and updater apply behavior all assume Windows.
- macOS requires explicit handling for Apple Silicon packaging, app permissions, unsigned app distribution limits, and non-CUDA inference defaults.

---

## Out of Scope

- Intel macOS x86_64 support.
- Linux support.
- Code signing, notarization, installer UX, Sparkle, Homebrew cask, or DMG packaging.
- CUDA, NVIDIA GPU runtime packaging, or GPU performance parity on macOS.
- Changing the Windows release artifact name, Windows CUDA validation contract, or Windows automatic update apply flow.
- Replacing faster-whisper or adding cloud transcription.

---

## Affected Areas

- Code / modules: platform/path helpers, `config.py`, `logging_setup.py`, `model_manager.py`, `autostart.py`, `playback_mute.py`, `update_checker.py`, `updater.py`, `__main__.py`, settings and tray wiring as needed.
- Packaging: `pyproject.toml`, `requirements.txt`, `spkup.spec` or a new macOS-specific PyInstaller spec, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/workflows/nightly.yml`.
- Docs: `README.md`, `docs/01-architecture.md`, `docs/03-testing.md`, `docs/04-delivery-workflow.md`, `docs/06-packaging-release.md`.
- Tests: path/config tests, platform guard tests, update asset selection tests, updater behavior tests, autostart tests, packaging metadata tests, and existing full-suite regression coverage.
- Manual verification surface: Apple Silicon Mac with microphone access, Accessibility/Input Monitoring permission for global hotkey capture, clipboard access, and packaged app launch.

---

## Tasks

### Task 1 - Define platform support contract

**Deliverable:** A documented macOS ARM64 contract that describes supported runtime behavior, explicitly unavailable features, artifact naming, and validation gates.

- [x] Confirm target macOS version range and Apple Silicon hardware baseline.
- [x] Decide whether initial macOS builds are source/dev only, packaged only, or both; default plan is both.
- [x] Document the macOS artifact shape as `spkup-X.Y.Z-macos-arm64.zip`.
- [x] Document unsigned app limitations and required macOS permissions.
- [x] Define platform-specific default runtime settings: keep existing Windows defaults, but use CPU-safe defaults for new macOS config files.
- [x] Preserve the Windows 11 x64 contract as the existing production baseline.

**Acceptance criterion:** Docs and specs clearly state what "macOS ARM64 supported" means and what is intentionally not promised. (AC-1)

---

### Task 2 - Remove hard Windows runtime assumptions

**Deliverable:** Runtime code can import and run on macOS without Windows-only modules or environment variables being required.

- [x] Introduce a small platform/path abstraction for config, logs, model cache, and update staging directories.
- [x] Introduce a small platform capability abstraction for supported update apply, autostart, playback muting, CUDA packaging validation, and platform artifact tags.
- [x] Keep Windows paths compatible with the existing `%APPDATA%` and `%LOCALAPPDATA%` behavior.
- [x] Use macOS paths under `~/Library/Application Support/spkup` and `~/Library/Caches/spkup`.
- [x] Guard Windows-only imports such as `winreg` so module import does not fail on macOS.
- [x] Feature-gate Windows-only playback muting and Windows update apply behavior instead of exposing broken controls.
- [x] Add an import smoke test that covers platform-sensitive modules on macOS and Windows-mocked branches.
- [x] Add unit tests covering Windows and macOS path selection and feature capability gates.

**Acceptance criterion:** The application package imports on macOS, existing Windows tests still pass, and platform-specific paths/features are selected deterministically. (AC-2)

---

### Task 3 - Make macOS runtime behavior usable

**Deliverable:** Core source-run behavior works on Apple Silicon macOS.

- [x] Use a platform-native Qt font fallback for overlay and settings preview text so macOS does not rely on Windows-only Segoe UI.
- [ ] Validate PyQt6 tray/menu-bar behavior on macOS and adjust labels or activation handling if needed.
- [ ] Validate `pynput` global hotkey behavior with macOS Accessibility/Input Monitoring permissions.
- [ ] Validate microphone capture via `sounddevice` and document the microphone permission prompt.
- [x] Use CPU-safe faster-whisper defaults on macOS; do not require CUDA-specific configuration.
- [x] Hide or disable unsupported Windows-only controls on macOS, including playback muting and Start on login unless LaunchAgent support is intentionally implemented in this slice.
- [x] Surface clear guidance when hotkey or microphone permissions are missing instead of failing silently.
- [ ] Confirm clipboard output and recent-history copy behavior through Qt.
- [x] Add or update tests for any runtime branching introduced for macOS.

**Acceptance criterion:** A source checkout on Apple Silicon can complete the core flow: start app, record via hotkey or tray/menu action, transcribe locally, and copy text to the clipboard. (AC-3)

---

### Task 4 - Add macOS ARM64 packaging

**Deliverable:** A reproducible PyInstaller package can be built for macOS ARM64.

- [x] Decide whether to share `spkup.spec` with platform conditionals or add a dedicated macOS spec.
- [x] Build a macOS app bundle or equivalent onedir package suitable for ZIP distribution.
- [x] Exclude Windows-only CUDA runtime collection and Windows CUDA bundle validation from macOS packaging.
- [x] Ensure bundled resources, PyQt6 plugins, faster-whisper, CTranslate2, sounddevice/PortAudio, and model-download dependencies are included.
- [x] Assert the packaged artifact is built on Apple Silicon and contains an ARM64 macOS executable, not an Intel or cross-labeled bundle.
- [x] Add packaging diagnostics equivalent to the Windows warning/xref artifacts where useful.

**Acceptance criterion:** A local or CI macOS ARM64 packaging run produces `spkup-X.Y.Z-macos-arm64.zip` and the extracted package launches on Apple Silicon. (AC-4)

---

### Task 5 - Extend CI and release automation

**Deliverable:** GitHub Actions validates and publishes macOS ARM64 artifacts alongside Windows artifacts.

- [x] Add a macOS ARM64 validation/build job if the repository has access to an Apple Silicon GitHub-hosted runner; otherwise document the required local packaging fallback.
- [x] Assert the CI runner architecture in the macOS job before packaging.
- [x] Keep the Windows CI/release/nightly jobs unchanged except for matrix or artifact aggregation work required to publish both platforms.
- [x] Ensure release and nightly workflows publish both `spkup-X.Y.Z-windows-x64.zip` and `spkup-X.Y.Z-macos-arm64.zip` when both platform jobs pass.
- [x] Ensure macOS packaging does not install the Windows `gpu` optional dependency or run Windows CUDA DLL validation.
- [x] Update artifact upload names and release notes expectations.

**Acceptance criterion:** Release automation has an explicit macOS ARM64 path that cannot accidentally publish a mislabeled Windows or CPU/CUDA-incomplete artifact. (AC-5)

---

### Task 6 - Make update checks platform-aware

**Deliverable:** Startup update checks select the current platform's artifact without regressing Windows auto-update apply.

- [x] Generalize update asset matching from Windows-only ZIP names to platform-specific asset names.
- [x] Select `spkup-X.Y.Z-windows-x64.zip` on Windows and `spkup-X.Y.Z-macos-arm64.zip` on Apple Silicon macOS.
- [x] Keep automatic apply restricted to Windows frozen builds until a signed/notarized macOS update strategy is chosen.
- [x] For macOS packaged builds, present a clear manual-update message with the matching release asset URL or disable apply while still detecting available releases.
- [x] Extend update checker and updater tests for both platforms.

**Acceptance criterion:** A release with both platform assets is interpreted correctly on Windows and macOS, and Windows automatic update tests continue to pass. (AC-6)

---

### Task 7 - Validate and document the support boundary

**Deliverable:** Automated and manual evidence is recorded before declaring macOS ARM64 support complete.

- [x] Run targeted tests for platform/path/update/packaging changes.
- [x] Run the full test suite on Windows or the primary dev environment.
- [x] Run macOS source-run smoke checks on Apple Silicon.
- [x] Run macOS packaged-artifact smoke checks on Apple Silicon.
- [x] Update docs with setup, permissions, packaging, release, troubleshooting, and known limitations.
- [x] Record validation evidence and next actions in `specs/progress.status.md`.

**Acceptance criterion:** `progress.status.md` records automated and manual evidence for every acceptance criterion before this work item is marked completed. (AC-7)

---

## Acceptance Criteria

| ID | Criterion | How To Verify |
| --- | --- | --- |
| AC-1 | macOS ARM64 support contract is documented without changing the Windows baseline. | Review `specs/spec-macos-arm64-support.issue.md`, `specs/project.plan.md`, README, and packaging docs. |
| AC-2 | Runtime imports and platform paths work on macOS without Windows-only environment variables or modules. | Run platform/path/autostart tests with macOS and Windows branches covered by monkeypatching. |
| AC-3 | Core source-run flow works on Apple Silicon. | Manual macOS smoke: app launch, tray/menu access, hotkey permission, microphone capture, local transcription, clipboard output. |
| AC-4 | macOS ARM64 packaging produces the expected ZIP artifact. | Build package and verify `spkup-X.Y.Z-macos-arm64.zip` contains a launchable macOS package. |
| AC-5 | CI/release/nightly automation has a macOS ARM64 path that preserves Windows artifacts. | Inspect workflow runs and release assets for both platform ZIPs. |
| AC-6 | Update checks select the current platform asset and preserve Windows auto-apply. | Run update checker/updater tests for Windows and macOS asset selection and apply gating. |
| AC-7 | Completion evidence is recorded. | Review `specs/progress.status.md` for automated commands, manual smoke results, changed files, and remaining risks. |

---

## Validation Plan

- Automated checks:
  - `python -m pytest tests/test_config.py tests/test_update_checker.py tests/test_updater.py -q`
  - Additional platform/path/autostart/packaging tests added by this spec.
  - Full suite: `python -m pytest tests/ -q`
  - CI workflow run with Windows and macOS ARM64 jobs, if runner access exists.
- Manual checks:
  - Apple Silicon source-run smoke with Accessibility/Input Monitoring and Microphone permissions.
  - Apple Silicon packaged-artifact smoke from the release ZIP.
  - Windows smoke or regression check if release workflow or shared runtime code changes affect Windows behavior.
- Evidence to capture in `specs/progress.status.md`:
  - Platform tested, macOS version, hardware architecture, package shape, test commands, manual permission observations, known limitations, and release asset names.

---

## Risks and Notes

- Dependencies: PyQt6, pynput, sounddevice/PortAudio, faster-whisper, CTranslate2, PyInstaller, and GitHub Actions runner availability all need Apple Silicon validation.
- Runtime permissions: macOS may require Accessibility/Input Monitoring for global hotkeys and Microphone permission for capture; first-run UX may need documentation or in-app guidance.
- Performance: initial macOS support is CPU-oriented unless a separately validated Apple Silicon acceleration path is introduced later.
- Distribution: unsigned and non-notarized app ZIPs can trigger Gatekeeper friction; signing/notarization is intentionally deferred.
- Release operations: if GitHub-hosted ARM64 macOS runners are unavailable, release automation may need a documented manual packaging handoff before full automation can be declared complete.
- Rollback or safety considerations: the Windows artifact and updater flow must remain releasable independently if macOS packaging fails.
- Open questions:
  - Should the default hotkey remain `ctrl+shift+space` on macOS or switch to a macOS-specific default after manual testing?

---

## Exit Gate

This maintenance item is closed only when all of the following are true:

1. All acceptance criteria above are satisfied.
2. For every substantial code or behavior change, the corresponding tests are written or updated, passing, and referenced as evidence.
3. `specs/progress.status.md` records the validation summary, evidence, and next action.
