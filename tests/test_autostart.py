import winreg
from unittest.mock import MagicMock, patch

from spkup import autostart


def test_exe_command_uses_python_module_in_dev_mode():
    with patch.object(autostart.sys, "executable", r"C:\Python312\python.exe"):
        assert autostart._exe_command() == r'"C:\Python312\python.exe" -m spkup'


def test_exe_command_uses_frozen_executable_when_packaged():
    with patch.object(autostart.sys, "frozen", True, create=True), patch.object(
        autostart.sys, "executable", r"C:\Apps\spkup\spkup.exe"
    ):
        assert autostart._exe_command() == r'"C:\Apps\spkup\spkup.exe"'


def test_enable_autostart_calls_set_value_ex():
    """enable_autostart() writes value name 'spkup' to the Run key."""
    mock_key = MagicMock()
    with patch("winreg.OpenKey") as mock_open, patch("winreg.SetValueEx") as mock_set:
        mock_open.return_value.__enter__.return_value = mock_key
        autostart.enable_autostart()
    mock_set.assert_called_once()
    assert mock_set.call_args.args[1] == "spkup"
    assert mock_set.call_args.args[4] == autostart._exe_command()


def test_disable_autostart_calls_delete_value():
    """disable_autostart() deletes value name 'spkup' from the Run key."""
    mock_key = MagicMock()
    with patch("winreg.OpenKey") as mock_open, patch("winreg.DeleteValue") as mock_del:
        mock_open.return_value.__enter__.return_value = mock_key
        autostart.disable_autostart()
    mock_del.assert_called_once()
    assert mock_del.call_args.args[1] == "spkup"


def test_disable_autostart_ignores_missing_key():
    """disable_autostart() does not raise when the registry key is absent."""
    with patch("winreg.OpenKey", side_effect=FileNotFoundError):
        autostart.disable_autostart()  # must not raise


def test_is_autostart_enabled_true():
    """is_autostart_enabled() returns True when the registry key exists."""
    with patch("winreg.OpenKey") as mock_open, patch(
        "winreg.QueryValueEx", return_value=("cmd", 1)
    ):
        mock_open.return_value.__enter__.return_value = MagicMock()
        assert autostart.is_autostart_enabled() is True


def test_is_autostart_enabled_false():
    """is_autostart_enabled() returns False when the registry key is absent."""
    with patch("winreg.OpenKey", side_effect=FileNotFoundError):
        assert autostart.is_autostart_enabled() is False
