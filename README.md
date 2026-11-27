# spkup

Push-to-talk speech-to-text for Windows and Apple Silicon macOS. Hold a hotkey or single-click the tray/menu-bar icon, speak, release or click again — transcribed text lands in your clipboard.

- Global hotkey (configurable, default `Ctrl+Shift+Space`)
- Single left-click tray icon toggle for record / stop (on macOS the context menu opens with a right-click)
- Local Whisper inference: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) on Windows, [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on the Apple Silicon GPU. No cloud, no API key
- Mixed Portuguese + English support (auto-detect)
- Custom vocabulary and whole-word replacements for names Whisper gets wrong
- Optional LLM clean-up of the transcript, local (Ollama, LM Studio) or OpenAI
- Minimal always-on-top overlay with a live waveform that follows your voice, plus transcribing / copied states
- Lives in the system tray; zero friction
- Startup update checks against GitHub Releases, enabled by default and confirm-before-apply

**Supported platforms:** Windows 11 x64 and macOS ARM64 / Apple Silicon, Python 3.12.

Windows runs on NVIDIA GPUs with bundled CUDA/cuDNN. Apple Silicon runs on the Mac GPU through MLX and defaults to the `large-v3-turbo` model.

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

macOS requires Microphone permission for recording and **Input Monitoring** permission for global hotkey capture. On first launch spkup detects a missing Input Monitoring grant, shows the native macOS prompt (which also adds spkup to the Input Monitoring list), and adds a "Grant Input Monitoring permission…" entry to the menu-bar menu that opens the right settings pane. Grant it under **System Settings → Privacy & Security → Privacy → Input Monitoring**, then restart spkup for the hotkey to start firing. Until then you can still record by left-clicking the menu-bar icon. When running from source (`python -m spkup`), macOS checks the grant of the terminal app that launched it, not Python. The first macOS package is unsigned and non-notarized, so Gatekeeper may require manual approval — and because the grant is keyed to the app's signature, an unsigned build can lose the permission across updates.

Run:

```bash
python -m spkup
# or
run.bat
```

Build and install the packaged app from your checkout:

```bash
scripts/build-macos.sh                                            # macOS → /Applications/spkup.app
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1  # Windows → %LOCALAPPDATA%\Programs\spkup
```

Both scripts create `.venv` if needed, build with PyInstaller, quit a running spkup, and replace
the installed copy. Set `SPKUP_INSTALL_DIR` to install somewhere else. The Windows script also
validates the bundled CUDA DLLs and adds a Start Menu shortcut.

From the repository root, `python -m spkup` now resolves the current checkout's
`src\spkup` code even if you also have an editable install from another clone or
worktree.

---

## Vocabulary, replacements and LLM post-processing

Open **Settings → Text**.

- **Vocabulary**: one term per line (`Tempobase`, `spkup`). Whisper gets them as a hint, so it leans toward these spellings. It is not a guarantee. Only the first 300 characters of the list reach Whisper.
- **Replacements**: one `from -> to` rule per line (`temple base -> Tempobase`). They ignore case, match whole words only, and run last.
- **Post-process with an LLM** (off by default): sends the transcript to a chat model that fixes errors, punctuation and casing, keeps the language, and follows your instructions. If the call fails or takes more than 20 s, the raw text goes to the clipboard and a notification shows the reason.
  - **Thinking / reasoning effort**: sent as `reasoning_effort`. **Off** is the default and the fastest: `gemma4:e4b` runs about 5x faster without thinking. Not every model accepts this field. If yours rejects it, the notification shows the server's error; pick **Model default** to send nothing.
  - **Local**: any OpenAI-compatible server. With [Ollama](https://ollama.com), run `ollama pull gemma4:e4b` and keep the default base URL `http://localhost:11434/v1`. Nothing leaves your machine.
  - **OpenAI**: base URL `https://api.openai.com/v1`, your model and API key. **The transcribed text leaves your machine.** The key is stored in the macOS Keychain or the Windows Credential Manager, never in `config.json` or the logs. Leave the field blank to keep the stored key.

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
