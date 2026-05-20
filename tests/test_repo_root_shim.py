from __future__ import annotations

from pathlib import Path

import spkup
import spkup.app


def test_repo_root_shim_points_to_current_checkout() -> None:
    expected = Path(__file__).resolve().parents[1] / "src" / "spkup" / "__init__.py"

    assert Path(spkup.__file__).resolve() == expected


def test_repo_root_shim_exposes_real_package_submodules() -> None:
    expected = Path(__file__).resolve().parents[1] / "src" / "spkup" / "app.py"

    assert Path(spkup.app.__file__).resolve() == expected
