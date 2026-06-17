import dataclasses
import logging
import sys
import threading
import time
from typing import cast

from PyQt6.QtCore import Qt, QRect, QRectF, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QBrush, QColor, QCursor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from spkup.accessibility import (
    is_accessibility_trusted,
    is_input_monitoring_trusted,
    open_accessibility_settings,
    open_input_monitoring_settings,
    request_accessibility_trust,
    request_input_monitoring_trust,
)
from spkup.audio_devices import describe as describe_device
from spkup.audio_devices import list_input_devices, resolve_device, spec_from_device
from spkup.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from spkup.clipboard import copy_to_clipboard
from spkup.config import AppConfig, CONFIG_PATH, load, save
from spkup.hotkey import HotkeyListener
from spkup.model_manager import is_downloaded
from spkup.overlay import OverlayState, OverlayWidget
from spkup.platform_support import is_macos, supports_autostart, supports_playback_mute
from spkup.playback_mute import PlaybackMuteController
from spkup.recorder import AudioRecorder
from spkup.sound_cues import play_cue
from spkup.transcription_history import TranscriptionHistory
from spkup.transcription_history_window import TranscriptionHistoryWindow
from spkup.transcriber import Transcriber
from spkup.update_checker import UpdateCheckWorker, UpdateInfo
from spkup.updater import (
    UpdateApplyError,
    UpdateDownloadWorker,
    is_frozen_windows_build,
    launch_staged_update,
)

_log = logging.getLogger(__name__)

# Minimum recording length (seconds) above which an empty transcription is
# treated as a likely mic problem and surfaced to the user. Shorter empties
# are silently ignored so accidental hotkey taps do not spam warnings.
EMPTY_WARNING_THRESHOLD_S = 5.0
RECORDING_COUNTDOWN_INTERVAL_MS = 100
TRIGGER_SUPPRESSION_WINDOW_S = 1.0


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
        self._transcribing_active = False
        self._start_trigger_suppression_until = 0.0
        self._recording_deadline_monotonic: float | None = None

        # Core components
        self._recorder = AudioRecorder(
            device=resolve_device(self._config.input_device),
            max_seconds=self._config.max_recording_seconds,
        )
        self._last_recording_duration: float = 0.0
        self._transcriber = Transcriber(self._config)
        self._overlay = OverlayWidget(
            self._config.overlay_position,
            recording_animation=self._config.recording_animation,
            transcribing_animation=self._config.transcribing_animation,
            done_animation=self._config.done_animation,
            error_animation=self._config.error_animation,
        )
        self._playback_mute = PlaybackMuteController()
        self._session_ready.connect(self._begin_recording_session)
        self._recording_countdown_timer = QTimer()
        self._recording_countdown_timer.timeout.connect(
            self._refresh_recording_countdown
        )
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
        self._update_check_worker: UpdateCheckWorker | None = None
        self._update_download_worker: UpdateDownloadWorker | None = None

        # Recorder → transcription pipeline
        # Duration capture runs first so _on_transcription_finished can judge
        # whether an empty result followed a substantial recording.
        self._recorder.recording_finished.connect(self._capture_recording_duration)
        self._recorder.recording_finished.connect(self._transcriber.transcribe)
        self._recorder.recording_error.connect(self._on_recording_error)

        # Transcription outputs
        self._transcriber.transcription_finished.connect(self._on_transcription_finished)
        self._transcriber.transcription_error.connect(self._on_transcription_error)

        # Hotkey listener (started only after a model is confirmed ready)
        self._listener = HotkeyListener(self._config.hotkey)
        self._listener.recording_started.connect(self._on_hotkey_recording_started)
        self._listener.recording_stopped.connect(self._on_hotkey_recording_stopped)

        self._app.aboutToQuit.connect(self._cleanup)

        # Tray icon & menu
        self._tray = QSystemTrayIcon(_make_tray_icon())
        self._tray.setToolTip("spkup — Push to Talk")
        self._tray.activated.connect(self._on_tray_activated)

        self._menu = QMenu()
        # macOS-only: the global hotkey is dead until the user grants
        # Input Monitoring. Surface a prominent, persistent entry to fix it.
        # The tray left-click still records meanwhile, so the app stays usable.
        self._input_monitoring_action: QAction | None = None
        if is_macos() and not is_input_monitoring_trusted():
            self._input_monitoring_action = self._menu.addAction(
                "⚠ Grant Input Monitoring permission for the hotkey…"
            )
            assert self._input_monitoring_action is not None
            self._input_monitoring_action.triggered.connect(self._on_open_input_monitoring)
            self._menu.addSeparator()
        settings_action = self._menu.addAction("Settings")
        assert settings_action is not None
        settings_action.triggered.connect(self._on_settings)
        self._menu.addSeparator()
        self._autostart_action: QAction | None = None
        if supports_autostart():
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
        self._mic_menu = cast(QMenu, self._menu.addMenu("Microphone"))
        self._mic_action_group: QActionGroup | None = None
        self._mic_menu.aboutToShow.connect(self._rebuild_mic_menu)
        self._menu.addSeparator()
        quit_action = self._menu.addAction("Quit")
        assert quit_action is not None
        quit_action.triggered.connect(QApplication.quit)

        # On macOS, attaching the menu via setContextMenu makes the OS pop it
        # up on *every* click, including the left-click we use to toggle
        # recording. Leave the tray menu unattached there and pop it up
        # manually on the right-click (Context) activation instead. On Windows
        # the native behavior is already left-click = trigger, right-click =
        # menu, so keep using setContextMenu.
        if not is_macos():
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

        if self._input_monitoring_action is not None:
            QTimer.singleShot(300, self._notify_input_monitoring_needed)

        QTimer.singleShot(1500, self._start_update_check_if_enabled)

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
            if is_macos():
                # pynput's macOS backend calls TSMGetInputSourceProperty via
                # CFRunLoop/CGEventTap teardown; on macOS 14+ this triggers a
                # dispatch_assert_queue SIGTRAP when stop()+start() are
                # invoked in the same process. The new hotkey is already
                # persisted by SettingsDialog._on_save, so defer activation
                # to the next launch instead of restarting the listener.
                _log.info(
                    "Hotkey changed on macOS; deferring activation to next "
                    "launch to avoid pynput in-process restart crash"
                )
                if QSystemTrayIcon.supportsMessages():
                    self._tray.showMessage(
                        "spkup",
                        (
                            f"Hotkey saved as {new_config.hotkey}. "
                            "Restart spkup for it to take effect."
                        ),
                        QSystemTrayIcon.MessageIcon.Information,
                        6000,
                    )
            else:
                if self._listener_active:
                    self._listener.stop()
                self._listener = HotkeyListener(new_config.hotkey)
                self._listener.recording_started.connect(self._on_hotkey_recording_started)
                self._listener.recording_stopped.connect(self._on_hotkey_recording_stopped)
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
        else:
            # Propagate config changes (e.g. idle-unload timeout) without rebuild.
            self._transcriber.update_config(new_config)

        # Update input device if changed
        if old.input_device != new_config.input_device:
            self._recorder.set_device(resolve_device(new_config.input_device))
            _log.info(
                "Input device changed via settings: %s",
                describe_device(new_config.input_device),
            )

        if old.max_recording_seconds != new_config.max_recording_seconds:
            self._recorder.set_max_seconds(new_config.max_recording_seconds)

        # Reposition overlay if corner changed
        if old.overlay_position != new_config.overlay_position:
            self._overlay._overlay_position = new_config.overlay_position
            self._overlay._reposition()

        # Update animation selections
        self._overlay.set_animation_key(
            OverlayState.RECORDING, new_config.recording_animation
        )
        self._overlay.set_animation_key(
            OverlayState.TRANSCRIBING, new_config.transcribing_animation
        )
        self._overlay.set_animation_key(
            OverlayState.DONE, new_config.done_animation
        )
        self._overlay.set_animation_key(
            OverlayState.ERROR, new_config.error_animation
        )

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

    # ---------- Updates ------------------------------------------------------

    def _start_update_check_if_enabled(self) -> None:
        if not self._config.check_updates_on_startup:
            _log.info("Startup update check disabled in settings")
            return

        worker = self._update_check_worker
        if worker is not None and worker.isRunning():
            return

        _log.info("Checking for application updates")
        self._update_check_worker = UpdateCheckWorker()
        self._update_check_worker.update_available.connect(self._on_update_available)
        self._update_check_worker.no_update.connect(self._on_update_check_no_update)
        self._update_check_worker.error.connect(self._on_update_check_error)
        self._update_check_worker.finished.connect(self._on_update_check_finished)
        self._update_check_worker.start()

    def _on_update_check_finished(self) -> None:
        self._update_check_worker = None

    def _on_update_check_no_update(self) -> None:
        _log.info("No application update available")

    def _on_update_check_error(self, msg: str) -> None:
        _log.warning("Update check unavailable: %s", msg)

    def _on_update_available(self, update: UpdateInfo) -> None:
        _log.info(
            "Application update available: version=%s prerelease=%s",
            update.version,
            update.prerelease,
        )

        if not is_frozen_windows_build():
            if QSystemTrayIcon.supportsMessages():
                self._tray.showMessage(
                    "spkup update available",
                    (
                        f"Version {update.version} is available as "
                        f"{update.asset.name}. Download it from GitHub Releases."
                    ),
                    QSystemTrayIcon.MessageIcon.Information,
                    6000,
                )
            return

        release_kind = "nightly pre-release" if update.prerelease else "release"
        reply = QMessageBox.question(
            None,
            "spkup update available",
            (
                f"spkup {update.version} is available as a {release_kind}.\n\n"
                "Download and apply it now? spkup will close and restart after "
                "the update is staged."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            _log.info("User declined update %s", update.version)
            return

        self._download_and_apply_update(update)

    def _download_and_apply_update(self, update: UpdateInfo) -> None:
        if self._update_download_worker is not None and self._update_download_worker.isRunning():
            return

        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup update",
                f"Downloading spkup {update.version}...",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

        self._update_download_worker = UpdateDownloadWorker(update)
        self._update_download_worker.download_finished.connect(
            self._on_update_download_finished
        )
        self._update_download_worker.error.connect(self._on_update_download_error)
        self._update_download_worker.finished.connect(self._on_update_download_worker_done)
        self._update_download_worker.start()

    def _on_update_download_worker_done(self) -> None:
        self._update_download_worker = None

    def _on_update_download_error(self, msg: str) -> None:
        _log.error("Update download failed: %s", msg)
        QMessageBox.critical(None, "spkup update failed", msg)

    def _on_update_download_finished(self, update: UpdateInfo, zip_path) -> None:
        try:
            launch_staged_update(update, zip_path)
        except UpdateApplyError as exc:
            _log.error("Update apply failed: %s", exc)
            QMessageBox.critical(None, "spkup update failed", str(exc))
            return

        QMessageBox.information(
            None,
            "spkup update",
            "The update is ready. spkup will close and restart automatically.",
        )
        QApplication.quit()

    # ---------- Microphone submenu -------------------------------------------

    def _rebuild_mic_menu(self) -> None:
        """Repopulate the tray microphone submenu.

        Called on `aboutToShow` so hot-plugged devices appear the next time
        the user opens the menu.
        """
        self._mic_menu.clear()
        self._mic_action_group = QActionGroup(self._mic_menu)
        self._mic_action_group.setExclusive(True)

        current = self._config.input_device

        default_action = self._mic_menu.addAction("System default")
        assert default_action is not None
        default_action.setCheckable(True)
        default_action.setChecked(current is None)
        default_action.triggered.connect(lambda _=False: self._on_mic_selected(None))
        self._mic_action_group.addAction(default_action)

        devices = list_input_devices()
        if not devices:
            placeholder = self._mic_menu.addAction("(no input devices found)")
            assert placeholder is not None
            placeholder.setEnabled(False)
            return

        self._mic_menu.addSeparator()
        for dev in devices:
            spec = spec_from_device(dev)
            label = f"{dev['name']} ({dev['hostapi']})"
            if dev["is_default"]:
                label += "  • default"
            action = self._mic_menu.addAction(label)
            assert action is not None
            action.setCheckable(True)
            is_current = (
                current is not None
                and current.get("name") == spec["name"]
                and current.get("hostapi") == spec["hostapi"]
            )
            action.setChecked(is_current)
            action.triggered.connect(
                lambda _checked=False, s=spec: self._on_mic_selected(s)
            )
            self._mic_action_group.addAction(action)

    def _on_mic_selected(self, spec: dict | None) -> None:
        if self._config.input_device == spec:
            return
        self._config = dataclasses.replace(self._config, input_device=spec)
        save(self._config)
        self._recorder.set_device(resolve_device(spec))
        _log.info("Input device changed: %s", describe_device(spec))

    # ---------- Recording lifecycle ------------------------------------------

    def _arm_start_trigger_suppression(self) -> None:
        self._start_trigger_suppression_until = (
            time.monotonic() + TRIGGER_SUPPRESSION_WINDOW_S
        )

    def _is_start_trigger_suppressed(self, now: float | None = None) -> bool:
        current_time = time.monotonic() if now is None else now
        return current_time < self._start_trigger_suppression_until

    def _request_recording_start(self, source: str) -> None:
        if self._transcribing_active:
            _log.info(
                "Routing %s start trigger to cancel active transcription",
                source,
            )
            self._cancel_active_transcription(source)
            return

        if self._recording_active or self._recording_start_pending:
            _log.debug(
                "Ignoring %s start trigger: recording already active=%s pending=%s",
                source,
                self._recording_active,
                self._recording_start_pending,
            )
            return

        current_time = time.monotonic()
        if self._is_start_trigger_suppressed(current_time):
            _log.debug(
                "Ignoring %s start trigger during %.2fs suppression window",
                source,
                self._start_trigger_suppression_until - current_time,
            )
            return

        self._on_recording_started()

    def _cancel_active_transcription(self, source: str) -> bool:
        """Single App-level cancel entry point for an in-progress transcription.

        Only succeeds when the app is in the transcribing state. Discards the
        active worker result, clears retained retry audio, hides the overlay,
        and arms the start-trigger suppression window so the cancel gesture
        itself does not bounce the app straight back into recording.

        Returns ``True`` when a cancel was actually performed. Future overlay
        cancel buttons should route here rather than duplicating teardown.
        """
        if not self._transcribing_active:
            _log.debug(
                "Ignoring %s cancel request: not currently transcribing",
                source,
            )
            return False

        _log.info("Cancelling active transcription (source=%s)", source)
        self._transcribing_active = False
        self._stop_transcription_watchdog()
        self._timeout_was_cuda_retry = False

        transcriber = getattr(self, "_transcriber", None)
        if transcriber is not None:
            transcriber.cancel_active()
            transcriber.clear_retry_state()

        self._set_retry_action_enabled(False)
        self._overlay.show_state(OverlayState.HIDDEN)
        self._arm_start_trigger_suppression()
        return True

    def _request_recording_stop(self, source: str) -> None:
        if not self._recording_active and not self._recording_start_pending:
            _log.debug("Ignoring %s stop trigger: recording already idle", source)
            return

        self._on_recording_stopped()

    def _start_recording_countdown(self) -> None:
        max_seconds = max(1, int(self._config.max_recording_seconds))
        self._recording_deadline_monotonic = time.monotonic() + max_seconds
        timer = getattr(self, "_recording_countdown_timer", None)
        if timer is not None:
            timer.start(RECORDING_COUNTDOWN_INTERVAL_MS)
        self._refresh_recording_countdown()

    def _refresh_recording_countdown(self) -> None:
        deadline = self._recording_deadline_monotonic
        if deadline is None:
            return

        remaining = max(0.0, deadline - time.monotonic())
        overlay = getattr(self, "_overlay", None)
        if overlay is not None:
            overlay.set_recording_countdown(
                remaining,
                self._config.max_recording_seconds,
            )

    def _stop_recording_countdown(self) -> None:
        self._recording_deadline_monotonic = None

        timer = getattr(self, "_recording_countdown_timer", None)
        if timer is not None:
            timer.stop()

        overlay = getattr(self, "_overlay", None)
        if overlay is not None:
            overlay.clear_recording_countdown()

    def _on_hotkey_recording_started(self) -> None:
        self._request_recording_start("hotkey")

    def _on_hotkey_recording_stopped(self) -> None:
        self._request_recording_stop("hotkey")

    def _notify_input_monitoring_needed(self) -> None:
        """Tell the user the hotkey needs Input Monitoring and surface the settings."""
        _log.warning(
            "Input Monitoring permission missing; global hotkey will not fire until granted"
        )
        # Open System Settings to Input Monitoring pane
        request_input_monitoring_trust()
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                "spkup needs Input Monitoring permission",
                (
                    "The global hotkey stays inactive until you allow spkup under "
                    "System Settings → Privacy & Security → Input Monitoring, then "
                    "restart spkup. You can still record by clicking the menu-bar icon."
                ),
                QSystemTrayIcon.MessageIcon.Warning,
                8000,
            )

    def _on_open_input_monitoring(self) -> None:
        request_input_monitoring_trust()
        open_input_monitoring_settings()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # On macOS the menu is not attached to the tray (see __init__), so a
        # right-click only surfaces as a Context activation — pop the menu up
        # at the cursor manually. Left-click (Trigger) toggles recording.
        if is_macos() and reason == QSystemTrayIcon.ActivationReason.Context:
            self._menu.popup(QCursor.pos())
            return

        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return

        if self._recording_active or self._recording_start_pending:
            self._request_recording_stop("tray")
            return

        self._request_recording_start("tray")

    def _capture_recording_duration(self, audio) -> None:
        try:
            self._last_recording_duration = len(audio) / 16000.0
        except Exception:
            self._last_recording_duration = 0.0

    def _begin_recording_session(self) -> None:
        if not self._recording_start_pending:
            return

        self._recording_start_pending = False
        self._recording_active = True

        if self._config.mute_playback_while_recording and supports_playback_mute():
            self._playback_mute.mute_for_recording()

        self._recorder.start()
        if not self._recording_active:
            return

        self._overlay.show_state(OverlayState.RECORDING)
        self._start_recording_countdown()

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

        if self._config.mute_playback_while_recording and supports_playback_mute():
            self._recording_start_pending = True
            threading.Thread(target=self._play_start_cue_then_begin, daemon=True).start()
            return

        self._recording_active = True
        play_cue("start")
        self._recorder.start()
        if not self._recording_active:
            return

        self._overlay.show_state(OverlayState.RECORDING)
        self._start_recording_countdown()

    def _play_start_cue_then_begin(self) -> None:
        play_cue("start", blocking=True)
        if self._recording_start_pending:
            self._session_ready.emit()

    def _on_recording_stopped(self) -> None:
        _log.debug("Recording stopped; transcribing")
        self._tray.setIcon(_make_tray_icon(color="#ffffff"))
        self._stop_recording_countdown()

        if self._recording_start_pending:
            self._recording_start_pending = False
            self._arm_start_trigger_suppression()
            self._overlay.show_state(OverlayState.HIDDEN)
            return

        if not self._recording_active:
            self._restore_playback_mute()
            self._overlay.show_state(OverlayState.HIDDEN)
            return

        self._recording_active = False
        self._recorder.stop()
        self._restore_playback_mute()
        self._transcribing_active = True
        self._overlay.show_state(OverlayState.TRANSCRIBING)
        self._timeout_was_cuda_retry = False
        self._start_transcription_watchdog()
        self._arm_start_trigger_suppression()
        play_cue("transcribing")

    def _on_recording_error(self, msg: str) -> None:
        _log.error("Recording error: %s", msg)
        self._recording_start_pending = False
        self._recording_active = False
        self._stop_recording_countdown()
        self._arm_start_trigger_suppression()
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
        self._transcribing_active = False
        self._arm_start_trigger_suppression()
        stripped = text.strip()
        duration = self._last_recording_duration
        _log.info(
            "Transcription finished: %d chars (duration=%.1fs)",
            len(stripped), duration,
        )

        if not stripped:
            # Do not overwrite clipboard with an empty string or push an
            # empty entry into history. Warn only when the recording was
            # long enough that the user plainly tried to say something.
            if duration >= EMPTY_WARNING_THRESHOLD_S:
                _log.warning(
                    "Empty transcription after %.1fs of audio — likely mic issue",
                    duration,
                )
                self._overlay.show_state(OverlayState.ERROR)
                if QSystemTrayIcon.supportsMessages():
                    self._tray.showMessage(
                        "spkup — No speech detected",
                        "Nothing was transcribed. Check that the correct "
                        "microphone is selected and not muted.",
                        QSystemTrayIcon.MessageIcon.Warning,
                        4000,
                    )
            else:
                self._overlay.show_state(OverlayState.DONE)
            self._set_retry_action_enabled(False)
            return

        copy_to_clipboard(stripped)
        entry = self._transcription_history.add(stripped)
        _log.info("Added transcription history entry id=%s", entry.id)
        self._transcription_history_window.set_entries(
            self._transcription_history.list_entries()
        )
        self._set_retry_action_enabled(False)
        self._overlay.show_state(OverlayState.DONE)
        play_cue("done")

    def _on_transcription_error(self, msg: str) -> None:
        self._stop_transcription_watchdog()
        self._transcribing_active = False
        self._arm_start_trigger_suppression()
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
                self._transcribing_active = True
                self._overlay.show_state(OverlayState.TRANSCRIBING)
                self._start_transcription_watchdog()
                return

        self._transcribing_active = False
        self._timeout_was_cuda_retry = False
        self._arm_start_trigger_suppression()
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
            self._transcribing_active = True
            self._overlay.show_state(OverlayState.TRANSCRIBING)
            self._timeout_was_cuda_retry = False
            self._start_transcription_watchdog()
            self._set_retry_action_enabled(False)
        else:
            _log.warning("No audio available for retry")

    def _on_autostart_toggled(self, checked: bool) -> None:
        if not supports_autostart():
            _log.info("Ignoring autostart toggle on unsupported platform")
            return

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
        self._transcribing_active = False
        self._stop_recording_countdown()
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
