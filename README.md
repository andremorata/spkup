# spkup

Push-to-talk speech-to-text for Windows. Hold a hotkey, speak, release — transcribed text lands in your clipboard.

Planned distribution note: once Phase 9 is implemented, GitHub Releases are intended to become the project's distribution channel.

- Global hotkey (configurable, default `Ctrl+Shift+Space`)
- Local Whisper inference via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no cloud, no API key
- Mixed Portuguese + English support (auto-detect)
- Always-on-top overlay with RECORDING / TRANSCRIBING / DONE states
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

---

## Project Docs

| File | Contents |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | Component diagram, signal flow, threading model, module responsibilities |
| [docs/02-observability.md](docs/02-observability.md) | Logging config, log levels, troubleshooting |
| [docs/03-testing.md](docs/03-testing.md) | What gets unit tests, what gets manual verification, TDD rules |
| [docs/04-delivery-workflow.md](docs/04-delivery-workflow.md) | Phase lifecycle, definition of done, phase map |
| [docs/05-ai-agent-workflow.md](docs/05-ai-agent-workflow.md) | Rules for AI agents working in this repo |

## Delivery Specs

| File | Contents |
|---|---|
| [specs/project.plan.md](specs/project.plan.md) | Full project plan: stack, assumptions, and the full delivery roadmap |
| [specs/progress.status.md](specs/progress.status.md) | Current phase status and validation evidence |
| [specs/phase1.issue.md](specs/phase1.issue.md) — [phase9](specs/phase9.issue.md) | Per-phase tasks and acceptance criteria for the currently tracked delivery phases |
