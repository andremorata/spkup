# spkup

Push-to-talk speech-to-text for Windows. Hold a hotkey or single-click the tray icon, speak, release or click again — transcribed text lands in your clipboard.

- Global hotkey (configurable, default `Ctrl+Shift+Space`)
- Single left-click tray icon toggle for record / stop
- Local Whisper inference via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no cloud, no API key
- Mixed Portuguese + English support (auto-detect)
- Always-on-top overlay with live remaining-time feedback during capture plus RECORDING / TRANSCRIBING / DONE states
- Lives in the system tray; zero friction

**Target machine:** Windows 11, Python 3.12, RTX 4070 (8 GB VRAM)

---

## Setup

```bash
cd E:\spkup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

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
- Initial Windows release artifacts should derive from that same version, for example `spkup-X.Y.Z-windows-x64.zip`

The repository also has tagged-release automation, but the versioning contract above remains the single source of truth for release preparation.

---

## Project Docs

| File | Contents |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | Component diagram, signal flow, threading model, module responsibilities |
| [docs/02-observability.md](docs/02-observability.md) | Logging config, log levels, troubleshooting |
| [docs/03-testing.md](docs/03-testing.md) | What gets unit tests, what gets manual verification, TDD rules |
| [docs/04-delivery-workflow.md](docs/04-delivery-workflow.md) | Maintenance workflow, definition of done, historical MVP roadmap |
| [docs/05-ai-agent-workflow.md](docs/05-ai-agent-workflow.md) | Rules for AI agents working in this repo |
| [docs/06-packaging-release.md](docs/06-packaging-release.md) | Versioning contract, Windows artifact baseline, operator release workflow |

## Delivery Specs

| File | Contents |
|---|---|
| [specs/project.plan.md](specs/project.plan.md) | Full project plan: stack, assumptions, and the full delivery roadmap |
| [specs/progress.status.md](specs/progress.status.md) | Current maintenance status, historical MVP baseline, and validation evidence |
| [specs/spec-template.issue.md](specs/spec-template.issue.md) | Template for new post-MVP specs, extensions, and requirements |
| [specs/phase1.issue.md](specs/phase1.issue.md) — [phase9](specs/phase9.issue.md) | Historical MVP phase records kept for reference; do not extend with new scope |
