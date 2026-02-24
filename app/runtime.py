# ==============================================================================
# app/runtime.py — Runtime bootstrap + logging shared by entrypoint and UI
# [CODEX] Step 4.7.6: extracted from pdf_header.py to keep entrypoint lightweight
# ==============================================================================

from __future__ import annotations

import logging
import logging.handlers
import platform
import sys
import time
import uuid
from functools import wraps
from pathlib import Path

_VERSION = "0.0.0"
_BUILD_ID = "build-0000.00.00.00"
_CHANNEL = "release"
_INSTALL_DIR = Path(__file__).resolve().parents[1]

_LOG_PROFILE = "simple"
_APP_LOG = _INSTALL_DIR / "pdf_header_app.log"
_ERROR_LOG = _INSTALL_DIR / "pdf_header_errors.log"
_SESSION_ID = uuid.uuid4().hex[:8]

log_app = logging.getLogger("pdf_header.app")
log_ui = logging.getLogger("pdf_header.ui")
log_pdf = logging.getLogger("pdf_header.pdf")
log_update = logging.getLogger("pdf_header.update")
log_config = logging.getLogger("pdf_header.config")
log_font = logging.getLogger("pdf_header.font")


def configure_runtime(version: str, build_id: str, channel: str, install_dir: Path) -> None:
    """Configure runtime metadata before importing heavy modules."""
    global _VERSION, _BUILD_ID, _CHANNEL, _INSTALL_DIR, _APP_LOG, _ERROR_LOG
    _VERSION = version
    _BUILD_ID = build_id
    _CHANNEL = channel
    _INSTALL_DIR = install_dir
    _APP_LOG = _INSTALL_DIR / "pdf_header_app.log"
    _ERROR_LOG = _INSTALL_DIR / "pdf_header_errors.log"


def get_version() -> str:
    return _VERSION


def get_build_id() -> str:
    return _BUILD_ID


def get_channel() -> str:
    return _CHANNEL


def get_install_dir() -> Path:
    return _INSTALL_DIR


def get_error_log_path() -> Path:
    return _ERROR_LOG


def bootstrap_dependencies() -> None:
    """Ensure runtime deps are importable before UI startup."""
    try:
        import fitz  # noqa: F401
        import customtkinter  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"Dependance manquante : {exc}")
        if sys.platform == "win32":
            print("Lancez lancer.bat pour installer les dependances automatiquement.")
        else:
            print("Installez les dependances : pip install pymupdf Pillow customtkinter")
        sys.exit(1)


def default_log_profile(channel: str | None = None) -> str:
    current_channel = channel if channel is not None else _CHANNEL
    return "medium" if current_channel == "beta" else "simple"


def setup_logger(profile: str) -> None:
    """Configure logger handlers according to selected profile."""
    global _LOG_PROFILE
    _LOG_PROFILE = profile

    root = logging.getLogger("pdf_header")
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    py_level = logging.INFO if profile == "simple" else logging.DEBUG

    try:
        fh = logging.handlers.RotatingFileHandler(
            str(_APP_LOG), maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        fh.setLevel(py_level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:
        pass

    try:
        eh = logging.handlers.RotatingFileHandler(
            str(_ERROR_LOG), maxBytes=500_000, backupCount=3, encoding="utf-8"
        )
        eh.setLevel(logging.ERROR)
        eh.setFormatter(fmt)
        root.addHandler(eh)
    except Exception:
        pass

    if profile == "full":
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(fmt)
        root.addHandler(sh)


def debug_log(msg: str, level: int = 1) -> None:
    """Compatibility wrapper kept for migration stability."""
    if level == 1:
        log_app.info(msg)
    elif level == 2:
        log_app.debug(msg)
    else:
        log_app.debug(f"[VERB] {msg}")


def log_timed(logger, label: str | None = None):
    """Decorator logging START/OK/FAILED with elapsed_ms."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = label or func.__name__
            logger.debug(f"{name} START")
            t0 = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = int((time.perf_counter() - t0) * 1000)
                logger.debug(f"{name} OK elapsed_ms={elapsed}")
                return result
            except Exception as exc:
                elapsed = int((time.perf_counter() - t0) * 1000)
                logger.error(f"{name} FAILED elapsed_ms={elapsed} error={exc}")
                raise

        return wrapper

    return decorator


def log_session_start() -> None:
    runtime = (
        "embedded"
        if ("python.exe" in sys.executable.lower() or getattr(sys, "frozen", False))
        else "system"
    )
    log_app.info(
        f"APP_START session={_SESSION_ID} version={_VERSION} build={_BUILD_ID} "
        f"channel={_CHANNEL} profile={_LOG_PROFILE} "
        f"os={platform.system()} {platform.release()} "
        f"python={sys.version.split()[0]} runtime={runtime}"
    )
    log_app.info(f"APP_DIR install_dir={_INSTALL_DIR}")


def install_global_exception_handler() -> None:
    """Install global exception handler with GUI notification fallback."""

    def _global_exception_handler(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        log_app.critical("UNCAUGHT_EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "Erreur inattendue",
                "Une erreur inattendue s'est produite.\n"
                f"Details dans :\n{_ERROR_LOG}",
            )
        except Exception:
            pass

    sys.excepthook = _global_exception_handler
