import sys

from PyQt6.QtCore import Qt, QRect, QRectF
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from spkup.config import load
from spkup.hotkey import HotkeyListener
from spkup.recorder import AudioRecorder


def _make_tray_icon(size: int = 64, color: str = "#ffffff") -> QIcon:
    """Draw a microphone icon at the given size using QPainter."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    c = QColor(color)
    p.setBrush(QBrush(c))
    p.setPen(Qt.PenStyle.NoPen)

    s = size
    # Mic capsule body (rounded rect, upper-centre)
    cap_w = s * 0.36
    cap_h = s * 0.46
    cap_x = (s - cap_w) / 2
    cap_y = s * 0.04
    p.drawRoundedRect(QRectF(cap_x, cap_y, cap_w, cap_h), cap_w / 2, cap_w / 2)

    # Arc stand — drawn as a thick pen arc
    pen = QPen(c)
    pen.setWidthF(s * 0.09)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    arc_margin = int(s * 0.16)
    arc_rect = QRect(arc_margin, int(s * 0.28), s - 2 * arc_margin, s - 2 * arc_margin)
    p.drawArc(arc_rect, 0 * 16, -180 * 16)   # bottom semicircle

    # Vertical stem from arc bottom to base
    stem_x = s / 2
    stem_top = arc_rect.center().y() + arc_rect.height() / 2
    stem_bot = s * 0.88
    p.drawLine(int(stem_x), int(stem_top), int(stem_x), int(stem_bot))

    # Horizontal base
    base_w = s * 0.44
    base_x = (s - base_w) / 2
    base_y = s * 0.88
    pen2 = QPen(c)
    pen2.setWidthF(s * 0.09)
    pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen2)
    p.drawLine(int(base_x), int(base_y), int(base_x + base_w), int(base_y))

    p.end()
    return QIcon(px)


class App:
    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        self._config = load()
        self._recorder = AudioRecorder(max_seconds=self._config.max_recording_seconds)
        self._recorder.recording_finished.connect(self._on_recording_finished)
        self._recorder.recording_error.connect(self._on_recording_error)

        self._listener = HotkeyListener(self._config.hotkey)
        self._listener.recording_started.connect(self._on_recording_started)
        self._listener.recording_stopped.connect(self._on_recording_stopped)
        self._app.aboutToQuit.connect(self._cleanup)

        icon = _make_tray_icon()

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
        self._tray.setIcon(_make_tray_icon(color="#ff4444"))
        self._recorder.start()
        print("Recording started", flush=True)

    def _on_recording_stopped(self):
        self._tray.setIcon(_make_tray_icon(color="#ffffff"))
        self._recorder.stop()
        print("Recording stopped", flush=True)

    def _on_recording_finished(self, audio):
        print(f"Recording finished: shape={audio.shape}, dtype={audio.dtype}", flush=True)

    def _on_recording_error(self, msg: str):
        self._tray.setIcon(_make_tray_icon(color="#ffffff"))
        print(f"Recording error: {msg}", flush=True)

    def _cleanup(self):
        self._recorder.stop()
        self._listener.stop()

    def run(self) -> int:
        return self._app.exec()
