import sys

from PyQt6.QtWidgets import QApplication

from spkup.config import AppConfig
from spkup.settings_dialog import SettingsDialog

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def test_settings_dialog_updates_startup_check_toggle(monkeypatch) -> None:
    monkeypatch.setattr("spkup.settings_dialog._detect_cuda", lambda: False)
    monkeypatch.setattr("spkup.settings_dialog.list_input_devices", lambda: [])
    monkeypatch.setattr("spkup.settings_dialog.is_downloaded", lambda model: False)

    dialog = SettingsDialog(AppConfig(check_updates_on_startup=True))

    dialog._updates_checkbox.setChecked(False)

    assert dialog._config.check_updates_on_startup is False
    dialog.reject()


def test_settings_dialog_forces_cpu_when_cuda_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("spkup.settings_dialog._detect_cuda", lambda: False)
    monkeypatch.setattr("spkup.settings_dialog.list_input_devices", lambda: [])
    monkeypatch.setattr("spkup.settings_dialog.is_downloaded", lambda model: False)

    dialog = SettingsDialog(AppConfig(device="cuda"))

    assert dialog._config.device == "cpu"
    assert dialog._device_combo.currentText() == "cpu"
    dialog.reject()
