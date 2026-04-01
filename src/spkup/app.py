import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from spkup.config import load
from spkup.hotkey import HotkeyListener


class App:
    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        self._config = load()
        self._listener = HotkeyListener(self._config.hotkey)
        self._listener.recording_started.connect(self._on_recording_started)
        self._listener.recording_stopped.connect(self._on_recording_stopped)
        self._app.aboutToQuit.connect(self._cleanup)

        icon_path = Path(__file__).parent / "resources" / "tray.png"
        icon = QIcon(str(icon_path))

        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip("spkup — Push to Talk")

        self._menu = QMenu()
        settings_action = self._menu.addAction("Settings")
        settings_action.triggered.connect(self._on_settings)
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)

        self._tray.setContextMenu(self._menu)
        self._tray.show()
        self._listener.start()

    def _on_settings(self):
        QMessageBox.information(None, "Settings", "Not implemented yet.")

    def _on_recording_started(self):
        print("Recording started", flush=True)

    def _on_recording_stopped(self):
        print("Recording stopped", flush=True)

    def _cleanup(self):
        self._listener.stop()

    def run(self) -> int:
        return self._app.exec()
