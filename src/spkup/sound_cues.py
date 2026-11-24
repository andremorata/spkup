"""Short UI sound cues played through the native OS player.

macOS uses NSSound and Windows uses winsound. Both play a bundled WAV
asynchronously without opening an audio stream on the caller's thread.
The previous PortAudio path (sounddevice.play) blocked the Qt main thread for
~450 ms per cue on Bluetooth output, freezing the UI and delaying recording.
Regenerate the WAVs with scripts/make_sounds.py.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from spkup.platform_support import is_macos, is_windows

_log = logging.getLogger(__name__)

SOUNDS_DIR = Path(__file__).with_name("resources") / "sounds"
CUE_NAMES = ("start", "transcribing", "done")

# NSSound must stay referenced while it plays; reuse one instance per cue.
_ns_sounds: dict[str, object] = {}


def cue_path(name: str) -> Path:
    return SOUNDS_DIR / f"{name}.wav"


def _play_macos(name: str, blocking: bool) -> None:
    from AppKit import NSSound

    sound = _ns_sounds.get(name)
    if sound is None:
        sound = NSSound.alloc().initWithContentsOfFile_byReference_(str(cue_path(name)), True)
        if sound is None:
            raise OSError(f"could not load {cue_path(name)}")
        _ns_sounds[name] = sound
    sound.stop()  # restart cleanly if a quick repeat lands while it still plays
    sound.play()
    if blocking:
        time.sleep(sound.duration())


def _play_windows(name: str, blocking: bool) -> None:
    import winsound

    flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT
    if not blocking:
        flags |= winsound.SND_ASYNC
    winsound.PlaySound(str(cue_path(name)), flags)


def play_cue(name: str, blocking: bool = False) -> None:
    if name not in CUE_NAMES:
        _log.warning("Unknown sound cue: %s", name)
        return
    try:
        if is_macos():
            _play_macos(name, blocking)
        elif is_windows():
            _play_windows(name, blocking)
    except Exception as exc:
        _log.warning("Skipping sound cue '%s': %s", name, exc)


__all__ = ["CUE_NAMES", "cue_path", "play_cue"]
