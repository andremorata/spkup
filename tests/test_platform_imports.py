import importlib


def test_platform_sensitive_modules_import() -> None:
    for module_name in [
        "spkup.config",
        "spkup.logging_setup",
        "spkup.model_manager",
        "spkup.autostart",
        "spkup.update_checker",
        "spkup.updater",
        "spkup.playback_mute",
    ]:
        importlib.import_module(module_name)
