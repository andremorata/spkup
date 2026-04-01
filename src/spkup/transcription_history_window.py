from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .transcription_history import TranscriptionHistoryEntry

_PREVIEW_LIMIT = 72


def _build_preview(text: str) -> str:
    collapsed = " ".join(text.split())
    if not collapsed:
        return "(empty transcription)"
    if len(collapsed) <= _PREVIEW_LIMIT:
        return collapsed
    return collapsed[: _PREVIEW_LIMIT - 3].rstrip() + "..."


class TranscriptionHistoryWindow(QDialog):
    """Session-scoped recent transcription history window."""

    copy_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[TranscriptionHistoryEntry] = []

        self.setWindowTitle("spkup - Recent History")
        self.setModal(False)
        self.resize(560, 420)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        description = QLabel("Recent transcriptions for this app session.")
        description.setWordWrap(True)
        main_layout.addWidget(description)

        self._empty_label = QLabel(
            "No recent transcriptions yet.\n"
            "Your last 5 completed transcriptions will appear here."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        main_layout.addWidget(self._empty_label, 1)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self._list_widget = QListWidget()
        self._list_widget.setAlternatingRowColors(True)
        self._list_widget.currentRowChanged.connect(self._on_selection_changed)
        self._list_widget.itemDoubleClicked.connect(lambda _item: self._copy_selected())
        content_layout.addWidget(self._list_widget, 1)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("Select an entry to preview.")
        self._preview.setMinimumHeight(140)
        content_layout.addWidget(self._preview)

        main_layout.addWidget(self._content, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._copy_button = QPushButton("Copy Selected")
        self._copy_button.clicked.connect(self._copy_selected)
        button_row.addWidget(self._copy_button)

        self._delete_button = QPushButton("Delete Selected")
        self._delete_button.clicked.connect(self._delete_selected)
        button_row.addWidget(self._delete_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.hide)
        button_row.addWidget(close_button)

        main_layout.addLayout(button_row)

        self._refresh_view()

    def entries(self) -> list[TranscriptionHistoryEntry]:
        return list(self._entries)

    def selected_entry(self) -> TranscriptionHistoryEntry | None:
        row = self._list_widget.currentRow()
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def set_entries(self, entries: Sequence[TranscriptionHistoryEntry]) -> None:
        selected_row = self._list_widget.currentRow()
        self._entries = list(entries)
        self._reload_items(selected_row)

    def show_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def _reload_items(self, preferred_row: int = 0) -> None:
        self._list_widget.blockSignals(True)
        self._list_widget.clear()

        for entry in self._entries:
            item = QListWidgetItem(_build_preview(entry.text))
            item.setToolTip(entry.text or "(empty transcription)")
            self._list_widget.addItem(item)

        self._list_widget.blockSignals(False)

        if self._entries:
            target_row = max(0, min(preferred_row, len(self._entries) - 1))
            self._list_widget.setCurrentRow(target_row)
        else:
            self._preview.clear()
            self._on_selection_changed(-1)

        self._refresh_view()

    def _refresh_view(self) -> None:
        has_entries = bool(self._entries)
        self._empty_label.setVisible(not has_entries)
        self._content.setVisible(has_entries)
        self._copy_button.setEnabled(has_entries and self.selected_entry() is not None)
        self._delete_button.setEnabled(has_entries and self.selected_entry() is not None)

    def _on_selection_changed(self, row: int) -> None:
        if 0 <= row < len(self._entries):
            self._preview.setPlainText(self._entries[row].text)
        else:
            self._preview.clear()
        self._refresh_view()

    def _copy_selected(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            return
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(entry.text)
        self.copy_requested.emit(entry.text)

    def _delete_selected(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            return
        self.delete_requested.emit(entry.id)
