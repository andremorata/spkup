from __future__ import annotations

import logging
import types
import wave
from unittest.mock import MagicMock, patch

import spkup.sound_cues as sound_cues


def test_bundled_cues_are_short_quiet_wavs() -> None:
    for name in sound_cues.CUE_NAMES:
        with wave.open(str(sound_cues.cue_path(name))) as w:
            duration = w.getnframes() / w.getframerate()
            frames = w.readframes(w.getnframes())
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        assert 0.1 <= duration <= 0.8, name
        peak = max(abs(int.from_bytes(frames[i:i + 2], "little", signed=True))
                   for i in range(0, len(frames), 2))
        assert peak < 0.5 * 32767, name  # stays well under full scale


def test_play_cue_logs_warning_for_unknown_name(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        sound_cues.play_cue("missing")
    assert "Unknown sound cue: missing" in caplog.text


def test_windows_plays_file_async_unless_blocking(monkeypatch) -> None:
    fake = types.SimpleNamespace(SND_FILENAME=1, SND_NODEFAULT=2, SND_ASYNC=4, PlaySound=MagicMock())
    monkeypatch.setattr(sound_cues, "is_macos", lambda: False)
    monkeypatch.setattr(sound_cues, "is_windows", lambda: True)
    with patch.dict("sys.modules", {"winsound": fake}):
        sound_cues.play_cue("start")
        sound_cues.play_cue("done", blocking=True)
    assert fake.PlaySound.call_args_list[0].args == (str(sound_cues.cue_path("start")), 1 | 2 | 4)
    assert fake.PlaySound.call_args_list[1].args == (str(sound_cues.cue_path("done")), 1 | 2)


def test_macos_reuses_one_nssound_per_cue(monkeypatch) -> None:
    sound = MagicMock()
    ns_sound = MagicMock()
    ns_sound.alloc.return_value.initWithContentsOfFile_byReference_.return_value = sound
    monkeypatch.setattr(sound_cues, "is_macos", lambda: True)
    monkeypatch.setattr(sound_cues, "_ns_sounds", {})
    with patch.dict("sys.modules", {"AppKit": types.SimpleNamespace(NSSound=ns_sound)}):
        sound_cues.play_cue("start")
        sound_cues.play_cue("start")
    assert ns_sound.alloc.call_count == 1
    assert sound.play.call_count == 2


def test_play_cue_swallows_player_errors(monkeypatch, caplog) -> None:
    monkeypatch.setattr(sound_cues, "is_macos", lambda: True)
    monkeypatch.setattr(sound_cues, "_play_macos", MagicMock(side_effect=OSError("no device")))
    with caplog.at_level(logging.WARNING):
        sound_cues.play_cue("done")
    assert "Skipping sound cue 'done': no device" in caplog.text
