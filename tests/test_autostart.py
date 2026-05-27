from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from spkup import autostart


@pytest.fixture
def fake_winreg(monkeypatch):
    module = SimpleNamespace(
        HKEY_CURRENT_USER=object(),
        KEY_SET_VALUE=1,
        REG_SZ=1,
        OpenKey=MagicMock(),
        SetValueEx=MagicMock(),
        DeleteValue=MagicMock(),
        QueryValueEx=MagicMock(),
    )
    monkeypatch.setattr(autostart, "_winreg", module)
    monkeypatch.setattr(autostart, "supports_autostart", lambda: True)
    return module


def test_exe_command_uses_python_module_in_dev_mode():
    with patch.object(autostart.sys, "executable", r"C:\Python312\python.exe"):
        assert autostart._exe_command() == r'"C:\Python312\python.exe" -m spkup'


def test_exe_command_uses_frozen_executable_when_packaged():
    with patch.object(autostart.sys, "frozen", True, create=True), patch.object(
        autostart.sys, "executable", r"C:\Apps\spkup\spkup.exe"
    ):
        assert autostart._exe_command() == r'"C:\Apps\spkup\spkup.exe"'


def test_enable_autostart_calls_set_value_ex(fake_winreg):
    """enable_autostart() writes value name 'spkup' to the Run key."""
    mock_key = MagicMock()
    fake_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    autostart.enable_autostart()

    fake_winreg.SetValueEx.assert_called_once()
    assert fake_winreg.SetValueEx.call_args.args[1] == "spkup"
    assert fake_winreg.SetValueEx.call_args.args[4] == autostart._exe_command()


def test_disable_autostart_calls_delete_value(fake_winreg):
    """disable_autostart() deletes value name 'spkup' from the Run key."""
    mock_key = MagicMock()
    fake_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    autostart.disable_autostart()

    fake_winreg.DeleteValue.assert_called_once()
    assert fake_winreg.DeleteValue.call_args.args[1] == "spkup"


def test_disable_autostart_ignores_missing_key(fake_winreg):
    """disable_autostart() does not raise when the registry key is absent."""
    fake_winreg.OpenKey.side_effect = FileNotFoundError

    autostart.disable_autostart()  # must not raise


def test_is_autostart_enabled_true(fake_winreg):
    """is_autostart_enabled() returns True when the registry key exists."""
    fake_winreg.OpenKey.return_value.__enter__.return_value = MagicMock()
    fake_winreg.QueryValueEx.return_value = ("cmd", 1)

    assert autostart.is_autostart_enabled() is True


def test_is_autostart_enabled_false(fake_winreg):
    """is_autostart_enabled() returns False when the registry key is absent."""
    fake_winreg.OpenKey.side_effect = FileNotFoundError

    assert autostart.is_autostart_enabled() is False


def test_is_autostart_enabled_false_when_unsupported(monkeypatch):
    monkeypatch.setattr(autostart, "supports_autostart", lambda: False)

    assert autostart.is_autostart_enabled() is False


def test_enable_autostart_raises_when_unsupported(monkeypatch):
    monkeypatch.setattr(autostart, "supports_autostart", lambda: False)

    with pytest.raises(autostart.AutostartUnavailableError):
        autostart.enable_autostart()
