from PyQt6.QtWidgets import QApplication


def copy_to_clipboard(text: str) -> None:
    """Copy *text* to the system clipboard (Unicode-safe)."""
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)
