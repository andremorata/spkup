import sys
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication

from spkup.config import AppConfig
from spkup.post_processing import KEYRING_SERVICE, KEYRING_USERNAME
from spkup.settings_dialog import SettingsDialog, parse_replacements

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


@pytest.fixture
def dialog_factory(monkeypatch):
    monkeypatch.setattr("spkup.settings_dialog._detect_cuda", lambda: False)
    monkeypatch.setattr("spkup.settings_dialog.list_input_devices", lambda: [])
    monkeypatch.setattr("spkup.settings_dialog.is_downloaded", lambda model: False)
    monkeypatch.setattr("spkup.settings_dialog.save", lambda config: None)
    with patch("spkup.settings_dialog.keyring") as kr:
        kr.get_password.return_value = None
        yield lambda config: (SettingsDialog(config), kr)


def test_parse_replacements_ignores_blank_and_malformed_lines() -> None:
    text = "temple base -> Tempobase\n\nno arrow here\n -> empty\nspeak up->spkup\n"

    assert parse_replacements(text) == {"temple base": "Tempobase", "speak up": "spkup"}


def test_text_tab_saves_vocabulary_and_replacements(dialog_factory) -> None:
    dialog, _ = dialog_factory(AppConfig())
    saved: list[AppConfig] = []
    dialog.settings_saved.connect(saved.append)

    dialog._vocabulary_edit.setPlainText("Tempobase\n\n  spkup  \n")
    dialog._replacements_edit.setPlainText("temple base -> Tempobase")
    dialog._on_save()

    assert saved[0].vocabulary == ["Tempobase", "spkup"]
    assert saved[0].replacements == {"temple base": "Tempobase"}


def test_text_tab_shows_existing_replacements(dialog_factory) -> None:
    dialog, _ = dialog_factory(AppConfig(replacements={"a b": "C"}, vocabulary=["X", "Y"]))

    assert dialog._replacements_edit.toPlainText() == "a b -> C"
    assert dialog._vocabulary_edit.toPlainText() == "X\nY"
    dialog.reject()


def test_switching_provider_sets_defaults_and_privacy_note(dialog_factory) -> None:
    dialog, _ = dialog_factory(AppConfig())

    dialog._provider_combo.setCurrentIndex(dialog._provider_combo.findData("openai"))

    assert dialog._base_url_edit.text() == "https://api.openai.com/v1"
    assert dialog._llm_model_edit.text() == ""
    assert dialog._llm_model_edit.placeholderText()
    assert not dialog._api_key_edit.isHidden()
    assert not dialog._privacy_note.isHidden()

    dialog._provider_combo.setCurrentIndex(dialog._provider_combo.findData("local"))

    assert dialog._base_url_edit.text() == "http://localhost:11434/v1"
    assert dialog._llm_model_edit.text() == AppConfig().post_processing_model
    assert dialog._api_key_edit.isHidden()
    assert dialog._privacy_note.isHidden()
    dialog.reject()


def test_api_key_written_to_keyring_and_never_to_config(dialog_factory) -> None:
    dialog, kr = dialog_factory(AppConfig(post_processing_provider="openai"))
    saved: list[AppConfig] = []
    dialog.settings_saved.connect(saved.append)

    dialog._post_processing_group.setChecked(True)
    dialog._llm_model_edit.setText("gpt-4.1-mini")
    dialog._api_key_edit.setText("sk-new")
    dialog._on_save()

    kr.set_password.assert_called_once_with(KEYRING_SERVICE, KEYRING_USERNAME, "sk-new")
    assert saved[0].post_processing_enabled is True
    assert saved[0].post_processing_provider == "openai"
    assert saved[0].post_processing_model == "gpt-4.1-mini"
    assert "sk-new" not in repr(saved[0])


def test_blank_api_key_keeps_stored_key(dialog_factory) -> None:
    dialog, kr = dialog_factory(AppConfig(post_processing_provider="openai"))
    kr.get_password.return_value = "sk-old"

    dialog._on_save()

    kr.set_password.assert_not_called()


def test_keyring_read_failure_does_not_break_dialog(monkeypatch) -> None:
    monkeypatch.setattr("spkup.settings_dialog._detect_cuda", lambda: False)
    monkeypatch.setattr("spkup.settings_dialog.list_input_devices", lambda: [])
    monkeypatch.setattr("spkup.settings_dialog.is_downloaded", lambda model: False)
    with patch("spkup.settings_dialog.keyring") as kr:
        kr.get_password.side_effect = RuntimeError("no backend")
        dialog = SettingsDialog(AppConfig(post_processing_provider="openai"))

    assert dialog._api_key_edit.placeholderText()
    dialog.reject()
