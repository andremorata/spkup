import os
import sys
from pathlib import Path


def is_frozen_build() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def runtime_dir() -> Path:
    if is_frozen_build():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _nvidia_bin_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [path for path in sorted(root.glob("nvidia/*/bin")) if path.is_dir()]


def _dll_search_dirs() -> list[Path]:
    """Return Windows DLL search directories for dev and frozen builds."""
    if sys.platform != "win32":
        return []

    candidates: list[Path] = []

    if is_frozen_build():
        runtime = runtime_dir()
        candidates.append(runtime)
        candidates.extend(_nvidia_bin_dirs(runtime))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            bundle_path = Path(bundle_dir)
            candidates.append(bundle_path)
            candidates.extend(_nvidia_bin_dirs(bundle_path))
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


def _ensure_std_streams() -> None:
    """Guard against ``sys.stdout``/``sys.stderr`` being ``None``.

    PyInstaller windowed builds (``console=False``) detach the standard
    streams, so any library that writes to them (e.g. ``tqdm`` used by
    ``huggingface_hub`` during model downloads) raises
    ``AttributeError: 'NoneType' object has no attribute 'write'``.
    Redirect the missing streams to ``os.devnull`` so those writes become
    harmless no-ops.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            try:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
            except OSError:
                pass


def _bootstrap() -> None:
    _ensure_std_streams()
    _add_windows_dll_dirs()

    from spkup.logging_setup import configure_logging

    configure_logging()


def main() -> int:
    _bootstrap()

    from spkup.app import App

    return App().run()


if __name__ == "__main__":
    sys.exit(main())
