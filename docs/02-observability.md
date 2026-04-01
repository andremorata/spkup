# spkup — Observability

> Logging and diagnostic strategy for a single-user local desktop application.
> There are no servers, no cloud metrics, no alerting pipelines. All observability is local.

---

## 1. Approach

spkup is a personal tool. Observability means: when something goes wrong, the user (who is also the developer) can find out what happened and why by reading a log file.

No APM, no distributed tracing, no metrics dashboards.

---

## 2. Log File

| Property | Value |
| --- | --- |
| Location | `%LOCALAPPDATA%\spkup\spkup.log` |
| Rotation | `RotatingFileHandler`, max 5 MB per file, 3 backups |
| Format | `%(asctime)s %(levelname)-8s %(name)s — %(message)s` |
| Handlers | File (rotating) + stderr |
| Configured in | `src/spkup/logging_setup.py`, called at top of `__main__.py` |

---

## 3. Log Levels

| Level | Used for |
| --- | --- |
| `DEBUG` | Hotkey events, audio chunk counts, model load timing |
| `INFO` | App start/stop, recording started/stopped, transcription result, settings saved |
| `WARNING` | CUDA OOM (before CPU fallback), model not found, unexpected but recoverable states |
| `ERROR` | Mic not found, transcription failure, config write failure |
| `CRITICAL` | Unhandled exception in main thread (caught by top-level except) |

---

## 4. What Gets Logged

| Event | Level | Module |
| --- | --- | --- |
| App started | INFO | `__main__` |
| Config loaded / created | INFO | `config` |
| Hotkey listener started | INFO | `hotkey` |
| Recording started | DEBUG | `hotkey` |
| Recording stopped, array shape | DEBUG | `recorder` |
| Transcription started | INFO | `transcriber` |
| Transcription finished, text preview | INFO | `transcriber` |
| Model loaded (first use), elapsed | INFO | `transcriber` |
| CUDA OOM, falling back to CPU | WARNING | `transcriber` |
| Mic error | ERROR | `recorder` |
| Settings saved | INFO | `settings_dialog` |
| Model download progress | DEBUG | `model_manager` |
| App quit | INFO | `app` |

---

## 5. Error Visibility

Runtime errors surface to the user in two ways:

1. **Tray balloon notification** — short human-readable message (e.g. "Microphone not found")
2. **Log file** — full exception traceback for diagnosis

The overlay transitions to `HIDDEN` on any error so it does not get stuck in TRANSCRIBING state.

---

## 6. Troubleshooting

To diagnose an issue, open:

```
%LOCALAPPDATA%\spkup\spkup.log
```

Useful filters:
- `ERROR` or `WARNING` lines for failures
- `transcriber` logger for inference problems
- `hotkey` logger for missed key events
