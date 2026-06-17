import sys

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from spkup.settings_dialog import HotkeyEdit

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def _press(edit: HotkeyEdit, key: Qt.Key, modifiers: Qt.KeyboardModifier) -> None:
    edit._capturing = True
    event = QKeyEvent(QEvent.Type.KeyPress, key.value, modifiers)
    edit.keyPressEvent(event)


def test_capture_keeps_saved_hotkey_until_clicked() -> None:
    edit = HotkeyEdit("ctrl+shift+space")
    # ClickFocus keeps the field from grabbing initial focus and replacing the
    # saved value with the capture placeholder.
    assert edit.focusPolicy() == Qt.FocusPolicy.ClickFocus
    assert edit.text() == "ctrl+shift+space"


def test_macos_maps_meta_modifier_to_ctrl(monkeypatch) -> None:
    monkeypatch.setattr("spkup.settings_dialog.is_macos", lambda *a, **k: True)
    edit = HotkeyEdit("ctrl+shift+space")
    _press(edit, Qt.Key.Key_P, Qt.KeyboardModifier.MetaModifier | Qt.KeyboardModifier.ShiftModifier)
    assert edit._current == "ctrl+shift+p"


def test_non_macos_uses_control_modifier(monkeypatch) -> None:
    monkeypatch.setattr("spkup.settings_dialog.is_macos", lambda *a, **k: False)
    edit = HotkeyEdit("ctrl+shift+space")
    _press(edit, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert edit._current == "ctrl+shift+p"
