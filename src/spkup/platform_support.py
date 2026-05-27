from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Mapping

APP_NAME = "spkup"
WINDOWS_X64_TAG = "windows-x64"
MACOS_ARM64_TAG = "macos-arm64"


def _sys_platform(value: str | None = None) -> str:
    return sys.platform if value is None else value


def _machine(value: str | None = None) -> str:
    return (platform.machine() if value is None else value).lower()


def is_windows(sys_platform: str | None = None) -> bool:
    return _sys_platform(sys_platform) == "win32"


def is_macos(sys_platform: str | None = None) -> bool:
    return _sys_platform(sys_platform) == "darwin"


def is_macos_arm64(
    sys_platform: str | None = None,
    machine: str | None = None,
) -> bool:
    return is_macos(sys_platform) and _machine(machine) in {"arm64", "aarch64"}


def current_platform_tag(
    sys_platform: str | None = None,
    machine: str | None = None,
) -> str | None:
    if is_windows(sys_platform):
        return WINDOWS_X64_TAG
    if is_macos_arm64(sys_platform, machine):
        return MACOS_ARM64_TAG
    return None


def artifact_name(version: str, platform_tag: str | None = None) -> str | None:
    tag = current_platform_tag() if platform_tag is None else platform_tag
    if tag is None:
        return None
    return f"{APP_NAME}-{version}-{tag}.zip"


def bundle_root_name(version: str, platform_tag: str | None = None) -> str | None:
    tag = current_platform_tag() if platform_tag is None else platform_tag
    if tag is None:
        return None
    return f"{APP_NAME}-{version}-{tag}"


def default_device(sys_platform: str | None = None) -> str:
    return "cuda" if is_windows(sys_platform) else "cpu"


def default_compute_type(sys_platform: str | None = None) -> str:
    return "int8"


def supports_autostart(sys_platform: str | None = None) -> bool:
    return is_windows(sys_platform)


def supports_playback_mute(sys_platform: str | None = None) -> bool:
    return is_windows(sys_platform)


def supports_automatic_update_apply(sys_platform: str | None = None) -> bool:
    return is_windows(sys_platform)


def requires_cuda_packaging_validation(sys_platform: str | None = None) -> bool:
    return is_windows(sys_platform)


def _home(home: Path | str | None = None) -> Path:
    return Path.home() if home is None else Path(home)


def _env(environ: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def user_config_dir(
    sys_platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    env = _env(environ)
    if is_windows(sys_platform):
        base = env.get("APPDATA") or env.get("LOCALAPPDATA")
        return Path(base) / APP_NAME if base else _home(home) / "AppData" / "Roaming" / APP_NAME
    if is_macos(sys_platform):
        return _home(home) / "Library" / "Application Support" / APP_NAME
    return _home(home) / ".config" / APP_NAME


def user_cache_dir(
    sys_platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    env = _env(environ)
    if is_windows(sys_platform):
        base = env.get("LOCALAPPDATA") or env.get("APPDATA")
        return Path(base) / APP_NAME if base else _home(home) / "AppData" / "Local" / APP_NAME
    if is_macos(sys_platform):
        return _home(home) / "Library" / "Caches" / APP_NAME
    return _home(home) / ".cache" / APP_NAME


def user_log_dir(
    sys_platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    if is_macos(sys_platform):
        return _home(home) / "Library" / "Logs" / APP_NAME
    return user_cache_dir(sys_platform=sys_platform, environ=environ, home=home)


def model_cache_dir(
    sys_platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    return user_cache_dir(sys_platform=sys_platform, environ=environ, home=home) / "models"


def update_staging_root(
    sys_platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    return user_cache_dir(sys_platform=sys_platform, environ=environ, home=home) / "updates"
