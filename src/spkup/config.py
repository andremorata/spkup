import dataclasses
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclasses.dataclass
class AppConfig:
    hotkey: str = "ctrl+shift+space"
    model_size: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    overlay_position: str = "bottom-right"
    max_recording_seconds: int = 120


CONFIG_DIR = Path(os.environ["APPDATA"]) / "spkup"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load() -> AppConfig:
    if not CONFIG_PATH.exists():
        save(AppConfig())
        return AppConfig()

    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    valid_keys = {field.name for field in dataclasses.fields(AppConfig)}
    filtered = {key: value for key, value in raw.items() if key in valid_keys}
    return AppConfig(**filtered)


def save(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=CONFIG_DIR,
            delete=False,
        ) as temp_file:
            temp_file.write(json.dumps(dataclasses.asdict(config), indent=2) + "\n")
            temp_path = Path(temp_file.name)

        os.replace(temp_path, CONFIG_PATH)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
