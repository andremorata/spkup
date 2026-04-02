import os
import sys
from pathlib import Path


def is_frozen_build() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def runtime_dir() -> Path:
    if is_frozen_build():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _dll_search_dirs() -> list[Path]:
    """Return Windows DLL search directories for dev and frozen builds."""
    if sys.platform != "win32":
        return []

    candidates: list[Path] = []

    if is_frozen_build():
        candidates.append(runtime_dir())
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(Path(bundle_dir))
    else:
        for entry in sys.path:
            nvidia_root = Path(entry) / "nvidia"
            if not nvidia_root.is_dir():
                continue
            for bin_dir in nvidia_root.glob("*/bin"):
                if bin_dir.is_dir():
                    candidates.append(bin_dir)

    seen: set[Path] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _add_windows_dll_dirs() -> None:
    """Add DLL search directories so bundled CTranslate2 dependencies resolve."""
    extra: list[str] = []
    add_dll_directory = getattr(os, "add_dll_directory", None)

    for directory in _dll_search_dirs():
        extra.append(str(directory))
        if add_dll_directory is not None:
            add_dll_directory(str(directory))

    if extra:
        current_path = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join(extra + [current_path]) if current_path else os.pathsep.join(extra)


def _bootstrap() -> None:
    _add_windows_dll_dirs()

    from spkup.logging_setup import configure_logging

    configure_logging()


def main() -> int:
    _bootstrap()

    from spkup.app import App

    return App().run()


if __name__ == "__main__":
    sys.exit(main())
