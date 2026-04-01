import json

from spkup.config import AppConfig, load, save


def test_load_defaults(tmp_path, monkeypatch):
    """When no config file exists, load() creates it with defaults and returns defaults."""
    cfg_dir = tmp_path / "spkup"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    result = load()

    assert result == AppConfig()
    assert cfg_path.exists()


def test_round_trip(tmp_path, monkeypatch):
    """save() then load() returns an identical config."""
    cfg_dir = tmp_path / "spkup"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    cfg = AppConfig(hotkey="f9", max_recording_seconds=30)
    save(cfg)
    loaded = load()

    assert loaded == cfg


def test_unknown_keys_ignored(tmp_path, monkeypatch):
    """Extra keys in the JSON file are silently ignored."""
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


def test_save_creates_directory(tmp_path, monkeypatch):
    """save() creates the config directory if it doesn't exist."""
    cfg_dir = tmp_path / "nested" / "dir"
    cfg_path = cfg_dir / "config.json"
    monkeypatch.setattr("spkup.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("spkup.config.CONFIG_PATH", cfg_path)

    save(AppConfig())

    assert cfg_path.exists()
