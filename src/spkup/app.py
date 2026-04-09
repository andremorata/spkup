import logging
import sys
import threading
from typing import cast

from PyQt6.QtCore import Qt, QRect, QRectF, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from spkup.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from spkup.clipboard import copy_to_clipboard
from spkup.config import AppConfig, CONFIG_PATH, load
from spkup.hotkey import HotkeyListener
from spkup.model_manager import is_downloaded
from spkup.overlay import OverlayState, OverlayWidget
from spkup.playback_mute import PlaybackMuteController
from spkup.recorder import AudioRecorder
from spkup.sound_cues import play_cue
from spkup.transcription_history import TranscriptionHistory
from spkup.transcription_history_window import TranscriptionHistoryWindow
from spkup.transcriber import Transcriber

_log = logging.getLogger(__name__)


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


class App(QObject):
    _session_ready = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._app = cast(QApplication, QApplication.instance() or QApplication(sys.argv))
        self._app.setQuitOnLastWindowClosed(False)

        is_first_run = not CONFIG_PATH.exists()
        self._config = load()
        self._listener_active = False
        self._recording_start_pending = False
        self._recording_active = False

        # Core components
        self._recorder = AudioRecorder(max_seconds=self._config.max_recording_seconds)
        self._transcriber = Transcriber(self._config)
        self._overlay = OverlayWidget(self._config.overlay_position)
        self._playback_mute = PlaybackMuteController()
        self._session_ready.connect(self._begin_recording_session)
        self._transcription_watchdog = QTimer()
        self._transcription_watchdog.setSingleShot(True)
        self._transcription_watchdog.timeout.connect(self._on_transcription_timeout)
        self._timeout_was_cuda_retry = False
        self._transcription_history = TranscriptionHistory(max_entries=5)
        self._transcription_history_window = TranscriptionHistoryWindow()
        self._transcription_history_window.delete_requested.connect(
            self._delete_transcription_history_entry
        )
        self._transcription_history_window.copy_requested.connect(
            self._on_transcription_history_copy_requested
        )

        # Recorder → transcription pipeline
        self._recorder.recording_finished.connect(self._transcriber.transcribe)
        self._recorder.recording_error.connect(self._on_recording_error)

        # Transcription outputs
        self._transcriber.transcription_finished.connect(self._on_transcription_finished)
        self._transcriber.transcription_error.connect(self._on_transcription_error)

        # Hotkey listener (started only after a model is confirmed ready)
        self._listener = HotkeyListener(self._config.hotkey)
        self._listener.recording_started.connect(self._on_recording_started)
        self._listener.recording_stopped.connect(self._on_recording_stopped)

        self._app.aboutToQuit.connect(self._cleanup)

        # Tray icon & menu
        self._tray = QSystemTrayIcon(_make_tray_icon())
        self._tray.setToolTip("spkup — Push to Talk")

        self._menu = QMenu()
        settings_action = self._menu.addAction("Settings")
        assert settings_action is not None
        settings_action.triggered.connect(self._on_settings)
        self._menu.addSeparator()
        self._autostart_action = self._menu.addAction("Start on login")
        assert self._autostart_action is not None
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(is_autostart_enabled())
        self._autostart_action.triggered.connect(self._on_autostart_toggled)
        self._menu.addSeparator()
        history_action = self._menu.addAction("Recent transcriptions")
        assert history_action is not None
        history_action.triggered.connect(self._show_transcription_history)
        self._retry_action = cast(
            QAction, self._menu.addAction("Retry last transcription")
        )
        self._retry_action.setEnabled(False)
        self._retry_action.triggered.connect(self._on_retry_last)
        self._menu.addSeparator()
        quit_action = self._menu.addAction("Quit")
        assert quit_action is not None
        quit_action.triggered.connect(QApplication.quit)

        self._tray.setContextMenu(self._menu)
        self._tray.show()

        _log.info(
            "spkup starting (first_run=%s, model=%s)", is_first_run, self._config.model_size
        )

        if is_first_run or not is_downloaded(self._config.model_size):
            QTimer.singleShot(300, self._show_first_run_settings)
        else:
            self._listener.start()
            self._listener_active = True
            _log.info("Hotkey listener active: %s", self._config.hotkey)

    # ---------- Settings -----------------------------------------------------

    def _on_settings(self) -> None:
        from spkup.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._config)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _show_first_run_settings(self) -> None:
        from spkup.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._config, first_run=True)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self, new_config: AppConfig) -> None:
        old = self._config
        self._config = new_config

        _log.info(
            "Settings saved: model=%s device=%s hotkey=%s",
            new_config.model_size, new_config.device, new_config.hotkey,
        )

        # Restart hotkey listener if hotkey changed
        if old.hotkey != new_config.hotkey:
            if self._listener_active:
                self._listener.stop()
            self._listener = HotkeyListener(new_config.hotkey)
            self._listener.recording_started.connect(self._on_recording_started)
            self._listener.recording_stopped.connect(self._on_recording_stopped)
            if self._listener_active:
                self._listener.start()

        # Reinitialize transcriber if model / device / compute type changed
        if (
            old.model_size != new_config.model_size
            or old.device != new_config.device
            or old.compute_type != new_config.compute_type
        ):
            self._transcription_watchdog.stop()
            self._timeout_was_cuda_retry = False
            self._retry_action.setEnabled(False)
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

        # First-run: activate listener once a model is confirmed downloaded
        if not self._listener_active and is_downloaded(new_config.model_size):
            self._listener_active = True
            self._listener.start()
            _log.info("Hotkey listener activated: %s", new_config.hotkey)
            if QSystemTrayIcon.supportsMessages():
                self._tray.showMessage(
                    "spkup",
                    f"spkup is ready. Hold {new_config.hotkey} to record.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )

    # ---------- Recording lifecycle ------------------------------------------

    def _begin_recording_session(self) -> None:
        if not self._recording_start_pending:
            return

        self._recording_start_pending = False
        self._recording_active = True

        if self._config.mute_playback_while_recording:
            self._playback_mute.mute_for_recording()

        self._overlay.show_state(OverlayState.RECORDING)
        self._recorder.start()

    def _restore_playback_mute(self) -> None:
        if self._playback_mute.restore_pending:
            self._playback_mute.restore()

    def _start_transcription_watchdog(self) -> None:
        watchdog = getattr(self, "_transcription_watchdog", None)
        if watchdog is not None:
            watchdog.start(self._config.transcription_timeout_seconds * 1000)

    def _stop_transcription_watchdog(self) -> None:
        watchdog = getattr(self, "_transcription_watchdog", None)
        if watchdog is not None:
            watchdog.stop()

    def _set_retry_action_enabled(self, enabled: bool) -> None:
        retry_action = getattr(self, "_retry_action", None)
        if retry_action is not None:
            retry_action.setEnabled(enabled)

    def _on_recording_started(self) -> None:
        _log.debug("Recording started")
        self._tray.setIcon(_make_tray_icon(color="#ff4444"))

        self._stop_transcription_watchdog()
        self._timeout_was_cuda_retry = False
        self._set_retry_action_enabled(False)

        if self._config.mute_playback_while_recording:
            self._recording_start_pending = True
            threading.Thread(target=self._play_start_cue_then_begin, daemon=True).start()
            return

        self._recording_active = True
        play_cue("start")
        self._recorder.start()
        self._overlay.show_state(OverlayState.RECORDING)

    def _play_start_cue_then_begin(self) -> None:
        play_cue("start", blocking=True)
        if self._recording_start_pending:
            self._session_ready.emit()

    def _on_recording_stopped(self) -> None:
        _log.debug("Recording stopped; transcribing")
        self._tray.setIcon(_make_tray_icon(color="#ffffff"))

        if self._recording_start_pending:
            self._recording_start_pending = False
            self._overlay.show_state(OverlayState.HIDDEN)
            return

        if not self._recording_active:
            self._restore_playback_mute()
            self._overlay.show_state(OverlayState.HIDDEN)
            return

        self._recording_active = False
        self._recorder.stop()
        self._restore_playback_mute()
        self._overlay.show_state(OverlayState.TRANSCRIBING)
        self._timeout_was_cuda_retry = False
        self._start_transcription_watchdog()
        play_cue("transcribing")

    def _on_recording_error(self, msg: str) -> None:
        _log.error("Recording error: %s", msg)
        self._recording_start_pending = False
        self._recording_active = False
        self._restore_playback_mute()
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

    def _show_transcription_history(self) -> None:
        entries = self._transcription_history.list_entries()
        _log.info("Opening transcription history (%d entries)", len(entries))
        self._transcription_history_window.set_entries(entries)
        self._transcription_history_window.show_window()

    def _delete_transcription_history_entry(self, entry_id: str) -> None:
        deleted = self._transcription_history.delete(entry_id)
        _log.info(
            "Deleted transcription history entry id=%s deleted=%s",
            entry_id,
            deleted,
        )
        self._transcription_history_window.set_entries(
            self._transcription_history.list_entries()
        )

    def _on_transcription_history_copy_requested(self, text: str) -> None:
        _log.debug("Copied transcription history entry: %d chars", len(text))

    def _on_transcription_finished(self, text: str) -> None:
        self._stop_transcription_watchdog()
        _log.info("Transcription finished: %d chars", len(text))
        copy_to_clipboard(text)
        entry = self._transcription_history.add(text)
        _log.info("Added transcription history entry id=%s", entry.id)
        self._transcription_history_window.set_entries(
            self._transcription_history.list_entries()
        )
        self._set_retry_action_enabled(False)
        self._overlay.show_state(OverlayState.DONE)
        play_cue("done")

    def _on_transcription_error(self, msg: str) -> None:
        self._stop_transcription_watchdog()
        _log.error("Transcription error: %s", msg)
        self._overlay.show_state(OverlayState.ERROR)
        self._set_retry_action_enabled(self._transcriber.has_pending_retry)
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup",
                f"Transcription error: {msg}",
                QSystemTrayIcon.MessageIcon.Warning,
                3000,
            )

    def _on_transcription_timeout(self) -> None:
        device = self._config.device
        _log.error(
            "Transcription watchdog timeout after %d s (device=%s, model=%s)",
            self._config.transcription_timeout_seconds,
            device,
            self._config.model_size,
        )

        self._transcriber.cleanup_worker()

        if device != "cpu" and not self._timeout_was_cuda_retry:
            _log.info("Auto-retrying transcription on CPU after timeout")
            self._timeout_was_cuda_retry = True
            if self._transcriber.retry_last(force_cpu=True):
                self._overlay.show_state(OverlayState.TRANSCRIBING)
                self._start_transcription_watchdog()
                return

        self._timeout_was_cuda_retry = False
        self._overlay.show_state(OverlayState.ERROR)
        self._set_retry_action_enabled(self._transcriber.has_pending_retry)
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup",
                "Transcription timed out. Use 'Retry last transcription' to try again.",
                QSystemTrayIcon.MessageIcon.Warning,
                4000,
            )

    def _on_retry_last(self) -> None:
        if self._transcriber.retry_last():
            _log.info("Retrying last transcription")
            self._overlay.show_state(OverlayState.TRANSCRIBING)
            self._timeout_was_cuda_retry = False
            self._start_transcription_watchdog()
            self._set_retry_action_enabled(False)
        else:
            _log.warning("No audio available for retry")

    def _on_autostart_toggled(self, checked: bool) -> None:
        if checked:
            enable_autostart()
            _log.info("Autostart enabled")
        else:
            disable_autostart()
            _log.info("Autostart disabled")

    # ---------- Lifecycle ----------------------------------------------------

    def _cleanup(self) -> None:
        _log.info("spkup shutting down")
        self._recording_start_pending = False
        watchdog = getattr(self, "_transcription_watchdog", None)
        self._recording_active = False
        self._recorder.stop()
        transcriber = getattr(self, "_transcriber", None)
        if transcriber is not None:
            transcriber.cleanup_worker()
        self._restore_playback_mute()
        listener = getattr(self, "_listener", None)
        if listener is not None:
            listener.stop()

    def run(self) -> int:
        return self._app.exec()
