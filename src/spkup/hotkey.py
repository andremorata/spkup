from __future__ import annotations

import time

from threading import Lock

from PyQt6.QtCore import QMetaObject, QObject, Qt, pyqtSignal, pyqtSlot
from pynput import keyboard


VALID_MODIFIERS = {"ctrl", "shift", "alt"}
MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "shift": "shift",
    "shift_l": "shift",
    "shift_r": "shift",
    "alt": "alt",
    "alt_l": "alt",
    "alt_r": "alt",
    "alt_gr": "alt",
}


def parse_hotkey(hotkey_str: str) -> tuple[set[str], str]:
    stripped_hotkey = hotkey_str.strip()
    if not stripped_hotkey:
        raise ValueError("Hotkey must not be empty.")

    tokens = [token.strip().lower() for token in stripped_hotkey.split("+")]
    if any(not token for token in tokens):
        raise ValueError("Hotkey contains an empty token.")

    if len(tokens) == 1:
        trigger = tokens[0]
        if trigger in VALID_MODIFIERS:
            raise ValueError("Hotkey is missing a trigger key.")
        return set(), trigger

    modifier_tokens = tokens[:-1]
    trigger = tokens[-1]

    if trigger in VALID_MODIFIERS:
        raise ValueError("Hotkey is missing a trigger key.")

    unknown_modifiers = [token for token in modifier_tokens if token not in VALID_MODIFIERS]
    if unknown_modifiers:
        raise ValueError(f"Unknown modifier: {unknown_modifiers[0]}")

    return set(modifier_tokens), trigger


class HotkeyListener(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    _TAP_THRESHOLD = 0.3

    def __init__(self, hotkey_str: str):
        super().__init__()
        modifiers, trigger = parse_hotkey(hotkey_str)
        self._modifiers = modifiers
        self._trigger = trigger
        self._pressed_keys: set[str] = set()
        self._is_active = False
        self._toggle_mode = False
        self._press_time: float = 0.0
        self._listener: keyboard.Listener | None = None
        self._state_lock = Lock()

    def start(self) -> None:
        with self._state_lock:
            if self._listener is not None:
                return

            self._pressed_keys.clear()
            self._is_active = False
            self._toggle_mode = False
            self._press_time = 0.0
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()

    def stop(self) -> None:
        with self._state_lock:
            listener = self._listener
            self._listener = None
            self._pressed_keys.clear()
            self._is_active = False
            self._toggle_mode = False
            self._press_time = 0.0

        if listener is not None:
            listener.stop()

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        key_name = self._normalize_key(key)
        if key_name is None:
            return

        should_emit_started = False
        should_emit_stopped = False
        with self._state_lock:
            self._pressed_keys.add(key_name)
            required_keys = self._modifiers | {self._trigger}

            if self._is_active and self._toggle_mode and required_keys.issubset(self._pressed_keys):
                self._is_active = False
                self._toggle_mode = False
                should_emit_stopped = True
            elif not self._is_active and required_keys.issubset(self._pressed_keys):
                self._is_active = True
                self._toggle_mode = False
                self._press_time = time.monotonic()
                should_emit_started = True

        if should_emit_started:
            QMetaObject.invokeMethod(
                self,
                "_emit_started",
                Qt.ConnectionType.QueuedConnection,
            )
        if should_emit_stopped:
            QMetaObject.invokeMethod(
                self,
                "_emit_stopped",
                Qt.ConnectionType.QueuedConnection,
            )

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        key_name = self._normalize_key(key)
        if key_name is None:
            return

        should_emit_stopped = False
        with self._state_lock:
            if key_name == self._trigger and self._is_active and not self._toggle_mode:
                elapsed = time.monotonic() - self._press_time
                if elapsed < self._TAP_THRESHOLD:
                    self._toggle_mode = True
                else:
                    self._is_active = False
                    should_emit_stopped = True

            self._pressed_keys.discard(key_name)

        if should_emit_stopped:
            QMetaObject.invokeMethod(
                self,
                "_emit_stopped",
                Qt.ConnectionType.QueuedConnection,
            )

    @pyqtSlot()
    def _emit_started(self) -> None:
        self.recording_started.emit()

    @pyqtSlot()
    def _emit_stopped(self) -> None:
        self.recording_stopped.emit()

    def _normalize_key(self, key: keyboard.Key | keyboard.KeyCode) -> str | None:
        if getattr(key, "char", None):
            return key.char.lower()

        key_name = getattr(key, "name", None)
        if key_name is None:
            return None

        normalized_name = key_name.lower()
        return MODIFIER_ALIASES.get(normalized_name, normalized_name)
