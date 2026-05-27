import logging
import logging.handlers

from spkup.platform_support import user_log_dir

_LOG_DIR = user_log_dir()
LOG_PATH = _LOG_DIR / "spkup.log"

_FMT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"


def configure_logging() -> logging.Logger:
    """Configure root logger with rotating file logging plus stderr warnings."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(_FMT)

    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(logging.WARNING)  # keep the console quiet; full detail in file

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not root.handlers:
        root.addHandler(fh)
        root.addHandler(sh)

    return root
