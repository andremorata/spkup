import sys
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from spkup import app as app_module

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


def test_idle_tray_icon_is_a_template_on_macos_only() -> None:
    with patch.object(app_module, "is_macos", return_value=True):
        assert app_module._make_tray_icon().isMask() is True
        assert app_module._make_tray_icon(color=app_module._RECORDING_RED).isMask() is False
    with patch.object(app_module, "is_macos", return_value=False):
        assert app_module._make_tray_icon().isMask() is False


def test_tray_icon_has_1x_and_2x_pixmaps() -> None:
    sizes = {(s.width(), s.height()) for s in app_module._make_tray_icon().availableSizes()}
    assert {(22, 22), (44, 44)} <= sizes


def test_bundled_icon_assets_exist() -> None:
    resources = app_module._APP_ICON_PATH.parent
    for name in ("icon.png", "spkup.icns", "spkup.ico"):
        assert (resources / name).stat().st_size > 0
