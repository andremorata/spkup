import sys
import zipfile
from pathlib import Path

import pytest

from spkup.update_checker import ReleaseAsset, UpdateInfo
from spkup.updater import (
    UpdateApplyError,
    build_update_script,
    launch_staged_update,
    validate_update_archive,
)


def _update(version: str = "1.2.3") -> UpdateInfo:
    return UpdateInfo(
        version=version,
        tag_name=f"v{version}",
        release_name=f"spkup v{version}",
        html_url=f"https://github.com/andremorata/spkup/releases/tag/v{version}",
        prerelease=True,
        published_at=None,
        asset=ReleaseAsset(
            name=f"spkup-{version}-windows-x64.zip",
            browser_download_url=f"https://example.test/spkup-{version}.zip",
            size=100,
        ),
    )


def _write_update_zip(path: Path, version: str = "1.2.3") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"spkup-{version}-windows-x64/spkup.exe", "")
        archive.writestr(f"spkup-{version}-windows-x64/lib/example.dll", "")
    return path


def test_validate_update_archive_requires_expected_exe(tmp_path) -> None:
    archive = _write_update_zip(tmp_path / "update.zip")

    assert validate_update_archive(archive, "1.2.3") == "spkup-1.2.3-windows-x64"


def test_validate_update_archive_rejects_wrong_shape(tmp_path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("spkup.exe", "")

    with pytest.raises(UpdateApplyError, match="expected executable"):
        validate_update_archive(archive, "1.2.3")


def test_build_update_script_waits_extracts_and_restarts(tmp_path) -> None:
    archive = _write_update_zip(tmp_path / "update.zip")
    executable = tmp_path / "spkup-1.2.2-windows-x64" / "spkup.exe"
    executable.parent.mkdir()
    executable.write_text("", encoding="utf-8")

    script = build_update_script(
        zip_path=archive,
        version="1.2.3",
        current_pid=1234,
        current_executable=executable,
        script_path=tmp_path / "apply-update.ps1",
    )
    text = script.read_text(encoding="utf-8")

    assert "Wait-Process -Id $pidToWait" in text
    assert "Expand-Archive -Path $zipPath" in text
    assert "Start-Process -FilePath $newExe" in text
    assert "$bundleName = 'spkup-1.2.3-windows-x64'" in text


def test_launch_staged_update_rejects_source_runs(monkeypatch, tmp_path) -> None:
    archive = _write_update_zip(tmp_path / "update.zip")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    with pytest.raises(UpdateApplyError, match="packaged Windows builds"):
        launch_staged_update(_update(), archive)
