# Changelog

All notable user-visible changes. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions match the `vX.Y.Z` git tags
and the source `__version__`.

## [Unreleased]

### Changed
- Replaced the scaffold-era `specs/` roadmap machinery and the generic project-scaffold
  agent instructions with project-specific docs. Work is now tracked in GitHub Issues,
  decisions in `docs/adr/`, and history in this changelog. Documentation moved to
  flat names under `docs/` (`architecture`, `testing`, `observability`, `packaging-release`).

## [0.2.6] — 2026-05
### Added
- macOS ARM64 / Apple Silicon support: platform path and capability abstractions,
  CPU/int8 faster-whisper defaults, a dedicated `spkup-macos.spec` bundle, platform-aware
  update-asset selection, and macOS CI/release/nightly packaging paths. Windows-only
  features (autostart, playback mute, automatic update apply) are gated off on macOS.

## [0.2.5] — 2026-05
### Added
- Settings dialog title now shows the running version.

## [0.2.4] — 2026-05
### Added
- Opt-out startup update check against GitHub Releases with confirm-before-apply;
  Windows frozen builds stage and apply updates via a helper process.
- Live remaining-time countdown in the recording overlay with low-time urgency styling.
### Changed
- Nightly automation now publishes normal GitHub Releases instead of pre-releases.

## [0.2.3] — 2026-05
### Added
- Configurable idle unload of the transcription model to release memory when idle.

## [0.2.2] — 2026-04
### Added
- Model management in Settings: download busy indicator, approximate size hints, and delete.
### Fixed
- Model download crash in the frozen windowed build (missing stdout/stderr streams).

## [0.2.1] — 2026-04
### Added
- Manual cancellation of an in-progress transcription via the hotkey or a tray click.

## [0.2.0] — 2026-04
### Added
- Microphone input selection (tray submenu + Settings) and an empty-transcription warning.
- Recent transcription history (last 5 per session) with per-entry copy/delete.
- Optional playback muting during capture (Windows), restored on stop/error/quit.
- Audio start/transcribing/done cues.
- Transcription resilience: watchdog timeout, automatic CUDA→CPU fallback, and manual retry.
- Tray single-left-click recording toggle with redundant-trigger suppression.

## [0.1.x] — 2026-04
### Added
- Windows packaging (PyInstaller), GitHub Actions CI, tagged-release automation, and the
  `X.Y.Z` ↔ `vX.Y.Z` version contract.
### Fixed
- Bundle the NVIDIA CUDA/cuDNN runtime DLLs so release builds use the GPU instead of
  silently falling back to CPU.

## [0.1.0] — 2026-04
### Added
- Initial release: global push-to-talk hotkey (hold-to-record and quick-tap toggle),
  local faster-whisper transcription with PT+EN auto-detect, always-on-top recording
  overlay, clipboard output, settings dialog, system-tray operation, file logging,
  and Windows autostart.
