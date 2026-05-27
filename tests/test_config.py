import json

from spkup.config import AppConfig, default_config, load, save


def test_load_defaults(tmp_path, monkeypatch):
    """When no config file exists, load() creates it with defaults and returns defaults."""
    cfg_dir = tmp_path / "spkup"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    result = load()

    assert result == default_config()
    assert result.mute_playback_while_recording is False
    assert result.check_updates_on_startup is True
    assert cfg_path.exists()


def test_round_trip(tmp_path, monkeypatch):
    """save() then load() returns an identical config."""
    cfg_dir = tmp_path / "spkup"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    cfg = AppConfig(
        hotkey="f9",
        max_recording_seconds=30,
        mute_playback_while_recording=True,
        check_updates_on_startup=False,
    )
    save(cfg)
    loaded = load()

    assert loaded == cfg


def test_unknown_keys_ignored(tmp_path, monkeypatch):
    """Extra keys are ignored and missing keys fall back to dataclass defaults."""
    cfg_dir = tmp_path / "spkup"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    data = {"hotkey": "f9", "bogus_key": 42}
    cfg_path.write_text(json.dumps(data), encoding="utf-8")

    result = load()

    assert result.hotkey == "f9"
    assert result.model_size == "large-v3"  # default preserved
    assert result.mute_playback_while_recording is False
    assert result.check_updates_on_startup is True


def test_save_creates_directory(tmp_path, monkeypatch):
    """save() creates the config directory if it doesn't exist."""
    cfg_dir = tmp_path / "nested" / "dir"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    save(AppConfig())

    assert cfg_path.exists()


def test_default_transcription_timeout_seconds() -> None:
    """AppConfig() has transcription_timeout_seconds == 300 by default."""
    assert AppConfig().transcription_timeout_seconds == 300


def test_load_returns_default_timeout_when_key_missing(tmp_path, monkeypatch) -> None:
    """load() returns 300 when the config file does not contain the key."""
    cfg_dir = tmp_path / "spkup"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    data = {"hotkey": "f9", "model_size": "base"}
    cfg_path.write_text(json.dumps(data), encoding="utf-8")

    result = load()

    assert result.transcription_timeout_seconds == 300


def test_input_device_defaults_to_none() -> None:
    """AppConfig() has input_device == None (system default) by default."""
    assert AppConfig().input_device is None


def test_input_device_round_trips(tmp_path, monkeypatch) -> None:
    """A stored input_device spec survives save() → load()."""
    cfg_dir = tmp_path / "spkup"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    spec = {"name": "USB Headset Mic", "hostapi": "Windows WASAPI"}
    cfg = AppConfig(input_device=spec)
    save(cfg)
    loaded = load()

    assert loaded.input_device == spec


def test_load_missing_input_device_falls_back_to_none(tmp_path, monkeypatch) -> None:
    """Older config.json files without input_device load cleanly as None."""
    cfg_dir = tmp_path / "spkup"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    cfg_path.write_text(json.dumps({"hotkey": "f9"}), encoding="utf-8")

    result = load()

    assert result.input_device is None


def test_check_updates_on_startup_defaults_to_true() -> None:
    assert AppConfig().check_updates_on_startup is True


def test_default_config_uses_platform_safe_device(monkeypatch) -> None:
    monkeypatch.setattr("spkup.platform_support.sys.platform", "darwin")

    cfg = default_config()

    assert cfg.device == "cpu"
    assert cfg.compute_type == "int8"


def test_load_missing_device_uses_platform_default(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / "spkup"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)
    monkeypatch.setattr("spkup.platform_support.sys.platform", "darwin")

    cfg_path.write_text(json.dumps({"hotkey": "f9"}), encoding="utf-8")

    result = load()

    assert result.device == "cpu"
    assert result.compute_type == "int8"


def test_load_missing_update_check_falls_back_to_enabled(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / "spkup"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    cfg_path.write_text(json.dumps({"hotkey": "f9"}), encoding="utf-8")

    result = load()

    assert result.check_updates_on_startup is True
