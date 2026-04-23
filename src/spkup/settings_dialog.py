from __future__ import annotations

import dataclasses
from typing import cast

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFocusEvent, QFont, QKeyEvent, QPaintEvent, QPainter, QStandardItemModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from spkup.audio_devices import list_input_devices, spec_from_device
from spkup.config import AppConfig, save
from spkup.hotkey import parse_hotkey
from spkup.model_manager import (
    _ModelDownloadWorker,
    delete_model,
    format_model_size,
    is_downloaded,
)
from spkup.overlay import OverlayState, _STATE_COLORS


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

    def focusInEvent(self, a0: QFocusEvent | None) -> None:
        self._capturing = True
        self.setText("Press hotkey…")
        self.setStyleSheet("")
        super().focusInEvent(a0)

    def focusOutEvent(self, a0: QFocusEvent | None) -> None:
        self._capturing = False
        self.setText(self._current)
        self.setStyleSheet("")
        super().focusOutEvent(a0)

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            return

        if not self._capturing:
            super().keyPressEvent(a0)
            return

        key = a0.key()
        _MODIFIER_KEYS = {
            Qt.Key.Key_Control.value,
            Qt.Key.Key_Shift.value,
            Qt.Key.Key_Alt.value,
            Qt.Key.Key_Meta.value,
            Qt.Key.Key_AltGr.value,
        }
        if key in _MODIFIER_KEYS:
            return  # wait for the trigger key

        mods = a0.modifiers()
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

_PILL_W, _PILL_H = 160, 44
_CORNER_RADIUS = 6
_ICON_ZONE = 36

_ANIM_STATE_ORDER = [
    OverlayState.RECORDING,
    OverlayState.TRANSCRIBING,
    OverlayState.DONE,
    OverlayState.ERROR,
]
_ANIM_CONFIG_FIELD: dict[OverlayState, str] = {
    OverlayState.RECORDING: "recording_animation",
    OverlayState.TRANSCRIBING: "transcribing_animation",
    OverlayState.DONE: "done_animation",
    OverlayState.ERROR: "error_animation",
}
_STATE_LABELS_UI: dict[OverlayState, str] = {
    OverlayState.RECORDING: "Recording",
    OverlayState.TRANSCRIBING: "Transcribing",
    OverlayState.DONE: "Done",
    OverlayState.ERROR: "Error",
}


class AnimationPreviewWidget(QWidget):
    """Small 160×44 mini-pill that previews an animation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_PILL_W, _PILL_H)
        self._state: OverlayState = OverlayState.RECORDING
        self._animation: object | None = None
        self._label = "Capturing"
        self._color_hex = _STATE_COLORS[OverlayState.RECORDING]

    def preview(self, state: OverlayState, key: str) -> None:
        """Start previewing animation *key* for *state*."""
        from spkup.animations import get_animation
        from spkup.overlay import _STATE_LABELS

        # Cleanup previous
        if self._animation is not None:
            self._animation.cleanup()  # type: ignore[attr-defined]
            self._animation = None

        self._state = state
        self._color_hex = _STATE_COLORS.get(state, "#999999")
        self._label = _STATE_LABELS.get(state, "")
        self._animation = get_animation(state, key)
        self._animation.start(self)  # type: ignore[attr-defined]
        self.update()

    def stop_preview(self) -> None:
        if self._animation is not None:
            self._animation.cleanup()  # type: ignore[attr-defined]
            self._animation = None
        self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        anim = self._animation
        opacity = getattr(anim, "opacity", 1.0)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(opacity)

        bg = QColor(self._color_hex)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), _CORNER_RADIUS, _CORNER_RADIUS)

        layout = getattr(anim, "layout_mode", "full") if anim else "full"
        if layout == "icon" and anim is not None:
            icon_rect = QRect(4, 4, _ICON_ZONE, _PILL_H - 8)
            anim.paint(p, icon_rect)  # type: ignore[attr-defined]
            text_rect = QRect(_ICON_ZONE + 4, 0, _PILL_W - _ICON_ZONE - 8, _PILL_H)
        else:
            text_rect = self.rect()
            if anim is not None:
                anim.paint(p, self.rect())  # type: ignore[attr-defined]

        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._label)
        p.end()


class SettingsDialog(QDialog):
    """Settings dialog for hotkey, model, device, overlay position, and animations."""

    settings_saved = pyqtSignal(object)  # AppConfig

    def __init__(self, config: AppConfig, first_run: bool = False, parent=None) -> None:
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

        if first_run:
            banner = QLabel(
                "Welcome to spkup!\n"
                "Choose a Whisper model below and click Download to get started."
            )
            banner.setWordWrap(True)
            banner.setStyleSheet(
                "background:#1565C0; color:#ffffff; padding:10px; border-radius:6px;"
            )
            main_layout.addWidget(banner)

        # ── Tab widget ───────────────────────────────────────────────────
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # ═══════════════ General tab ═══════════════
        general_tab = QWidget()
        gen_layout = QVBoxLayout(general_tab)
        gen_layout.setSpacing(12)

        # ── Hotkey ──────────────────────────────────────────────────────────
        self._hotkey_edit = HotkeyEdit(config.hotkey)
        self._hotkey_edit.hotkey_changed.connect(
            lambda v: setattr(self._config, "hotkey", v)
        )
        gen_layout.addWidget(QLabel("Hotkey"))
        gen_layout.addWidget(self._hotkey_edit)

        # ── Model ────────────────────────────────────────────────────────────
        gen_layout.addWidget(QLabel("Model size"))
        model_row = QWidget()
        model_row_layout = QHBoxLayout(model_row)
        model_row_layout.setContentsMargins(0, 0, 0, 0)

        self._model_combo = QComboBox()
        for m in _MODELS:
            badge = "✓" if is_downloaded(m) else "↓"
            size = format_model_size(m)
            suffix = f" ({size})" if size else ""
            self._model_combo.addItem(f"{badge}  {m}{suffix}", m)
        idx = _MODELS.index(config.model_size) if config.model_size in _MODELS else 0
        self._model_combo.setCurrentIndex(idx)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

        self._download_btn = QPushButton("Download")
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.setVisible(not is_downloaded(config.model_size))
        self._download_btn.setToolTip(self._download_tooltip(config.model_size))

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.setVisible(is_downloaded(config.model_size))
        self._delete_btn.setToolTip(
            "Remove this model from the local cache to free disk space."
        )

        model_row_layout.addWidget(self._model_combo, 1)
        model_row_layout.addWidget(self._download_btn)
        model_row_layout.addWidget(self._delete_btn)
        gen_layout.addWidget(model_row)

        # ── Microphone ───────────────────────────────────────────────────────
        gen_layout.addWidget(QLabel("Microphone"))
        self._mic_combo = QComboBox()
        self._mic_combo.addItem("System default", None)
        current_mic = config.input_device
        selected_idx = 0
        for i, dev in enumerate(list_input_devices(), start=1):
            label = f"{dev['name']} ({dev['hostapi']})"
            if dev["is_default"]:
                label += "  • default"
            spec = spec_from_device(dev)
            self._mic_combo.addItem(label, spec)
            if (
                current_mic is not None
                and current_mic.get("name") == spec["name"]
                and current_mic.get("hostapi") == spec["hostapi"]
            ):
                selected_idx = i
        self._mic_combo.setCurrentIndex(selected_idx)
        self._mic_combo.currentIndexChanged.connect(
            lambda idx: setattr(
                self._config, "input_device", self._mic_combo.itemData(idx)
            )
        )
        gen_layout.addWidget(self._mic_combo)

        # ── Device ───────────────────────────────────────────────────────────
        gen_layout.addWidget(QLabel("Device"))
        self._device_combo = QComboBox()
        self._device_combo.addItems(["cuda", "cpu"])
        has_cuda = _detect_cuda()
        if not has_cuda:
            model = cast(QStandardItemModel | None, self._device_combo.model())
            if model is not None:
                item = model.item(0)
                if item is not None:
                    item.setEnabled(False)
            self._device_combo.setCurrentText("cpu")
        else:
            self._device_combo.setCurrentText(config.device)
        self._device_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "device", v)
        )
        gen_layout.addWidget(self._device_combo)

        # ── Compute type ─────────────────────────────────────────────────────
        gen_layout.addWidget(QLabel("Compute type"))
        self._compute_combo = QComboBox()
        self._compute_combo.addItems(["float16", "int8", "float32"])
        self._compute_combo.setCurrentText(config.compute_type)
        self._compute_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "compute_type", v)
        )
        gen_layout.addWidget(self._compute_combo)

        # ── Playback ──────────────────────────────────────────────────────────
        self._mute_playback_checkbox = QCheckBox("Mute playback while recording")
        self._mute_playback_checkbox.setChecked(
            config.mute_playback_while_recording
        )
        self._mute_playback_checkbox.setToolTip(
            "Temporarily mute playback output while recording is active."
        )
        self._mute_playback_checkbox.toggled.connect(
            lambda checked: setattr(
                self._config,
                "mute_playback_while_recording",
                checked,
            )
        )
        gen_layout.addWidget(self._mute_playback_checkbox)
        gen_layout.addStretch()

        tabs.addTab(general_tab, "General")

        # ═══════════════ Overlay tab ═══════════════
        overlay_tab = QWidget()
        ovl_layout = QVBoxLayout(overlay_tab)
        ovl_layout.setSpacing(12)

        # ── Overlay position ─────────────────────────────────────────────────
        ovl_layout.addWidget(QLabel("Overlay position"))
        self._overlay_combo = QComboBox()
        self._overlay_combo.addItems(
            ["bottom-right", "bottom-center", "bottom-left",
             "top-right", "top-center", "top-left"]
        )
        self._overlay_combo.setCurrentText(config.overlay_position)
        self._overlay_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "overlay_position", v)
        )
        ovl_layout.addWidget(self._overlay_combo)

        # ── Animation combos ─────────────────────────────────────────────────
        from spkup.animations import get_display_name, get_keys_for_state

        self._anim_combos: dict[OverlayState, QComboBox] = {}
        for state in _ANIM_STATE_ORDER:
            label = _STATE_LABELS_UI[state]
            ovl_layout.addWidget(QLabel(f"{label} animation"))
            combo = QComboBox()
            keys = get_keys_for_state(state)
            current_key = getattr(config, _ANIM_CONFIG_FIELD[state])
            for k in keys:
                combo.addItem(get_display_name(state, k), k)
            # Select current
            for i in range(combo.count()):
                if combo.itemData(i) == current_key:
                    combo.setCurrentIndex(i)
                    break
            combo.currentIndexChanged.connect(
                lambda _idx, s=state, c=combo: self._on_anim_combo_changed(s, c)
            )
            ovl_layout.addWidget(combo)
            self._anim_combos[state] = combo

        # ── Preview ──────────────────────────────────────────────────────────
        ovl_layout.addSpacing(8)
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight:bold;")
        ovl_layout.addWidget(preview_label)

        preview_row = QWidget()
        preview_layout = QHBoxLayout(preview_row)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self._preview_widget = AnimationPreviewWidget()
        preview_layout.addWidget(self._preview_widget)
        preview_layout.addStretch()

        self._test_btn = QPushButton("Test")
        self._test_btn.setToolTip("Cycle through all 4 states with current animation selections")
        self._test_btn.clicked.connect(self._on_test)
        preview_layout.addWidget(self._test_btn)

        ovl_layout.addWidget(preview_row)
        ovl_layout.addStretch()

        tabs.addTab(overlay_tab, "Overlay")

        # Start by previewing the recording animation
        self._trigger_preview(OverlayState.RECORDING)

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

    def _on_anim_combo_changed(self, state: OverlayState, combo: QComboBox) -> None:
        key = combo.currentData()
        field = _ANIM_CONFIG_FIELD[state]
        setattr(self._config, field, key)
        self._trigger_preview(state)

    def _trigger_preview(self, state: OverlayState) -> None:
        combo = self._anim_combos.get(state)
        if combo is None:
            return
        key = combo.currentData()
        if key:
            self._preview_widget.preview(state, key)

    def _on_test(self) -> None:
        """Cycle through all 4 states with 1.2 s each."""
        self._test_btn.setEnabled(False)
        states = list(_ANIM_STATE_ORDER)
        delay = 1200  # ms between states

        def show_next(idx: int) -> None:
            if idx >= len(states):
                self._preview_widget.stop_preview()
                self._test_btn.setEnabled(True)
                # Return to recording preview
                self._trigger_preview(OverlayState.RECORDING)
                return
            s = states[idx]
            combo = self._anim_combos.get(s)
            key = combo.currentData() if combo else "classic"
            self._preview_widget.preview(s, key)
            QTimer.singleShot(delay, lambda: show_next(idx + 1))

        show_next(0)

    def _on_model_changed(self, index: int) -> None:
        model_size = self._model_combo.currentData()
        self._config.model_size = model_size
        downloaded = is_downloaded(model_size)
        self._download_btn.setVisible(not downloaded)
        self._download_btn.setToolTip(self._download_tooltip(model_size))
        self._delete_btn.setVisible(downloaded)

    def _download_tooltip(self, model_size: str) -> str:
        size = format_model_size(model_size)
        if size:
            return f"Download the {model_size} model ({size})."
        return f"Download the {model_size} model."

    def _set_combo_badge(self, model_size: str, badge: str) -> None:
        """Update the currently selected combo row with a new badge prefix."""
        idx = self._model_combo.currentIndex()
        size = format_model_size(model_size)
        suffix = f" ({size})" if size else ""
        self._model_combo.setItemText(idx, f"{badge}  {model_size}{suffix}")

    def _on_download(self) -> None:
        model_size = self._model_combo.currentData()

        size_hint = format_model_size(model_size)
        label = (
            f"Downloading {model_size}"
            + (f" ({size_hint})" if size_hint else "")
            + "…\nThis can take a while."
        )
        # Indeterminate busy indicator: huggingface_hub does not expose a
        # byte-level progress callback that works in the windowed build,
        # and file-by-file jumps stall on the big model file. A marquee
        # bar is a more honest signal that work is ongoing.
        self._progress_dlg = QProgressDialog(label, "Cancel", 0, 0, self)
        self._progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dlg.setMinimumDuration(0)

        self._download_worker = _ModelDownloadWorker(model_size)
        self._download_worker.finished.connect(self._on_download_done)
        self._download_worker.error.connect(self._on_download_error)
        self._progress_dlg.canceled.connect(self._download_worker.terminate)
        self._download_worker.start()
        self._progress_dlg.exec()

    def _on_download_done(self) -> None:
        if self._progress_dlg is not None:
            self._progress_dlg.close()
        model_size = self._model_combo.currentData()
        self._set_combo_badge(model_size, "✓")
        self._download_btn.setVisible(False)
        self._delete_btn.setVisible(True)

    def _on_download_error(self, msg: str) -> None:
        if self._progress_dlg is not None:
            self._progress_dlg.close()
        QMessageBox.critical(self, "Download failed", msg)

    def _on_delete(self) -> None:
        model_size = self._model_combo.currentData()
        if not is_downloaded(model_size):
            self._download_btn.setVisible(True)
            self._delete_btn.setVisible(False)
            return

        size_hint = format_model_size(model_size)
        detail = (
            f"Remove the {model_size} model"
            + (f" ({size_hint})" if size_hint else "")
            + " from the local cache?\n\n"
            "You can download it again later from this dialog."
        )
        reply = QMessageBox.question(
            self,
            "Delete model",
            detail,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_model(model_size)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Delete failed", str(exc))
            return

        self._set_combo_badge(model_size, "↓")
        self._download_btn.setVisible(True)
        self._download_btn.setToolTip(self._download_tooltip(model_size))
        self._delete_btn.setVisible(False)

    def _on_save(self) -> None:
        self._preview_widget.stop_preview()
        save(self._config)
        self.settings_saved.emit(self._config)
        self.accept()

    def reject(self) -> None:
        self._preview_widget.stop_preview()
        super().reject()
