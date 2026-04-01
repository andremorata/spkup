from __future__ import annotations

import dataclasses

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spkup.config import AppConfig, save
from spkup.hotkey import parse_hotkey
from spkup.model_manager import _ModelDownloadWorker, is_downloaded


def _detect_cuda() -> bool:
    """Return True if CUDA is available via ctranslate2."""
    try:
        import ctranslate2

        return bool(ctranslate2.get_supported_compute_types("cuda"))
    except Exception:
        return False


def _qt_key_to_str(key: int) -> str | None:
    """Convert a Qt key code to a pynput-compatible name string."""
    _SPECIAL: dict[int, str] = {
        Qt.Key.Key_Space.value: "space",
        Qt.Key.Key_Return.value: "enter",
        Qt.Key.Key_Enter.value: "enter",
        Qt.Key.Key_Backspace.value: "backspace",
        Qt.Key.Key_Tab.value: "tab",
        Qt.Key.Key_Escape.value: "escape",
        Qt.Key.Key_F1.value: "f1",
        Qt.Key.Key_F2.value: "f2",
        Qt.Key.Key_F3.value: "f3",
        Qt.Key.Key_F4.value: "f4",
        Qt.Key.Key_F5.value: "f5",
        Qt.Key.Key_F6.value: "f6",
        Qt.Key.Key_F7.value: "f7",
        Qt.Key.Key_F8.value: "f8",
        Qt.Key.Key_F9.value: "f9",
        Qt.Key.Key_F10.value: "f10",
        Qt.Key.Key_F11.value: "f11",
        Qt.Key.Key_F12.value: "f12",
    }
    if key in _SPECIAL:
        return _SPECIAL[key]
    # Printable ASCII: letters (0x41–0x5A) and digits (0x30–0x39)
    if 0x20 <= key <= 0x7E:
        return chr(key).lower()
    return None


class HotkeyEdit(QLineEdit):
    """Read-only line edit that captures a key combination on focus."""

    hotkey_changed = pyqtSignal(str)

    def __init__(self, initial: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self._current = initial
        self.setText(initial)
        self._capturing = False

    def focusInEvent(self, event) -> None:
        self._capturing = True
        self.setText("Press hotkey…")
        self.setStyleSheet("")
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._capturing = False
        self.setText(self._current)
        self.setStyleSheet("")
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        _MODIFIER_KEYS = {
            Qt.Key.Key_Control.value,
            Qt.Key.Key_Shift.value,
            Qt.Key.Key_Alt.value,
            Qt.Key.Key_Meta.value,
            Qt.Key.Key_AltGr.value,
        }
        if key in _MODIFIER_KEYS:
            return  # wait for the trigger key

        mods = event.modifiers()
        parts: list[str] = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")

        trigger = _qt_key_to_str(key)
        if trigger is None:
            return

        parts.append(trigger)
        combo = "+".join(parts)

        try:
            parse_hotkey(combo)
            self._current = combo
            self.setText(combo)
            self.setStyleSheet("border: 1.5px solid #43A047;")
            self.hotkey_changed.emit(combo)
        except ValueError:
            self.setText(f"{combo}  ✗ invalid")
            self.setStyleSheet("border: 1.5px solid #E53935;")


_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]


class SettingsDialog(QDialog):
    """Settings dialog for hotkey, model, device, and overlay position."""

    settings_saved = pyqtSignal(object)  # AppConfig

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("spkup — Settings")
        self.setModal(True)
        self.setMinimumWidth(440)

        # Work on a copy so Cancel discards all changes
        self._config = dataclasses.replace(config)
        self._download_worker: _ModelDownloadWorker | None = None
        self._progress_dlg: QProgressDialog | None = None

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # ── Hotkey ──────────────────────────────────────────────────────────
        self._hotkey_edit = HotkeyEdit(config.hotkey)
        self._hotkey_edit.hotkey_changed.connect(
            lambda v: setattr(self._config, "hotkey", v)
        )
        main_layout.addWidget(QLabel("Hotkey"))
        main_layout.addWidget(self._hotkey_edit)

        # ── Model ────────────────────────────────────────────────────────────
        main_layout.addWidget(QLabel("Model size"))
        model_row = QWidget()
        model_row_layout = QHBoxLayout(model_row)
        model_row_layout.setContentsMargins(0, 0, 0, 0)

        self._model_combo = QComboBox()
        for m in _MODELS:
            badge = "✓" if is_downloaded(m) else "↓"
            self._model_combo.addItem(f"{badge}  {m}", m)
        idx = _MODELS.index(config.model_size) if config.model_size in _MODELS else 0
        self._model_combo.setCurrentIndex(idx)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

        self._download_btn = QPushButton("Download")
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.setVisible(not is_downloaded(config.model_size))

        model_row_layout.addWidget(self._model_combo, 1)
        model_row_layout.addWidget(self._download_btn)
        main_layout.addWidget(model_row)

        # ── Device ───────────────────────────────────────────────────────────
        main_layout.addWidget(QLabel("Device"))
        self._device_combo = QComboBox()
        self._device_combo.addItems(["cuda", "cpu"])
        has_cuda = _detect_cuda()
        if not has_cuda:
            self._device_combo.model().item(0).setEnabled(False)
            self._device_combo.setCurrentText("cpu")
        else:
            self._device_combo.setCurrentText(config.device)
        self._device_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "device", v)
        )
        main_layout.addWidget(self._device_combo)

        # ── Compute type ─────────────────────────────────────────────────────
        main_layout.addWidget(QLabel("Compute type"))
        self._compute_combo = QComboBox()
        self._compute_combo.addItems(["float16", "int8", "float32"])
        self._compute_combo.setCurrentText(config.compute_type)
        self._compute_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "compute_type", v)
        )
        main_layout.addWidget(self._compute_combo)

        # ── Overlay position ─────────────────────────────────────────────────
        main_layout.addWidget(QLabel("Overlay position"))
        self._overlay_combo = QComboBox()
        self._overlay_combo.addItems(
            ["bottom-right", "bottom-center", "bottom-left",
             "top-right", "top-center", "top-left"]
        )
        self._overlay_combo.setCurrentText(config.overlay_position)
        self._overlay_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "overlay_position", v)
        )
        main_layout.addWidget(self._overlay_combo)

        # ── Buttons ───────────────────────────────────────────────────────────
        main_layout.addSpacing(8)
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addWidget(btn_row)

    # ---------- Slots --------------------------------------------------------

    def _on_model_changed(self, index: int) -> None:
        model_size = self._model_combo.currentData()
        self._config.model_size = model_size
        self._download_btn.setVisible(not is_downloaded(model_size))

    def _on_download(self) -> None:
        model_size = self._model_combo.currentData()

        self._progress_dlg = QProgressDialog(
            f"Downloading {model_size}…", "Cancel", 0, 100, self
        )
        self._progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dlg.setValue(0)

        self._download_worker = _ModelDownloadWorker(model_size)
        self._download_worker.progress.connect(self._progress_dlg.setValue)
        self._download_worker.finished.connect(self._on_download_done)
        self._download_worker.error.connect(self._on_download_error)
        self._progress_dlg.canceled.connect(self._download_worker.terminate)
        self._download_worker.start()
        self._progress_dlg.exec()

    def _on_download_done(self) -> None:
        if self._progress_dlg is not None:
            self._progress_dlg.setValue(100)
            self._progress_dlg.close()
        idx = self._model_combo.currentIndex()
        model_size = self._model_combo.currentData()
        self._model_combo.setItemText(idx, f"✓  {model_size}")
        self._download_btn.setVisible(False)

    def _on_download_error(self, msg: str) -> None:
        if self._progress_dlg is not None:
            self._progress_dlg.close()
        QMessageBox.critical(self, "Download failed", msg)

    def _on_save(self) -> None:
        save(self._config)
        self.settings_saved.emit(self._config)
        self.accept()
