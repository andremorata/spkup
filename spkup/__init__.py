"""Repo-root shim so ``python -m spkup`` runs the current worktree sources.

This repository uses a ``src/`` layout. When developers run ``python -m spkup``
from a worktree root while an editable install from another checkout also
exists, Python can resolve the installed package instead of the files being
edited. This shim executes the real package ``src/spkup`` in-place and exposes
its submodules through the normal ``spkup`` package path.
"""

from __future__ import annotations

from pathlib import Path

_REAL_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "spkup"
_REAL_INIT = _REAL_PACKAGE_DIR / "__init__.py"

__file__ = str(_REAL_INIT)
__path__ = [str(_REAL_PACKAGE_DIR)]

exec(compile(_REAL_INIT.read_text(encoding="utf-8"), __file__, "exec"), globals())
