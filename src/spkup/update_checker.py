from __future__ import annotations

import dataclasses
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from spkup import __version__

_log = logging.getLogger(__name__)

RELEASES_API_URL = "https://api.github.com/repos/andremorata/spkup/releases"
_SEMVER_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_WINDOWS_ASSET_RE = re.compile(r"^spkup-(\d+\.\d+\.\d+)-windows-x64\.zip$")


@dataclasses.dataclass(frozen=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size: int | None = None


@dataclasses.dataclass(frozen=True)
class UpdateInfo:
    version: str
    tag_name: str
    release_name: str
    html_url: str
    prerelease: bool
    published_at: str | None
    asset: ReleaseAsset


class UpdateCheckError(RuntimeError):
    """Raised when update metadata cannot be retrieved or parsed."""


def parse_semver(value: str) -> tuple[int, int, int] | None:
    match = _SEMVER_TAG_RE.match(value.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_version = parse_semver(candidate)
    current_version = parse_semver(current)
    if candidate_version is None or current_version is None:
        return False
    return candidate_version > current_version


def _release_version(release: dict[str, Any]) -> tuple[str, tuple[int, int, int]] | None:
    tag_name = str(release.get("tag_name", ""))
    version = parse_semver(tag_name)
    if version is None:
        return None
    return ".".join(str(part) for part in version), version


def _select_windows_asset(
    release: dict[str, Any],
    version: str,
) -> ReleaseAsset | None:
    expected_name = f"spkup-{version}-windows-x64.zip"
    fallback: ReleaseAsset | None = None

    for raw_asset in release.get("assets", []):
        if not isinstance(raw_asset, dict):
            continue
        name = str(raw_asset.get("name", ""))
        url = str(raw_asset.get("browser_download_url", ""))
        if not name or not url:
            continue

        match = _WINDOWS_ASSET_RE.match(name)
        if match is None or match.group(1) != version:
            continue

        asset = ReleaseAsset(
            name=name,
            browser_download_url=url,
            size=raw_asset.get("size") if isinstance(raw_asset.get("size"), int) else None,
        )
        if name == expected_name:
            return asset
        fallback = asset

    return fallback


def select_available_update(
    releases: list[dict[str, Any]],
    current_version: str = __version__,
) -> UpdateInfo | None:
    candidates: list[tuple[tuple[int, int, int], UpdateInfo]] = []

    for release in releases:
        if release.get("draft"):
            continue

        version_info = _release_version(release)
        if version_info is None:
            continue
        version, version_tuple = version_info

        if not is_newer_version(version, current_version):
            continue

        asset = _select_windows_asset(release, version)
        if asset is None:
            _log.info(
                "Ignoring release %s: no matching Windows ZIP asset",
                release.get("tag_name"),
            )
            continue

        candidates.append(
            (
                version_tuple,
                UpdateInfo(
                    version=version,
                    tag_name=str(release.get("tag_name", f"v{version}")),
                    release_name=str(release.get("name") or release.get("tag_name") or version),
                    html_url=str(release.get("html_url", "")),
                    prerelease=bool(release.get("prerelease")),
                    published_at=(
                        str(release.get("published_at"))
                        if release.get("published_at") is not None
                        else None
                    ),
                    asset=asset,
                ),
            )
        )

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def fetch_available_update(
    current_version: str = __version__,
    releases_url: str = RELEASES_API_URL,
    timeout_seconds: float = 8.0,
) -> UpdateInfo | None:
    request = urllib.request.Request(
        releases_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"spkup/{current_version}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except (OSError, urllib.error.URLError) as exc:
        raise UpdateCheckError(f"Could not check for updates: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise UpdateCheckError("GitHub Releases response was not valid JSON") from exc

    if not isinstance(data, list):
        raise UpdateCheckError("GitHub Releases response had an unexpected shape")

    return select_available_update(data, current_version=current_version)


class UpdateCheckWorker(QThread):
    update_available = pyqtSignal(object)
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        current_version: str = __version__,
        releases_url: str = RELEASES_API_URL,
        timeout_seconds: float = 8.0,
    ) -> None:
        super().__init__()
        self._current_version = current_version
        self._releases_url = releases_url
        self._timeout_seconds = timeout_seconds

    def run(self) -> None:
        try:
            update = fetch_available_update(
                current_version=self._current_version,
                releases_url=self._releases_url,
                timeout_seconds=self._timeout_seconds,
            )
        except UpdateCheckError as exc:
            self.error.emit(str(exc))
            return

        if update is None:
            self.no_update.emit()
        else:
            self.update_available.emit(update)
