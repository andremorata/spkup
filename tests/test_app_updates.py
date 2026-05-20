import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from spkup.app import App
from spkup.config import AppConfig
from spkup.update_checker import ReleaseAsset, UpdateInfo

_qapp: QApplication = QApplication.instance() or QApplication(sys.argv[:1])  # type: ignore[assignment]


class _Signal:
    def __init__(self) -> None:
        self.connected = []

    def connect(self, callback) -> None:
        self.connected.append(callback)


class _FakeWorker:
    instances = []

    def __init__(self) -> None:
        self.update_available = _Signal()
        self.no_update = _Signal()
        self.error = _Signal()
        self.finished = _Signal()
        self.started = False
        _FakeWorker.instances.append(self)

    def isRunning(self) -> bool:
        return False

    def start(self) -> None:
        self.started = True


def _stub_app(config: AppConfig) -> App:
    app = QObject.__new__(App)
    QObject.__init__(app)
    app._config = config
    app._update_check_worker = None
    app._update_download_worker = None
    app._tray = MagicMock()
    return app  # type: ignore[return-value]


def _update() -> UpdateInfo:
    return UpdateInfo(
        version="0.2.4",
        tag_name="v0.2.4",
        release_name="spkup v0.2.4",
        html_url="https://github.com/andremorata/spkup/releases/tag/v0.2.4",
        prerelease=True,
        published_at=None,
        asset=ReleaseAsset(
            name="spkup-0.2.4-windows-x64.zip",
            browser_download_url="https://example.test/spkup-0.2.4.zip",
            size=1,
        ),
    )


def test_start_update_check_respects_disabled_config(monkeypatch) -> None:
    _FakeWorker.instances = []
    monkeypatch.setattr("spkup.app.UpdateCheckWorker", _FakeWorker)
    app = _stub_app(AppConfig(check_updates_on_startup=False))

    app._start_update_check_if_enabled()

    assert _FakeWorker.instances == []


def test_start_update_check_starts_worker_when_enabled(monkeypatch) -> None:
    _FakeWorker.instances = []
    monkeypatch.setattr("spkup.app.UpdateCheckWorker", _FakeWorker)
    app = _stub_app(AppConfig(check_updates_on_startup=True))

    app._start_update_check_if_enabled()

    assert len(_FakeWorker.instances) == 1
    assert _FakeWorker.instances[0].started is True


def test_update_available_in_source_run_does_not_download(monkeypatch) -> None:
    app = _stub_app(AppConfig())
    app._download_and_apply_update = MagicMock()
    monkeypatch.setattr("spkup.app.is_frozen_windows_build", lambda: False)
    monkeypatch.setattr("spkup.app.QSystemTrayIcon.supportsMessages", lambda: False)

    app._on_update_available(_update())

    app._download_and_apply_update.assert_not_called()
