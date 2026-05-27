from pathlib import Path

from spkup import platform_support as ps


def test_platform_tag_selects_windows_x64() -> None:
    assert ps.current_platform_tag("win32", "AMD64") == "windows-x64"


def test_platform_tag_selects_macos_arm64() -> None:
    assert ps.current_platform_tag("darwin", "arm64") == "macos-arm64"


def test_platform_tag_rejects_unsupported_macos_arch() -> None:
    assert ps.current_platform_tag("darwin", "x86_64") is None


def test_windows_paths_preserve_existing_appdata_contract() -> None:
    env = {"APPDATA": r"C:\Users\andre\AppData\Roaming", "LOCALAPPDATA": r"C:\Users\andre\AppData\Local"}

    assert ps.user_config_dir("win32", env) == Path(env["APPDATA"]) / "spkup"
    assert ps.model_cache_dir("win32", env) == Path(env["LOCALAPPDATA"]) / "spkup" / "models"
    assert ps.update_staging_root("win32", env) == Path(env["LOCALAPPDATA"]) / "spkup" / "updates"


def test_macos_paths_use_library_locations(tmp_path) -> None:
    assert ps.user_config_dir("darwin", home=tmp_path) == (
        tmp_path / "Library" / "Application Support" / "spkup"
    )
    assert ps.model_cache_dir("darwin", home=tmp_path) == (
        tmp_path / "Library" / "Caches" / "spkup" / "models"
    )
    assert ps.user_log_dir("darwin", home=tmp_path) == (
        tmp_path / "Library" / "Logs" / "spkup"
    )


def test_platform_capabilities_are_explicit() -> None:
    assert ps.supports_autostart("win32") is True
    assert ps.supports_autostart("darwin") is False
    assert ps.supports_playback_mute("win32") is True
    assert ps.supports_playback_mute("darwin") is False
    assert ps.requires_cuda_packaging_validation("win32") is True
    assert ps.requires_cuda_packaging_validation("darwin") is False


def test_ui_font_family_uses_native_default_off_windows() -> None:
    assert ps.ui_font_family("win32") == "Segoe UI"
    assert ps.ui_font_family("darwin") == ""
    assert ps.ui_font_family("linux") == ""
