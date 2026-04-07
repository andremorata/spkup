from __future__ import annotations

import logging
import sys
from typing import Any, Protocol

_log = logging.getLogger(__name__)


class PlaybackMuteBackend(Protocol):
    def get_mute(self) -> bool:
        """Return the current mute state for the default playback endpoint."""
        ...

    def set_mute(self, muted: bool) -> None:
        """Set the current mute state for the default playback endpoint."""
        ...


class PlaybackMuteController:
    """Snapshot and restore playback mute state for a recording session."""

    def __init__(self, backend: PlaybackMuteBackend | None = None) -> None:
        self._backend = backend if backend is not None else _create_default_backend()
        self._snapshot_muted: bool | None = None
        self._changed_mute = False

    @property
    def restore_pending(self) -> bool:
        return self._snapshot_muted is not None

    def mute_for_recording(self) -> bool:
        """Snapshot the current state and mute playback for the active session."""
        if self._snapshot_muted is not None:
            return True

        if self._backend is None:
            return False

        try:
            current_muted = self._backend.get_mute()
            self._snapshot_muted = current_muted
            self._changed_mute = False

            if not current_muted:
                self._backend.set_mute(True)
                self._changed_mute = True

            return True
        except Exception:
            self._snapshot_muted = None
            self._changed_mute = False
            _log.warning("Playback mute is unavailable; continuing without muting", exc_info=True)
            return False

    def restore(self) -> bool:
        """Restore the pre-recording mute state if this controller changed it."""
        if self._snapshot_muted is None:
            return False

        if self._backend is None:
            self._snapshot_muted = None
            self._changed_mute = False
            return False

        try:
            if self._changed_mute:
                self._backend.set_mute(self._snapshot_muted)

            self._snapshot_muted = None
            self._changed_mute = False
            return True
        except Exception:
            _log.warning(
                "Failed to restore playback mute state; leaving snapshot pending",
                exc_info=True,
            )
            return False


def _create_default_backend() -> PlaybackMuteBackend | None:
    if sys.platform != "win32":
        return None
    return WindowsPlaybackMuteBackend()


if sys.platform == "win32":
    import ctypes
    import uuid
    from ctypes import wintypes

    HRESULT = wintypes.LONG
    CLSCTX_INPROC_SERVER = 0x1
    E_RENDER = 0
    E_MULTIMEDIA = 1
    COINIT_APARTMENTTHREADED = 0x2
    RPC_E_CHANGED_MODE = ctypes.c_long(0x80010106).value

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

        @classmethod
        def from_string(cls, value: str) -> GUID:
            result = cls()
            raw = uuid.UUID(value).bytes_le
            result.Data1 = int.from_bytes(raw[0:4], "little")
            result.Data2 = int.from_bytes(raw[4:6], "little")
            result.Data3 = int.from_bytes(raw[6:8], "little")
            for index, item in enumerate(raw[8:]):
                result.Data4[index] = item
            return result


    QUERY_INTERFACE = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
    ADD_REF = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
    RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
    GET_DEFAULT_AUDIO_ENDPOINT = ctypes.WINFUNCTYPE(
        HRESULT,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_void_p),
    )
    ACTIVATE = ctypes.WINFUNCTYPE(
        HRESULT,
        ctypes.c_void_p,
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    )
    SET_MUTE = ctypes.WINFUNCTYPE(
        HRESULT,
        ctypes.c_void_p,
        wintypes.BOOL,
        ctypes.c_void_p,
    )
    GET_MUTE = ctypes.WINFUNCTYPE(
        HRESULT,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.BOOL),
    )


    class IUnknownVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", QUERY_INTERFACE),
            ("AddRef", ADD_REF),
            ("Release", RELEASE),
        ]


    class IUnknown(ctypes.Structure):
        _fields_ = [("lpVtbl", ctypes.POINTER(IUnknownVtbl))]


    class IMMDeviceEnumeratorVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", QUERY_INTERFACE),
            ("AddRef", ADD_REF),
            ("Release", RELEASE),
            ("EnumAudioEndpoints", ctypes.c_void_p),
            ("GetDefaultAudioEndpoint", GET_DEFAULT_AUDIO_ENDPOINT),
            ("GetDevice", ctypes.c_void_p),
            ("RegisterEndpointNotificationCallback", ctypes.c_void_p),
            ("UnregisterEndpointNotificationCallback", ctypes.c_void_p),
        ]


    class IMMDeviceEnumerator(ctypes.Structure):
        _fields_ = [("lpVtbl", ctypes.POINTER(IMMDeviceEnumeratorVtbl))]


    class IMMDeviceVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", QUERY_INTERFACE),
            ("AddRef", ADD_REF),
            ("Release", RELEASE),
            ("Activate", ACTIVATE),
            ("OpenPropertyStore", ctypes.c_void_p),
            ("GetId", ctypes.c_void_p),
            ("GetState", ctypes.c_void_p),
        ]


    class IMMDevice(ctypes.Structure):
        _fields_ = [("lpVtbl", ctypes.POINTER(IMMDeviceVtbl))]


    class IAudioEndpointVolumeVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", QUERY_INTERFACE),
            ("AddRef", ADD_REF),
            ("Release", RELEASE),
            ("RegisterControlChangeNotify", ctypes.c_void_p),
            ("UnregisterControlChangeNotify", ctypes.c_void_p),
            ("GetChannelCount", ctypes.c_void_p),
            ("SetMasterVolumeLevel", ctypes.c_void_p),
            ("SetMasterVolumeLevelScalar", ctypes.c_void_p),
            ("GetMasterVolumeLevel", ctypes.c_void_p),
            ("GetMasterVolumeLevelScalar", ctypes.c_void_p),
            ("SetChannelVolumeLevel", ctypes.c_void_p),
            ("SetChannelVolumeLevelScalar", ctypes.c_void_p),
            ("GetChannelVolumeLevel", ctypes.c_void_p),
            ("GetChannelVolumeLevelScalar", ctypes.c_void_p),
            ("SetMute", SET_MUTE),
            ("GetMute", GET_MUTE),
            ("GetVolumeStepInfo", ctypes.c_void_p),
            ("VolumeStepUp", ctypes.c_void_p),
            ("VolumeStepDown", ctypes.c_void_p),
            ("QueryHardwareSupport", ctypes.c_void_p),
            ("GetVolumeRange", ctypes.c_void_p),
        ]


    class IAudioEndpointVolume(ctypes.Structure):
        _fields_ = [("lpVtbl", ctypes.POINTER(IAudioEndpointVolumeVtbl))]


    EndpointVolumePointer = Any


    CLSID_MMDEVICE_ENUMERATOR = GUID.from_string("BCDE0395-E52F-467C-8E3D-C4579291692E")
    IID_IMMDEVICE_ENUMERATOR = GUID.from_string("A95664D2-9614-4F35-A746-DE8DB63617E6")
    IID_IAUDIO_ENDPOINT_VOLUME = GUID.from_string("5CDF2C82-841E-4546-9722-0CF74078229A")

    _ole32 = ctypes.WinDLL("ole32")
    _ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    _ole32.CoInitializeEx.restype = HRESULT
    _ole32.CoUninitialize.argtypes = []
    _ole32.CoUninitialize.restype = None
    _ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    _ole32.CoCreateInstance.restype = HRESULT


    def _check_hresult(result: int, operation: str) -> None:
        if result < 0:
            raise OSError(f"{operation} failed with HRESULT 0x{result & 0xFFFFFFFF:08X}")


    def _release(pointer: ctypes.c_void_p) -> None:
        if not pointer.value:
            return
        unknown = ctypes.cast(pointer, ctypes.POINTER(IUnknown))
        unknown.contents.lpVtbl.contents.Release(ctypes.cast(pointer, ctypes.c_void_p))


    class _EndpointVolumeHandle:
        def __init__(self) -> None:
            self._should_uninitialize = False
            self._enumerator = ctypes.c_void_p()
            self._device = ctypes.c_void_p()
            self._endpoint = ctypes.c_void_p()

        def __enter__(self) -> EndpointVolumePointer:
            init_result = _ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
            if init_result in (0, 1):
                self._should_uninitialize = True
            elif init_result != RPC_E_CHANGED_MODE:
                _check_hresult(init_result, "CoInitializeEx")

            try:
                _check_hresult(
                    _ole32.CoCreateInstance(
                        ctypes.byref(CLSID_MMDEVICE_ENUMERATOR),
                        None,
                        CLSCTX_INPROC_SERVER,
                        ctypes.byref(IID_IMMDEVICE_ENUMERATOR),
                        ctypes.byref(self._enumerator),
                    ),
                    "CoCreateInstance",
                )

                enumerator = ctypes.cast(
                    self._enumerator, ctypes.POINTER(IMMDeviceEnumerator)
                )
                _check_hresult(
                    enumerator.contents.lpVtbl.contents.GetDefaultAudioEndpoint(
                        ctypes.cast(self._enumerator, ctypes.c_void_p),
                        E_RENDER,
                        E_MULTIMEDIA,
                        ctypes.byref(self._device),
                    ),
                    "IMMDeviceEnumerator.GetDefaultAudioEndpoint",
                )

                device = ctypes.cast(self._device, ctypes.POINTER(IMMDevice))
                _check_hresult(
                    device.contents.lpVtbl.contents.Activate(
                        ctypes.cast(self._device, ctypes.c_void_p),
                        ctypes.byref(IID_IAUDIO_ENDPOINT_VOLUME),
                        CLSCTX_INPROC_SERVER,
                        None,
                        ctypes.byref(self._endpoint),
                    ),
                    "IMMDevice.Activate",
                )

                return ctypes.cast(
                    self._endpoint, ctypes.POINTER(IAudioEndpointVolume)
                )
            except Exception:
                self.close()
                raise

        def __exit__(self, exc_type, exc, tb) -> None:
            self.close()

        def close(self) -> None:
            _release(self._endpoint)
            _release(self._device)
            _release(self._enumerator)
            self._endpoint = ctypes.c_void_p()
            self._device = ctypes.c_void_p()
            self._enumerator = ctypes.c_void_p()

            if self._should_uninitialize:
                _ole32.CoUninitialize()
                self._should_uninitialize = False


    class WindowsPlaybackMuteBackend:
        """Windows Core Audio backend for the default playback endpoint."""

        def get_mute(self) -> bool:
            with _EndpointVolumeHandle() as endpoint:
                muted = wintypes.BOOL()
                _check_hresult(
                    endpoint.contents.lpVtbl.contents.GetMute(
                        ctypes.cast(endpoint, ctypes.c_void_p), ctypes.byref(muted)
                    ),
                    "IAudioEndpointVolume.GetMute",
                )
                return bool(muted.value)

        def set_mute(self, muted: bool) -> None:
            with _EndpointVolumeHandle() as endpoint:
                _check_hresult(
                    endpoint.contents.lpVtbl.contents.SetMute(
                        ctypes.cast(endpoint, ctypes.c_void_p),
                        wintypes.BOOL(bool(muted)),
                        None,
                    ),
                    "IAudioEndpointVolume.SetMute",
                )


else:

    class WindowsPlaybackMuteBackend:
        """Non-Windows stub used when the module is imported on other platforms."""

        def get_mute(self) -> bool:
            raise OSError("Windows playback mute is only available on Windows")

        def set_mute(self, muted: bool) -> None:
            raise OSError("Windows playback mute is only available on Windows")
