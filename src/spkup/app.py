import sys

from PyQt6.QtCore import Qt, QRect, QRectF
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from spkup.clipboard import copy_to_clipboard
from spkup.config import AppConfig, load
from spkup.hotkey import HotkeyListener
from spkup.overlay import OverlayState, OverlayWidget
from spkup.recorder import AudioRecorder
from spkup.transcriber import Transcriber


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
    p.drawArc(arc_rect, 0 * 16, -180 * 16)

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

        # Core components
        self._recorder = AudioRecorder(max_seconds=self._config.max_recording_seconds)
        self._transcriber = Transcriber(self._config)
        self._overlay = OverlayWidget(self._config.overlay_position)

        # Recorder → transcription pipeline
        self._recorder.recording_finished.connect(self._transcriber.transcribe)
        self._recorder.recording_error.connect(self._on_recording_error)

        # Transcription outputs
        self._transcriber.transcription_finished.connect(self._on_transcription_finished)
        self._transcriber.transcription_error.connect(self._on_transcription_error)

        # Hotkey listener
        self._listener = HotkeyListener(self._config.hotkey)
        self._listener.recording_started.connect(self._on_recording_started)
        self._listener.recording_stopped.connect(self._on_recording_stopped)

        self._app.aboutToQuit.connect(self._cleanup)

        # Tray icon & menu
        self._tray = QSystemTrayIcon(_make_tray_icon())
        self._tray.setToolTip("spkup — Push to Talk")

        self._menu = QMenu()
        settings_action = self._menu.addAction("Settings")
        settings_action.triggered.connect(self._on_settings)
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)

        self._tray.setContextMenu(self._menu)
        self._tray.show()
        self._listener.start()

    # ---------- Settings -----------------------------------------------------

    def _on_settings(self) -> None:
        from spkup.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._config)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self, new_config: AppConfig) -> None:
        old = self._config
        self._config = new_config

        # Restart hotkey listener if hotkey changed
        if old.hotkey != new_config.hotkey:
            self._listener.stop()
            self._listener = HotkeyListener(new_config.hotkey)
            self._listener.recording_started.connect(self._on_recording_started)
            self._listener.recording_stopped.connect(self._on_recording_stopped)
            self._listener.start()

        # Reinitialize transcriber if model / device / compute type changed
        if (
            old.model_size != new_config.model_size
            or old.device != new_config.device
            or old.compute_type != new_config.compute_type
        ):
            old_transcriber = self._transcriber
            self._recorder.recording_finished.disconnect(old_transcriber.transcribe)
            old_transcriber.transcription_finished.disconnect(
                self._on_transcription_finished
            )
            old_transcriber.transcription_error.disconnect(self._on_transcription_error)

            self._transcriber = Transcriber(new_config)
            self._recorder.recording_finished.connect(self._transcriber.transcribe)
            self._transcriber.transcription_finished.connect(
                self._on_transcription_finished
            )
            self._transcriber.transcription_error.connect(self._on_transcription_error)

        # Reposition overlay if corner changed
        if old.overlay_position != new_config.overlay_position:
            self._overlay._overlay_position = new_config.overlay_position
            self._overlay._reposition()

    # ---------- Recording lifecycle ------------------------------------------

    def _on_recording_started(self) -> None:
        self._tray.setIcon(_make_tray_icon(color="#ff4444"))
        self._recorder.start()
        self._overlay.show_state(OverlayState.RECORDING)

    def _on_recording_stopped(self) -> None:
        self._tray.setIcon(_make_tray_icon(color="#ffffff"))
        self._recorder.stop()
        self._overlay.show_state(OverlayState.TRANSCRIBING)

    def _on_recording_error(self, msg: str) -> None:
        self._tray.setIcon(_make_tray_icon(color="#ffffff"))
        self._overlay.show_state(OverlayState.HIDDEN)
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup",
                f"Recording error: {msg}",
                QSystemTrayIcon.MessageIcon.Warning,
                3000,
            )

    # ---------- Transcription output -----------------------------------------

    def _on_transcription_finished(self, text: str) -> None:
        copy_to_clipboard(text)
        self._overlay.show_state(OverlayState.DONE)
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup",
                text[:80],
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )

    def _on_transcription_error(self, msg: str) -> None:
        self._overlay.show_state(OverlayState.HIDDEN)
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup",
                f"Transcription error: {msg}",
                QSystemTrayIcon.MessageIcon.Warning,
                3000,
            )

    # ---------- Lifecycle ----------------------------------------------------

    def _cleanup(self) -> None:
        self._recorder.stop()
        self._listener.stop()

    def run(self) -> int:
        return self._app.exec()
