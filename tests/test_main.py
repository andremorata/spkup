from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from spkup import __main__


def test_runtime_dir_uses_source_path_when_not_frozen() -> None:
    with patch.object(__main__.sys, "frozen", False, create=True):
        assert __main__.runtime_dir() == Path(__main__.__file__).resolve().parent


def test_runtime_dir_uses_executable_parent_when_frozen() -> None:
    with patch.object(__main__.sys, "frozen", True, create=True), patch.object(
        __main__.sys, "_MEIPASS", r"C:\Apps\spkup\_internal", create=True
    ), patch.object(__main__.sys, "executable", r"C:\Apps\spkup\spkup.exe"):
        assert __main__.runtime_dir() == Path(r"C:\Apps\spkup")


def test_dll_search_dirs_scan_nvidia_bins_in_dev_mode(tmp_path: Path) -> None:
    cuda_bin = tmp_path / "site-packages" / "nvidia" / "cublas" / "bin"
    cuda_bin.mkdir(parents=True)

    with patch.object(__main__.sys, "platform", "win32"), patch.object(
        __main__.sys, "frozen", False, create=True
    ), patch.object(__main__.sys, "path", [str(tmp_path / "site-packages")]):
        assert __main__._dll_search_dirs() == [cuda_bin.resolve()]


def test_dll_search_dirs_include_bundle_dirs_in_frozen_mode(tmp_path: Path) -> None:
    runtime = tmp_path / "dist" / "spkup"
    bundle = runtime / "_internal"
    runtime.mkdir(parents=True)
    bundle.mkdir(parents=True)

    with patch.object(__main__.sys, "platform", "win32"), patch.object(
        __main__.sys, "frozen", True, create=True
    ), patch.object(__main__.sys, "_MEIPASS", str(bundle), create=True), patch.object(
        __main__.sys, "executable", str(runtime / "spkup.exe")
    ):
        assert __main__._dll_search_dirs() == [runtime.resolve(), bundle.resolve()]