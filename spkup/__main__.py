from __future__ import annotations

from pathlib import Path

_REAL_MAIN = Path(__file__).resolve().parent.parent / "src" / "spkup" / "__main__.py"

globals_dict = {
    "__name__": "__main__",
    "__file__": str(_REAL_MAIN),
    "__package__": "spkup",
}

exec(compile(_REAL_MAIN.read_text(encoding="utf-8"), str(_REAL_MAIN), "exec"), globals_dict)
