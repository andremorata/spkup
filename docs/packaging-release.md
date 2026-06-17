# spkup — Packaging and Release Runbook

> Release/versioning contract baseline. This file defines the version source of truth, supported platform artifact shapes, and the operator workflow to prepare and cut a release.

---

## 1. Versioning Contract

The project uses one authoritative release version:

- Source version format: `X.Y.Z`
- Source of truth: `src/spkup/__init__.py`
- Build metadata source: Hatchling reads the version from `src/spkup/__init__.py`
- Git release tag format: `vX.Y.Z`
- Release title and artifact names: derived from the same `X.Y.Z`

Examples:

- Source version: `0.1.0`
- Git tag: `v0.1.0`
- Release artifacts: `spkup-0.1.0-windows-x64.zip`, `spkup-0.1.0-macos-arm64.zip`

Rules:

1. Do not set a release version anywhere else in the repository metadata.
2. Do not create a release tag that does not match `src/spkup/__init__.py`.
3. Do not rename release artifacts by hand to a different version string.

---

## 2. Platform Artifact Baseline

The Windows release artifact remains the production baseline:

- Platform: Windows 11 x64
- Packaging direction: PyInstaller frozen build
- Distribution channel: GitHub Releases
- Artifact form: versioned ZIP archive containing the runnable Windows app bundle

Baseline artifact naming:

- Archive: `spkup-X.Y.Z-windows-x64.zip`
- Expanded app folder: `spkup-X.Y.Z-windows-x64/`
- Primary executable inside the bundle: `spkup.exe`

Baseline expectations for the first packaged release:

- The artifact is built from a tagged commit
- The artifact launches on a clean Windows machine with the expected runtime files bundled
- The artifact includes the NVIDIA CUDA/cuDNN runtime DLLs required for GPU transcription on the target Windows RTX machine
- The artifact supports the core user flow: tray startup, hotkey capture, recording, transcription, overlay feedback, and clipboard output

The macOS ARM64 release artifact is additive and does not replace the Windows baseline:

- Platform: Apple Silicon macOS ARM64
- Packaging direction: PyInstaller `.app` bundle wrapped in a versioned ZIP folder
- Distribution channel: GitHub Releases
- Artifact form: `spkup-X.Y.Z-macos-arm64.zip`
- Expanded app folder: `spkup-X.Y.Z-macos-arm64/`
- Primary app inside the folder: `spkup.app`
- Primary executable inside the app: `spkup.app/Contents/MacOS/spkup`
- Runtime default: CPU/int8 faster-whisper

The macOS artifact must be built on an Apple Silicon runner or host and the packaged executable must report `arm64` via `file`.

Current platform baselines do not yet promise:

- Code signing
- Installer UX
- macOS notarization
- macOS automatic update apply
- Intel macOS or Linux artifacts

---

## 3. Release Preparation Checklist

Before cutting `vX.Y.Z`:

1. Confirm the working tree is ready for release.
2. Update `src/spkup/__init__.py` so `__version__` is the intended `X.Y.Z` release.
3. Run local automated validation:

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest
```

4. If validating a Windows frozen release candidate, confirm the CUDA runtime DLL
   contract before packaging or upload:

```bash
python -m spkup.packaging_validation dist\spkup
```

5. If validating a macOS ARM64 release candidate, build and verify the package:

```bash
python -m PyInstaller --clean spkup-macos.spec
file dist/spkup.app/Contents/MacOS/spkup
```

Then wrap it as `spkup-X.Y.Z-macos-arm64.zip` with `spkup.app` inside the versioned top-level folder.

6. Run the local manual smoke checks required for the current release candidate on every affected platform:

- App starts successfully
- Tray/menu-bar icon appears and quit still works
- Hotkey starts and stops capture correctly
- A spoken sample produces transcription output
- Overlay state changes remain correct
- Clipboard receives the transcription result
- macOS prompts or already has Microphone and Accessibility/Input Monitoring permissions
- macOS unsigned-app launch friction is documented for the candidate

7. Verify the release version contract is still aligned:

- `src/spkup/__init__.py` contains `X.Y.Z`
- Intended Git tag is `vX.Y.Z`
- Intended artifact names use `X.Y.Z` for both platform ZIPs

If any of those values differ, stop and correct the version source before tagging.

---

## 4. Cutting the Release

Use the following operator workflow to prepare and publish a release:

1. Commit the release-preparation changes, including the version bump if one was required.
2. Create an annotated tag that matches the source version exactly:

```bash
git tag -a vX.Y.Z -m "spkup vX.Y.Z"
```

3. Push the commit and tag:

```bash
git push origin <branch>
git push origin vX.Y.Z
```

4. Push the matching `vX.Y.Z` tag.
5. The GitHub Actions workflow in `.github/workflows/release.yml` builds Windows and macOS ARM64 artifacts and publishes both ZIPs to the matching GitHub Release only after both platform builds succeed.

The local validation and version-alignment checks above still happen before tagging. The release workflow automates packaging and upload after the matching tag is pushed; it does not change the version contract.

---

## 5. Automation Boundary

Future workflow changes should preserve this contract rather than replace it:

- Packaging configuration should derive artifact names from `src/spkup.__version__`
- CI should validate tests and packaging against the same version source
- Release automation should trigger only from `vX.Y.Z` tags
- GitHub Release names and uploaded artifacts should use the same `X.Y.Z`

If a future workflow needs additional metadata, add it around this contract instead of introducing a second version source.

Windows release and nightly packaging jobs install the `gpu` optional dependency
group before PyInstaller runs. This makes NVIDIA runtime wheels available for
`spkup.spec`, which collects their DLLs into the frozen bundle. The workflows
then run `python -m spkup.packaging_validation dist\spkup` before ZIP
publication; missing critical CUDA/cuDNN DLLs fail the Windows build instead of
publishing a CPU-fallback artifact.

macOS release and nightly packaging jobs intentionally do not install the
Windows `gpu` optional dependency group and do not run CUDA DLL validation. They
build from `spkup-macos.spec`, assert `uname -m` is `arm64`, and verify the
packaged executable is arm64 before ZIP publication.

---

## 6. Runtime Auto-Update Contract

Packaged builds check GitHub Releases on startup by default. The runtime updater uses the same release contract defined above:

- Eligible release tags are semantic `vX.Y.Z` tags.
- Draft releases are ignored.
- Scheduled nightly builds publish normal GitHub Releases, so the updater primarily tracks normal releases.
- Older pre-releases may still exist in release history, but future scheduled artifacts should not carry the pre-release badge.
- The app only considers a release relevant when it includes the current platform asset:
  - Windows: `spkup-X.Y.Z-windows-x64.zip`
  - macOS ARM64: `spkup-X.Y.Z-macos-arm64.zip`
- The user is prompted before any download or apply step.
- Source/development runs can detect that an update exists, but automatic apply is only supported in frozen Windows builds.
- macOS packaged builds detect matching releases and show manual-update guidance; automatic apply is deferred until a signing/notarization strategy exists.

The apply flow is staged because Windows cannot safely overwrite the running executable. After the user confirms, Spkup downloads the ZIP under `%LOCALAPPDATA%/spkup/updates`, validates that it contains the expected `spkup.exe`, launches a helper PowerShell process, exits, and lets the helper extract and start the new bundle.

Current limitations:

- Release ZIPs are not code-signed.
- No separate checksum or signature artifact is verified.
- There is no channel selector yet; scheduled releases are treated as the active release stream by design.
- macOS artifacts are unsigned and non-notarized.
