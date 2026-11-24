from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from spkup import accessibility


def test_input_monitoring_required_only_on_macos() -> None:
    assert accessibility.input_monitoring_required("darwin") is True
    assert accessibility.input_monitoring_required("win32") is False
    assert accessibility.input_monitoring_required("linux") is False


def test_input_monitoring_trusted_true_off_macos() -> None:
    assert accessibility.is_input_monitoring_trusted("win32") is True
    assert accessibility.request_input_monitoring_trust("win32") is True


def _fake_quartz(granted: bool) -> types.ModuleType:
    module = types.ModuleType("Quartz")
    module.CGPreflightListenEventAccess = lambda: granted  # type: ignore[attr-defined]
    module.CGRequestListenEventAccess = lambda: granted  # type: ignore[attr-defined]
    return module


@pytest.mark.parametrize("granted", [True, False])
def test_is_input_monitoring_trusted_reports_preflight(granted: bool) -> None:
    with patch.dict("sys.modules", {"Quartz": _fake_quartz(granted)}):
        assert accessibility.is_input_monitoring_trusted("darwin") is granted


def test_is_input_monitoring_trusted_defaults_true_when_check_fails() -> None:
    """When the check fails, should default to True to avoid nagging."""
    quartz = types.ModuleType("Quartz")
    quartz.CGPreflightListenEventAccess = MagicMock(side_effect=RuntimeError("fail"))  # type: ignore[attr-defined]
    with patch.dict("sys.modules", {"Quartz": quartz}):
        assert accessibility.is_input_monitoring_trusted("darwin") is True


def test_request_input_monitoring_uses_native_prompt() -> None:
    with patch.dict("sys.modules", {"Quartz": _fake_quartz(False)}), patch(
        "spkup.accessibility.open_input_monitoring_settings"
    ) as mock_open:
        assert accessibility.request_input_monitoring_trust("darwin") is False
    mock_open.assert_not_called()


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
