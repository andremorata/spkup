from unittest.mock import MagicMock, patch

from spkup.clipboard import copy_to_clipboard


def test_copy_to_clipboard_calls_set_text():
    """copy_to_clipboard() delegates to QApplication.clipboard().setText()."""
    mock_cb = MagicMock()
    with patch("spkup.clipboard.QApplication.clipboard", return_value=mock_cb):
        copy_to_clipboard("hello world")
    mock_cb.setText.assert_called_once_with("hello world")


def test_copy_to_clipboard_unicode():
    """copy_to_clipboard() passes unicode text through unchanged."""
    mock_cb = MagicMock()
    with patch("spkup.clipboard.QApplication.clipboard", return_value=mock_cb):
        copy_to_clipboard("Olá, mundo! 🎤")
    mock_cb.setText.assert_called_once_with("Olá, mundo! 🎤")


def test_copy_to_clipboard_empty_string():
    """copy_to_clipboard() accepts an empty string."""
    mock_cb = MagicMock()
    with patch("spkup.clipboard.QApplication.clipboard", return_value=mock_cb):
        copy_to_clipboard("")
    mock_cb.setText.assert_called_once_with("")
