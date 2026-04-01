import os
import sys
from pathlib import Path


def _add_nvidia_dll_dirs() -> None:
    """Add nvidia wheel DLL directories to PATH so ctranslate2 can find them.

    The nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels place their DLLs under
    site-packages/nvidia/*/bin/.  ctranslate2's C++ code calls LoadLibrary
    directly and only searches PATH, so we prepend the directories there.
    os.add_dll_directory() is also called as a belt-and-suspenders measure.
    """
    if sys.platform != "win32":
        return
    extra: list[str] = []
    for sp in sys.path:
        nvidia_root = Path(sp) / "nvidia"
        if not nvidia_root.is_dir():
            continue
        for bin_dir in nvidia_root.glob("*/bin"):
            if bin_dir.is_dir():
                extra.append(str(bin_dir))
                os.add_dll_directory(str(bin_dir))
    if extra:
        os.environ["PATH"] = os.pathsep.join(extra) + os.pathsep + os.environ.get("PATH", "")


_add_nvidia_dll_dirs()

from spkup.logging_setup import configure_logging  # noqa: E402

configure_logging()

from spkup.app import App  # noqa: E402

sys.exit(App().run())
