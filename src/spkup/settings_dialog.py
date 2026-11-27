from __future__ import annotations

import dataclasses
from typing import cast

import keyring
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFocusEvent, QKeyEvent, QPalette, QStandardItemModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QStackedWidget,
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
from spkup.platform_support import is_macos, supports_playback_mute, uses_mlx_engine
from spkup.post_processing import KEYRING_SERVICE, KEYRING_USERNAME, OPENAI_BASE_URL
from spkup.transcriber import VOCABULARY_PROMPT_MAX_CHARS


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
        # Capture only on an explicit click. Otherwise the dialog hands this
        # field initial focus on open, which swaps the saved hotkey for the
        # "Press hotkey…" placeholder before the user has done anything.
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
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
        # macOS Qt swaps Control and Command: the physical Control key arrives
        # as MetaModifier, which is what pynput reports as "ctrl" at runtime.
        # Match that here so capturing Ctrl+… on macOS isn't silently dropped.
        ctrl_modifier = (
            Qt.KeyboardModifier.MetaModifier
            if is_macos()
            else Qt.KeyboardModifier.ControlModifier
        )
        if mods & ctrl_modifier:
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


_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"]


def parse_replacements(text: str) -> dict[str, str]:
    """Parse one ``from -> to`` rule per line, skipping blank or malformed lines."""
    rules: dict[str, str] = {}
    for line in text.splitlines():
        source, arrow, target = line.partition("->")
        if arrow and source.strip():
            rules[source.strip()] = target.strip()
    return rules


_PAGE_MARGIN = 24
_CARD_RADIUS = 10


def _secondary(text: str, *, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName("secondary")
    label.setWordWrap(wrap)
    return label


class _Card(QFrame):
    """Rounded group of settings rows separated by hairlines, as in System Settings."""

    def __init__(self, title: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._title = title
        self._has_rows = False

    def add(self, widget: QWidget) -> QWidget:
        if self._has_rows:
            line = QFrame()
            line.setObjectName("hairline")
            line.setFixedHeight(1)
            self._layout.addWidget(line)
        self._layout.addWidget(widget)
        self._has_rows = True
        return widget

    def row(self, title: str, control: QWidget, description: str = "") -> QWidget:
        """Title (and optional description) on the left, control on the right."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(QLabel(title))
        if description:
            text.addWidget(_secondary(description))
        layout.addLayout(text, 1)
        layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return self.add(row)

    def block(self, title: str, control: QWidget, description: str = "") -> QWidget:
        """Title and description above a full-width control (text editors)."""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(4)
        layout.addWidget(QLabel(title))
        if description:
            layout.addWidget(_secondary(description))
        layout.addSpacing(4)
        layout.addWidget(control)
        return self.add(row)


def _section(title: str) -> QLabel:
    label = QLabel(title)
    label.setObjectName("section")
    return label


def _page(title: str, *items: QWidget) -> QScrollArea:
    content = QWidget()
    content.setObjectName("page")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(_PAGE_MARGIN, 18, _PAGE_MARGIN, _PAGE_MARGIN)
    layout.setSpacing(8)
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    layout.addWidget(heading)
    layout.addSpacing(6)
    for item in items:
        if isinstance(item, QLabel) and item.objectName() == "section":
            layout.addSpacing(10)
        layout.addWidget(item)
    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(content)
    return scroll


def _stylesheet(palette: QPalette) -> str:
    text = palette.color(QPalette.ColorRole.WindowText)
    window = palette.color(QPalette.ColorRole.Window)
    dark = window.lightness() < 128
    card = window.lighter(125) if dark else palette.color(QPalette.ColorRole.Base)
    sidebar = window.darker(115) if dark else window.darker(106)
    hairline = QColor(text)
    hairline.setAlphaF(0.10)
    secondary = QColor(text)
    secondary.setAlphaF(0.55)
    highlight = palette.color(QPalette.ColorRole.Highlight)
    field = window.darker(118) if dark else palette.color(QPalette.ColorRole.Base)
    border = QColor(text)
    border.setAlphaF(0.16)

    def rgba(color: QColor) -> str:
        return f"rgba({color.red()},{color.green()},{color.blue()},{color.alphaF():.2f})"

    return f"""
        QWidget#page {{ background: {window.name()}; }}
        QListWidget#sidebar {{
            background: {sidebar.name()}; border: none; outline: none; padding: 10px 8px;
        }}
        QListWidget#sidebar::item {{ padding: 7px 10px; border-radius: 6px; margin: 1px 0; }}
        QListWidget#sidebar::item:selected {{ background: {highlight.name()}; color: white; }}
        QFrame#card {{ background: {card.name()}; border-radius: {_CARD_RADIUS}px; }}
        QFrame#hairline {{ background: {rgba(hairline)}; margin: 0 14px; }}
        QLabel#pageTitle {{ font-size: 20px; font-weight: 600; }}
        QLabel#section {{ font-size: 12px; font-weight: 600; color: {rgba(secondary)}; padding-left: 4px; }}
        QLabel#secondary {{ font-size: 11px; color: {rgba(secondary)}; }}
        QLabel#warning {{ font-size: 11px; color: #E8710A; }}
        QLineEdit, QPlainTextEdit {{
            background: {field.name()}; border: 1px solid {rgba(border)}; border-radius: 6px;
            padding: 5px 8px; selection-background-color: {highlight.name()};
        }}
        QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {highlight.name()}; }}
        QLineEdit:disabled, QPlainTextEdit:disabled {{ color: {rgba(secondary)}; }}
        QLabel#banner {{
            background: {highlight.name()}; color: white; padding: 10px 12px; border-radius: 8px;
        }}
    """


class SettingsDialog(QDialog):
    """Settings window: a sidebar of sections, each a page of grouped rows."""

    settings_saved = pyqtSignal(object)  # AppConfig

    def __init__(self, config: AppConfig, first_run: bool = False, parent=None) -> None:
        super().__init__(parent)
        from spkup import __version__
        self.setWindowTitle("spkup Settings")
        self.setModal(True)
        self.resize(780, 580)
        self.setMinimumSize(700, 480)
        self.setStyleSheet(_stylesheet(self.palette()))

        # Work on a copy so Cancel discards all changes
        self._config = dataclasses.replace(config)
        self._download_worker: _ModelDownloadWorker | None = None
        self._progress_dlg: QProgressDialog | None = None

        pages = [
            ("General", self._build_general_page(config)),
            ("Transcription", self._build_transcription_page(config, first_run)),
            ("Vocabulary", self._build_vocabulary_page(config)),
            ("AI Cleanup", self._build_cleanup_page(config)),
        ]

        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(190)
        self._stack = QStackedWidget()
        for name, page in pages:
            self._sidebar.addItem(QListWidgetItem(name))
            self._stack.addWidget(page)
        self._sidebar.currentRowChanged.connect(self._stack.setCurrentIndex)
        # First run lands on the model, which must be downloaded before anything works.
        self._sidebar.setCurrentRow(1 if first_run else 0)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(_PAGE_MARGIN, 10, _PAGE_MARGIN, 14)
        footer_layout.addWidget(_secondary(f"spkup {__version__}", wrap=False))
        footer_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        footer_layout.addWidget(cancel_btn)
        footer_layout.addWidget(save_btn)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._stack, 1)
        right_layout.addWidget(footer)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar)
        root.addWidget(right, 1)

    # ---------- Pages --------------------------------------------------------

    def _build_general_page(self, config: AppConfig) -> QScrollArea:
        self._hotkey_edit = HotkeyEdit(config.hotkey)
        self._hotkey_edit.setFixedWidth(200)
        self._hotkey_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hotkey_edit.hotkey_changed.connect(
            lambda v: setattr(self._config, "hotkey", v)
        )
        shortcut = _Card()
        shortcut.row(
            "Push-to-talk shortcut",
            self._hotkey_edit,
            "Hold to record, release to transcribe. Click the field, then press the keys.",
        )

        self._mic_combo = QComboBox()
        self._mic_combo.setFixedWidth(260)
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

        self._mute_playback_checkbox = QCheckBox()
        self._mute_playback_checkbox.setChecked(config.mute_playback_while_recording)
        mute_description = "Silence other audio while you speak."
        if not supports_playback_mute():
            self._mute_playback_checkbox.setChecked(False)
            self._mute_playback_checkbox.setEnabled(False)
            mute_description = "Available on Windows only."
            self._config.mute_playback_while_recording = False
        self._mute_playback_checkbox.toggled.connect(
            lambda checked: setattr(self._config, "mute_playback_while_recording", checked)
        )
        audio = _Card()
        audio.row("Microphone", self._mic_combo)
        audio.row("Mute playback while recording", self._mute_playback_checkbox, mute_description)

        self._overlay_combo = QComboBox()
        self._overlay_combo.setFixedWidth(180)
        for value in (
            "bottom-center", "bottom-left", "bottom-right",
            "top-center", "top-left", "top-right",
        ):
            self._overlay_combo.addItem(value.replace("-", " ").capitalize(), value)
        self._overlay_combo.setCurrentIndex(
            max(0, self._overlay_combo.findData(config.overlay_position))
        )
        self._overlay_combo.currentIndexChanged.connect(
            lambda _i: setattr(self._config, "overlay_position", self._overlay_combo.currentData())
        )
        overlay = _Card()
        overlay.row(
            "Overlay position",
            self._overlay_combo,
            "Where the recording indicator appears on screen.",
        )

        self._updates_checkbox = QCheckBox()
        self._updates_checkbox.setChecked(config.check_updates_on_startup)
        self._updates_checkbox.toggled.connect(
            lambda checked: setattr(self._config, "check_updates_on_startup", checked)
        )
        updates = _Card()
        updates.row(
            "Check for updates on startup",
            self._updates_checkbox,
            "spkup asks before downloading or installing anything.",
        )

        return _page(
            "General",
            _section("Shortcut"), shortcut,
            _section("Audio"), audio,
            _section("Appearance"), overlay,
            _section("Updates"), updates,
        )

    def _build_transcription_page(self, config: AppConfig, first_run: bool) -> QScrollArea:
        items: list[QWidget] = []
        if first_run:
            banner = QLabel(
                "Welcome to spkup! Pick a Whisper model and click Download to get started."
            )
            banner.setObjectName("banner")
            banner.setWordWrap(True)
            items.append(banner)

        self._model_combo = QComboBox()
        self._model_combo.setFixedWidth(220)
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
        self._delete_btn.setToolTip("Remove this model from the local cache to free disk space.")

        model_controls = QWidget()
        model_layout = QHBoxLayout(model_controls)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.addWidget(self._model_combo)
        model_layout.addWidget(self._download_btn)
        model_layout.addWidget(self._delete_btn)

        model = _Card()
        model.row(
            "Whisper model",
            model_controls,
            "Larger models are more accurate and slower. ✓ means downloaded.",
        )

        self._device_combo = QComboBox()
        self._device_combo.setFixedWidth(120)
        self._device_combo.addItems(["cuda", "cpu"])
        if not _detect_cuda():
            items_model = cast(QStandardItemModel | None, self._device_combo.model())
            if items_model is not None:
                item = items_model.item(0)
                if item is not None:
                    item.setEnabled(False)
            self._device_combo.setCurrentText("cpu")
            self._config.device = "cpu"
        else:
            self._device_combo.setCurrentText(config.device)
        self._device_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "device", v)
        )

        self._compute_combo = QComboBox()
        self._compute_combo.setFixedWidth(120)
        self._compute_combo.addItems(["float16", "int8", "float32"])
        self._compute_combo.setCurrentText(config.compute_type)
        self._compute_combo.currentTextChanged.connect(
            lambda v: setattr(self._config, "compute_type", v)
        )

        # MLX always runs on the Apple GPU; device and compute type do not apply.
        if not uses_mlx_engine():
            model.row("Device", self._device_combo, "CUDA needs an NVIDIA GPU.")
            model.row("Compute type", self._compute_combo, "int8 uses the least memory.")

        self._idle_unload_combo = QComboBox()
        self._idle_unload_combo.setFixedWidth(140)
        minutes = sorted({0, 5, 10, 15, 30, 60, 120, 240, config.model_idle_unload_minutes})
        for value in minutes:
            self._idle_unload_combo.addItem("Never" if value == 0 else f"After {value} min", value)
        self._idle_unload_combo.setCurrentIndex(
            self._idle_unload_combo.findData(config.model_idle_unload_minutes)
        )
        self._idle_unload_combo.currentIndexChanged.connect(
            lambda _i: setattr(
                self._config,
                "model_idle_unload_minutes",
                self._idle_unload_combo.currentData(),
            )
        )
        memory = _Card()
        memory.row(
            "Unload model after inactivity",
            self._idle_unload_combo,
            "Frees memory when idle. The next dictation reloads it, which takes a few seconds.",
        )

        items += [_section("Model"), model, _section("Memory"), memory]
        return _page("Transcription", *items)

    def _build_vocabulary_page(self, config: AppConfig) -> QScrollArea:
        self._vocabulary_edit = QPlainTextEdit("\n".join(config.vocabulary))
        self._vocabulary_edit.setPlaceholderText("Tempobase\nspkup\nDiagnet")
        self._vocabulary_edit.setFixedHeight(120)

        self._replacements_edit = QPlainTextEdit(
            "\n".join(f"{source} -> {target}" for source, target in config.replacements.items())
        )
        self._replacements_edit.setPlaceholderText("temple base -> Tempobase\nspeak up -> spkup")
        self._replacements_edit.setFixedHeight(120)

        vocabulary = _Card()
        vocabulary.block(
            "Vocabulary",
            self._vocabulary_edit,
            "Names and terms Whisper should spell your way, one per line. "
            "It is a strong hint, not a guarantee.",
        )
        replacements = _Card()
        replacements.block(
            "Replacements",
            self._replacements_edit,
            "One “from -> to” rule per line. Applied last, ignoring case, whole words only.",
        )
        return _page("Vocabulary", vocabulary, replacements)

    def _build_cleanup_page(self, config: AppConfig) -> QScrollArea:
        self._post_processing_toggle = QCheckBox()
        self._post_processing_toggle.setChecked(config.post_processing_enabled)
        toggle = _Card()
        toggle.row(
            "Clean up with an LLM",
            self._post_processing_toggle,
            "A language model fixes errors, punctuation and casing and follows your "
            "instructions. If it fails, the raw text is copied and a notification says why.",
        )

        self._provider_combo = QComboBox()
        self._provider_combo.setFixedWidth(240)
        self._provider_combo.addItem("Local (Ollama, LM Studio)", "local")
        self._provider_combo.addItem("OpenAI", "openai")
        self._provider_combo.setCurrentIndex(
            max(0, self._provider_combo.findData(config.post_processing_provider))
        )
        self._provider = self._provider_combo.currentData()
        self._provider_fields: dict[str, tuple[str, str, str]] = {}
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        self._privacy_note = QLabel("Your transcribed text is sent to OpenAI and leaves this Mac.")
        self._privacy_note.setObjectName("warning")
        self._privacy_note.setWordWrap(True)

        self._base_url_edit = QLineEdit(config.post_processing_base_url)
        self._base_url_edit.setFixedWidth(240)
        self._llm_model_edit = QLineEdit(config.post_processing_model)
        self._llm_model_edit.setFixedWidth(240)

        self._effort_combo = QComboBox()
        self._effort_combo.setFixedWidth(240)
        for label, value in (
            ("Off (fastest)", "none"),
            ("Low", "low"),
            ("Medium", "medium"),
            ("High", "high"),
            ("Model default (send nothing)", ""),
        ):
            self._effort_combo.addItem(label, value)
        self._effort_combo.setCurrentIndex(
            max(0, self._effort_combo.findData(config.post_processing_reasoning_effort))
        )

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setFixedWidth(240)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        provider = _Card()
        provider_row = provider.row("Provider", self._provider_combo)
        provider_row.layout().itemAt(0).layout().addWidget(self._privacy_note)
        provider.row("Base URL", self._base_url_edit)
        provider.row("Model", self._llm_model_edit)
        provider.row(
            "Thinking",
            self._effort_combo,
            "Off is fastest. Pick “Model default” if the model rejects the setting.",
        )
        self._api_key_row = provider.row(
            "API key", self._api_key_edit, "Kept in the system keychain, never in config files."
        )

        self._instructions_edit = QPlainTextEdit(config.post_processing_instructions)
        self._instructions_edit.setPlaceholderText(
            "e.g. Use a formal tone. Format lists as bullets."
        )
        self._instructions_edit.setFixedHeight(120)
        instructions = _Card()
        instructions.block(
            "Instructions",
            self._instructions_edit,
            "Extra guidance for the model. Your vocabulary is always included.",
        )

        self._cleanup_details = (provider, instructions)
        self._post_processing_toggle.toggled.connect(self._update_cleanup_enabled)
        self._update_cleanup_enabled(config.post_processing_enabled)
        self._update_provider_widgets()

        return _page(
            "AI Cleanup",
            toggle,
            _section("Connection"), provider,
            _section("Prompt"), instructions,
        )

    # ---------- Slots --------------------------------------------------------

    def _update_cleanup_enabled(self, enabled: bool) -> None:
        for card in self._cleanup_details:
            card.setEnabled(enabled)

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

    def _is_openai(self) -> bool:
        return self._provider_combo.currentData() == "openai"

    def _on_provider_changed(self, _index: int) -> None:
        # Each provider keeps what the user typed, so flipping back and forth loses nothing.
        self._provider_fields[self._provider] = (
            self._base_url_edit.text(),
            self._llm_model_edit.text(),
            self._effort_combo.currentData(),
        )
        self._provider = self._provider_combo.currentData()
        defaults = {
            "local": (
                AppConfig.post_processing_base_url,
                AppConfig.post_processing_model,
                AppConfig.post_processing_reasoning_effort,
            ),
            # Non-reasoning OpenAI models reject reasoning_effort, so send nothing by default.
            "openai": (OPENAI_BASE_URL, "", ""),
        }
        base_url, model, effort = self._provider_fields.get(
            self._provider, defaults[self._provider]
        )
        self._base_url_edit.setText(base_url)
        self._llm_model_edit.setText(model)
        self._effort_combo.setCurrentIndex(self._effort_combo.findData(effort))
        self._update_provider_widgets()

    def _update_provider_widgets(self) -> None:
        openai = self._is_openai()
        for widget in (self._privacy_note, self._api_key_row, self._api_key_edit):
            widget.setVisible(openai)
        self._llm_model_edit.setPlaceholderText("OpenAI model name" if openai else "")
        if not openai:
            return
        try:
            stored = bool(keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME))
        except Exception:
            stored = False
        self._api_key_edit.setPlaceholderText(
            "Stored in the system keychain. Leave blank to keep it."
            if stored
            else "Paste your OpenAI API key"
        )

    def _on_save(self) -> None:
        if self._post_processing_toggle.isChecked() and not (
            self._base_url_edit.text().strip() and self._llm_model_edit.text().strip()
        ):
            QMessageBox.warning(
                self,
                "Post-processing incomplete",
                "Fill in the base URL and the model, or turn post-processing off.",
            )
            return
        self._config.vocabulary = [
            term.strip()
            for term in self._vocabulary_edit.toPlainText().splitlines()
            if term.strip()
        ]
        self._config.replacements = parse_replacements(
            self._replacements_edit.toPlainText()
        )
        self._config.post_processing_enabled = self._post_processing_toggle.isChecked()
        self._config.post_processing_provider = self._provider_combo.currentData()
        self._config.post_processing_base_url = self._base_url_edit.text().strip()
        self._config.post_processing_model = self._llm_model_edit.text().strip()
        self._config.post_processing_reasoning_effort = self._effort_combo.currentData()
        self._config.post_processing_instructions = (
            self._instructions_edit.toPlainText().strip()
        )
        api_key = self._api_key_edit.text().strip()
        if api_key and self._is_openai():
            try:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            except Exception as exc:
                QMessageBox.warning(self, "API key not saved", str(exc))
                return
        if self._post_processing_toggle.isChecked() and self._is_openai() and not api_key:
            try:
                stored = bool(keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME))
            except Exception:
                stored = False
            if not stored:
                QMessageBox.warning(
                    self,
                    "OpenAI API key missing",
                    "Paste your OpenAI API key, or turn post-processing off.",
                )
                return
        if len(", ".join(self._config.vocabulary)) > VOCABULARY_PROMPT_MAX_CHARS:
            message = (
                f"Only the first {VOCABULARY_PROMPT_MAX_CHARS} characters of the vocabulary "
                "reach Whisper."
            )
            if self._config.post_processing_enabled:
                message += " The LLM still gets every term."
            QMessageBox.information(self, "Vocabulary too long", message)
        save(self._config)
        self.settings_saved.emit(self._config)
        self.accept()

