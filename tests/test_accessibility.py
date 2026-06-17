from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

from spkup import accessibility


def test_input_monitoring_required_only_on_macos() -> None:
    assert accessibility.input_monitoring_required("darwin") is True
    assert accessibility.input_monitoring_required("win32") is False
    assert accessibility.input_monitoring_required("linux") is False


def test_input_monitoring_trusted_true_off_macos() -> None:
    assert accessibility.is_input_monitoring_trusted("win32") is True
    assert accessibility.request_input_monitoring_trust("win32") is True


def test_is_input_monitoring_trusted_returns_false_when_not_authorized() -> None:
    """When tccutil reports not authorized, should return False."""
    # Mock the Foundation import and subprocess call
    with patch("spkup.accessibility.is_macos", return_value=True):
        fake_nsbundle = MagicMock()
        fake_nsbundle.mainBundle.return_value.bundleIdentifier.return_value = "com.example.spkup"
        
        with patch.dict("sys.modules", {"Foundation": MagicMock(NSBundle=fake_nsbundle)}):
            with patch("spkup.accessibility.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "kTCCServiceListenEvent: denied"
                mock_run.return_value = mock_result
                
                # Should return False when not authorized
                result = accessibility.is_input_monitoring_trusted("darwin")
                assert result is False


def test_is_input_monitoring_trusted_returns_true_when_authorized() -> None:
    """When tccutil reports authorized, should return True."""
    with patch("spkup.accessibility.is_macos", return_value=True):
        fake_nsbundle = MagicMock()
        fake_nsbundle.mainBundle.return_value.bundleIdentifier.return_value = "com.example.spkup"
        
        with patch.dict("sys.modules", {"Foundation": MagicMock(NSBundle=fake_nsbundle)}):
            with patch("spkup.accessibility.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "kTCCServiceListenEvent: authorized"
                mock_run.return_value = mock_result
                
                # Should return True when authorized
                result = accessibility.is_input_monitoring_trusted("darwin")
                assert result is True


def test_is_input_monitoring_trusted_defaults_true_when_check_fails() -> None:
    """When the check fails, should default to True to avoid nagging."""
    with patch("spkup.accessibility.subprocess.run", side_effect=Exception("fail")):
        assert accessibility.is_input_monitoring_trusted("darwin") is True


def test_request_input_monitoring_opens_settings_on_macos() -> None:
    """request_input_monitoring_trust should open settings on macOS."""
    with patch("spkup.accessibility.open_input_monitoring_settings") as mock_open:
        with patch("spkup.accessibility.is_input_monitoring_trusted", return_value=False):
            accessibility.request_input_monitoring_trust("darwin")
    mock_open.assert_called_once_with("darwin")


def test_open_input_monitoring_settings_runs_open_on_macos() -> None:
    with patch("spkup.accessibility.subprocess.run") as run:
        accessibility.open_input_monitoring_settings("darwin")
    run.assert_called_once_with(
        ["open", accessibility.INPUT_MONITORING_SETTINGS_URL], check=False
    )


def test_open_input_monitoring_settings_noop_off_macos() -> None:
    with patch("spkup.accessibility.subprocess.run") as run:
        accessibility.open_input_monitoring_settings("win32")
    run.assert_not_called()


def test_accessibility_required_only_on_macos() -> None:
    assert accessibility.accessibility_required("darwin") is True
    assert accessibility.accessibility_required("win32") is False
    assert accessibility.accessibility_required("linux") is False


def test_trusted_true_off_macos() -> None:
    assert accessibility.is_accessibility_trusted("win32") is True
    assert accessibility.request_accessibility_trust("win32") is True


def _fake_application_services(trusted: bool) -> types.ModuleType:
    module = types.ModuleType("ApplicationServices")
    module.AXIsProcessTrusted = lambda: trusted  # type: ignore[attr-defined]
    module.AXIsProcessTrustedWithOptions = lambda options: trusted  # type: ignore[attr-defined]
    module.kAXTrustedCheckOptionPrompt = "AXTrustedCheckOptionPrompt"  # type: ignore[attr-defined]
    return module


def test_is_trusted_reflects_axis_process_trusted_on_macos() -> None:
    for trusted in (True, False):
        with patch.dict(sys.modules, {"ApplicationServices": _fake_application_services(trusted)}):
            assert accessibility.is_accessibility_trusted("darwin") is trusted


def test_is_trusted_defaults_true_when_pyobjc_missing() -> None:
    # Simulate the import failing inside the function.
    with patch.dict(sys.modules, {"ApplicationServices": None}):
        assert accessibility.is_accessibility_trusted("darwin") is True


def test_request_trust_uses_prompt_option_on_macos() -> None:
    fake = _fake_application_services(trusted=False)
    calls: list[dict] = []
    fake.AXIsProcessTrustedWithOptions = lambda options: calls.append(options) or False  # type: ignore[attr-defined]
    with patch.dict(sys.modules, {"ApplicationServices": fake}):
        assert accessibility.request_accessibility_trust("darwin") is False
    assert calls == [{"AXTrustedCheckOptionPrompt": True}]


def test_open_settings_runs_open_on_macos() -> None:
    with patch("spkup.accessibility.subprocess.run") as run:
        accessibility.open_accessibility_settings("darwin")
    run.assert_called_once_with(
        ["open", accessibility.ACCESSIBILITY_SETTINGS_URL], check=False
    )


def test_open_settings_noop_off_macos() -> None:
    with patch("spkup.accessibility.subprocess.run") as run:
        accessibility.open_accessibility_settings("win32")
    run.assert_not_called()
