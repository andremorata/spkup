import json
from io import BytesIO

import pytest

from spkup.update_checker import (
    RELEASES_API_URL,
    UpdateCheckError,
    fetch_available_update,
    is_newer_version,
    parse_semver,
    select_available_update,
)


def _release(version: str, *, draft=False, prerelease=True, assets=None):
    return {
        "tag_name": f"v{version}",
        "name": f"spkup v{version}",
        "html_url": f"https://github.com/andremorata/spkup/releases/tag/v{version}",
        "draft": draft,
        "prerelease": prerelease,
        "published_at": "2026-05-20T20:00:00Z",
        "assets": assets
        if assets is not None
        else [
            {
                "name": f"spkup-{version}-windows-x64.zip",
                "browser_download_url": f"https://example.test/spkup-{version}.zip",
                "size": 123,
            }
        ],
    }


def test_parse_semver_accepts_optional_v_prefix() -> None:
    assert parse_semver("v1.2.3") == (1, 2, 3)
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("v1.2") is None


def test_is_newer_version_compares_semver_numbers() -> None:
    assert is_newer_version("0.10.0", "0.9.9") is True
    assert is_newer_version("0.2.3", "0.2.3") is False
    assert is_newer_version("0.2.2", "0.2.3") is False


def test_select_available_update_picks_highest_eligible_release() -> None:
    update = select_available_update(
        [
            _release("0.2.4", prerelease=True),
            _release("0.2.5", prerelease=False),
            _release("0.9.0", draft=True),
        ],
        current_version="0.2.3",
        platform_tag="windows-x64",
    )

    assert update is not None
    assert update.version == "0.2.5"
    assert update.asset.name == "spkup-0.2.5-windows-x64.zip"


def test_select_available_update_includes_nightly_prereleases() -> None:
    update = select_available_update(
        [_release("0.2.4", prerelease=True)],
        "0.2.3",
        platform_tag="windows-x64",
    )

    assert update is not None
    assert update.prerelease is True


def test_select_available_update_returns_none_without_matching_asset() -> None:
    update = select_available_update(
        [
            _release(
                "0.2.4",
                assets=[
                    {
                        "name": "source.zip",
                        "browser_download_url": "https://example.test/source.zip",
                    }
                ],
            )
        ],
        current_version="0.2.3",
        platform_tag="windows-x64",
    )

    assert update is None


def test_fetch_available_update_uses_github_releases_api(monkeypatch) -> None:
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps([_release("0.2.4")]).encode("utf-8")

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["user_agent"] = request.headers["User-agent"]
        return Response()

    monkeypatch.setattr("spkup.update_checker.urllib.request.urlopen", fake_urlopen)

    update = fetch_available_update(
        current_version="0.2.3",
        timeout_seconds=3,
        platform_tag="windows-x64",
    )

    assert update is not None
    assert update.version == "0.2.4"
    assert seen == {
        "url": RELEASES_API_URL,
        "timeout": 3,
        "user_agent": "spkup/0.2.3",
    }


def test_fetch_available_update_rejects_unexpected_response(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"message":"rate limited"}'

    monkeypatch.setattr(
        "spkup.update_checker.urllib.request.urlopen",
        lambda request, timeout: Response(),
    )

    with pytest.raises(UpdateCheckError, match="unexpected shape"):
        fetch_available_update(current_version="0.2.3", platform_tag="windows-x64")


def test_select_available_update_picks_macos_asset() -> None:
    update = select_available_update(
        [
            _release(
                "0.2.4",
                assets=[
                    {
                        "name": "spkup-0.2.4-windows-x64.zip",
                        "browser_download_url": "https://example.test/windows.zip",
                    },
                    {
                        "name": "spkup-0.2.4-macos-arm64.zip",
                        "browser_download_url": "https://example.test/macos.zip",
                    },
                ],
            )
        ],
        current_version="0.2.3",
        platform_tag="macos-arm64",
    )

    assert update is not None
    assert update.asset.name == "spkup-0.2.4-macos-arm64.zip"


def test_select_available_update_returns_none_without_target_platform_asset() -> None:
    assert (
        select_available_update(
            [_release("0.2.4")],
            current_version="0.2.3",
            platform_tag="linux-x64",
        )
        is None
    )
