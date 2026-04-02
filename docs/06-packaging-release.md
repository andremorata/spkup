# spkup — Packaging and Release Runbook

> Phase 9 release/versioning contract baseline. This file defines the version source of truth, the initial Windows artifact shape, and the operator workflow to prepare and cut a release before automation exists.

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
- Release artifact: `spkup-0.1.0-windows-x64.zip`

Rules:

1. Do not set a release version anywhere else in the repository metadata.
2. Do not create a release tag that does not match `src/spkup/__init__.py`.
3. Do not rename release artifacts by hand to a different version string.

---

## 2. Initial Windows Artifact Baseline

The first supported Windows release artifact is intentionally narrow and practical:

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
- The artifact supports the core user flow: tray startup, hotkey capture, recording, transcription, overlay feedback, and clipboard output

This baseline does not yet promise:

- Code signing
- Installer UX
- Auto-update support
- Cross-platform artifacts

---

## 3. Release Preparation Checklist

Before cutting `vX.Y.Z`:

1. Confirm the working tree is ready for release and Phase 9 scope changes are intentional.
2. Update `src/spkup/__init__.py` so `__version__` is the intended `X.Y.Z` release.
3. Run local automated validation:

```bash
cd e:\spkup
.venv\Scripts\activate
pytest
```

4. Run the local manual smoke checks required for the current release candidate on Windows:

- App starts successfully
- Tray icon appears and quit still works
- Hotkey starts and stops capture correctly
- A spoken sample produces transcription output
- Overlay state changes remain correct
- Clipboard receives the transcription result

5. Verify the release version contract is still aligned:

- `src/spkup/__init__.py` contains `X.Y.Z`
- Intended Git tag is `vX.Y.Z`
- Intended artifact names use `X.Y.Z`

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
5. The GitHub Actions workflow in `.github/workflows/release.yml` builds the Windows artifact and publishes `spkup-X.Y.Z-windows-x64.zip` to the matching GitHub Release.

The local validation and version-alignment checks above still happen before tagging. The release workflow automates packaging and upload after the matching tag is pushed; it does not change the version contract.

---

## 5. Future Automation Boundary

Later Phase 9 implementation work should preserve this contract rather than replace it:

- Packaging configuration should derive artifact names from `src/spkup.__version__`
- CI should validate tests and packaging against the same version source
- Release automation should trigger only from `vX.Y.Z` tags
- GitHub Release names and uploaded artifacts should use the same `X.Y.Z`

If a future workflow needs additional metadata, add it around this contract instead of introducing a second version source.
