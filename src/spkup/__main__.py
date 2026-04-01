import os
import sys
from pathlib import Path


def _add_nvidia_dll_dirs() -> None:
    """Add nvidia wheel DLL directories to the Windows DLL search path.

    The nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels place their DLLs under
    site-packages/nvidia/*/bin/.  On Windows these are not on PATH by default,
    so ctranslate2 cannot find cublas64_12.dll.  os.add_dll_directory() fixes
    this without modifying the system PATH.
    """
    if sys.platform != "win32":
        return
    for sp in sys.path:
        nvidia_root = Path(sp) / "nvidia"
        if not nvidia_root.is_dir():
            continue
        for bin_dir in nvidia_root.glob("*/bin"):
            if bin_dir.is_dir():
                os.add_dll_directory(str(bin_dir))


_add_nvidia_dll_dirs()

from spkup.app import App  # noqa: E402

sys.exit(App().run())
