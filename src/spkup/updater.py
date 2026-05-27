from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from textwrap import dedent
import urllib.error
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

from spkup.platform_support import (
    WINDOWS_X64_TAG,
    bundle_root_name,
    supports_automatic_update_apply,
    update_staging_root,
)
from spkup.update_checker import UpdateInfo

_log = logging.getLogger(__name__)


class UpdateApplyError(RuntimeError):
    """Raised when an update cannot be staged or applied."""


def is_frozen_windows_build() -> bool:
    return supports_automatic_update_apply() and bool(getattr(sys, "frozen", False))


def update_staging_dir(version: str) -> Path:
    return update_staging_root() / version


def download_update_asset(update: UpdateInfo, destination_dir: Path | None = None) -> Path:
    target_dir = destination_dir or update_staging_dir(update.version)
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / update.asset.name
    temp_destination = destination.with_suffix(destination.suffix + ".tmp")

    request = urllib.request.Request(
        update.asset.browser_download_url,
        headers={"User-Agent": f"spkup-updater/{update.version}"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with temp_destination.open("wb") as file:
                shutil.copyfileobj(response, file)
        os.replace(temp_destination, destination)
    except (OSError, urllib.error.URLError) as exc:
        if temp_destination.exists():
            temp_destination.unlink()
        raise UpdateApplyError(f"Could not download update: {exc}") from exc

    return destination


def validate_update_archive(
    zip_path: Path,
    version: str,
    platform_tag: str = WINDOWS_X64_TAG,
) -> str:
    expected_root = bundle_root_name(version, platform_tag)
    if expected_root is None:
        raise UpdateApplyError(f"Unsupported update platform: {platform_tag}")

    expected_exe = f"{expected_root}/spkup.exe"
    if platform_tag == "macos-arm64":
        expected_exe = f"{expected_root}/spkup.app/Contents/MacOS/spkup"

    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = set()
            for raw_name in archive.namelist():
                name = raw_name.replace("\\", "/").rstrip("/")
                if not name:
                    continue
                path = PurePosixPath(name)
                parts = path.parts
                if name.startswith("/") or (parts and parts[0].endswith(":")):
                    raise UpdateApplyError(f"Archive contains unsafe absolute path: {raw_name}")
                if "." in parts or ".." in parts:
                    raise UpdateApplyError(
                        f"Archive contains unsafe directory traversal path: {raw_name}"
                    )
                if parts and parts[0] != expected_root:
                    raise UpdateApplyError(
                        f"Archive contains unexpected top-level entry outside {expected_root}: {raw_name}"
                    )
                names.add(name)
    except (OSError, zipfile.BadZipFile) as exc:
        raise UpdateApplyError(f"Downloaded update is not a valid ZIP archive: {exc}") from exc

    if expected_exe not in names:
        raise UpdateApplyError(
            f"Downloaded update does not contain expected executable: {expected_exe}"
        )

    return expected_root


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_update_script(
    *,
    zip_path: Path,
    version: str,
    current_pid: int,
    current_executable: Path,
    script_path: Path,
) -> Path:
    bundle_name = validate_update_archive(zip_path, version)
    current_dir = current_executable.resolve().parent

    script = dedent(
        f"""
        $ErrorActionPreference = 'Stop'
        $pidToWait = {current_pid}
        $zipPath = {_ps_quote(str(zip_path.resolve()))}
        $currentDir = {_ps_quote(str(current_dir))}
        $bundleName = {_ps_quote(bundle_name)}
        $parentDir = Split-Path -Parent $currentDir
        $newBundleDir = Join-Path $parentDir $bundleName
        $backupDir = Join-Path $parentDir ((Split-Path -Leaf $currentDir) + '.backup-' + (Get-Date -Format 'yyyyMMddHHmmss'))

        try {{
          Wait-Process -Id $pidToWait -ErrorAction SilentlyContinue
        }} catch {{
        }}

        if (Test-Path $newBundleDir) {{
          Remove-Item $newBundleDir -Recurse -Force
        }}

        Expand-Archive -Path $zipPath -DestinationPath $parentDir -Force
        $newExe = Join-Path $newBundleDir 'spkup.exe'
        if (-not (Test-Path $newExe)) {{
          throw "Updated executable was not found at $newExe"
        }}

        if ((Resolve-Path $currentDir).Path -ne (Resolve-Path $newBundleDir).Path) {{
          if (Test-Path $currentDir) {{
            Rename-Item -Path $currentDir -NewName (Split-Path -Leaf $backupDir)
          }}
        }}

        Start-Process -FilePath $newExe
        """
    ).strip() + "\n"

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")
    return script_path


def launch_staged_update(
    update: UpdateInfo,
    zip_path: Path,
    *,
    current_pid: int | None = None,
    current_executable: Path | None = None,
) -> Path:
    if not is_frozen_windows_build():
        raise UpdateApplyError(
            "Automatic update apply is available only in packaged Windows builds."
        )

    pid = os.getpid() if current_pid is None else current_pid
    executable = Path(sys.executable) if current_executable is None else current_executable
    script_path = update_staging_dir(update.version) / "apply-update.ps1"
    script = build_update_script(
        zip_path=zip_path,
        version=update.version,
        current_pid=pid,
        current_executable=executable,
        script_path=script_path,
    )

    _log.info("Launching staged updater script: %s", script)
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ],
            close_fds=True,
        )
    except OSError as exc:
        raise UpdateApplyError(f"Could not launch staged updater: {exc}") from exc
    return script


class UpdateDownloadWorker(QThread):
    download_finished = pyqtSignal(object, object)
    error = pyqtSignal(str)

    def __init__(self, update: UpdateInfo) -> None:
        super().__init__()
        self._update = update

    def run(self) -> None:
        try:
            zip_path = download_update_asset(self._update)
        except UpdateApplyError as exc:
            self.error.emit(str(exc))
            return

        self.download_finished.emit(self._update, zip_path)
