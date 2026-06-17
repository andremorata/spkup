# spkup

Push-to-talk speech-to-text for Windows and Apple Silicon macOS. Hold a hotkey or single-click the tray/menu-bar icon, speak, release or click again — transcribed text lands in your clipboard.

- Global hotkey (configurable, default `Ctrl+Shift+Space`)
- Single left-click tray icon toggle for record / stop (on macOS the context menu opens with a right-click)
- Local Whisper inference via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no cloud, no API key
- Mixed Portuguese + English support (auto-detect)
- Always-on-top overlay with live remaining-time feedback during capture plus RECORDING / TRANSCRIBING / DONE states
- Lives in the system tray; zero friction
- Startup update checks against GitHub Releases, enabled by default and confirm-before-apply

**Supported platforms:** Windows 11 x64 and macOS ARM64 / Apple Silicon, Python 3.12.

Windows remains the GPU-accelerated production baseline with NVIDIA CUDA/cuDNN runtime packaging. macOS support is CPU-oriented in the first ARM64 slice.

---

## Setup

Windows:

```bash
cd path\to\spkup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On Windows, `requirements.txt` includes NVIDIA CUDA/cuDNN runtime wheels so
local PyInstaller bundles match GPU-capable GitHub release artifacts.

macOS ARM64:

```bash
cd /path/to/spkup
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,build]"
```

macOS requires Microphone permission for recording and **Input Monitoring** permission for global hotkey capture. On first launch spkup detects a missing Input Monitoring grant, opens System Settings directly to the correct pane, and adds a "Grant Input Monitoring permission…" entry to the menu-bar menu that opens the right settings pane. Grant it under **System Settings → Privacy & Security → Privacy → Input Monitoring**, then restart spkup for the hotkey to start firing. Until then you can still record by left-clicking the menu-bar icon. The first macOS package is unsigned and non-notarized, so Gatekeeper may require manual approval — and because the grant is keyed to the app's signature, an unsigned build can lose the permission across updates.

Run:

```bash
python -m spkup
# or
run.bat
```

From the repository root, `python -m spkup` now resolves the current checkout's
`src\spkup` code even if you also have an editable install from another clone or
worktree.

---

## Release Versioning

The project uses one release version contract:

- Source version lives in `src/spkup/__init__.py` as `__version__ = "X.Y.Z"`
- Build metadata reads that version through Hatchling dynamic metadata in `pyproject.toml`
- Git release tags must be `vX.Y.Z` for the same source version
- Release artifacts derive from that same version:
  - `spkup-X.Y.Z-windows-x64.zip`
  - `spkup-X.Y.Z-macos-arm64.zip`

The repository also has tagged-release automation, but the versioning contract above remains the single source of truth for release preparation.

Packaged builds check GitHub Releases on startup by default. Windows builds can download and apply matching Windows ZIP updates after confirmation. macOS builds detect matching macOS ARM64 releases but do not auto-apply them until a signed/notarized update strategy exists; users update manually from the release asset.

---

## Project Docs

| File | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Component diagram, signal flow, threading model, module responsibilities |
| [docs/observability.md](docs/observability.md) | Logging config, log levels, troubleshooting |
| [docs/testing.md](docs/testing.md) | What gets unit tests, what gets manual verification, TDD rules |
| [docs/packaging-release.md](docs/packaging-release.md) | Versioning contract, platform artifact baselines, operator release workflow |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [AGENTS.md](AGENTS.md) | Contributor & AI-agent guide |
| [CHANGELOG.md](CHANGELOG.md) | User-visible change history |

Work is tracked in [GitHub Issues](https://github.com/andremorata/spkup/issues).
