# ==============================================================================
# PDF Header Tool — pdf_header.py
# Version : 0.4.6
# Build   : build-2026.02.24.01
# Repo    : MondeDesPossibles/pdf-header-tool
# [CODEX] Step 4.7.6 entrypoint: bootstrap + update + UI launch only
# ==============================================================================

VERSION     = "0.4.7-beta.2"
BUILD_ID    = "build-2026.02.24.01"
GITHUB_REPO = "MondeDesPossibles/pdf-header-tool"
CHANNEL     = "beta"
_RUNNING_VERSION = VERSION

import sys
from pathlib import Path

INSTALL_DIR = Path(__file__).resolve().parent
if str(INSTALL_DIR) not in sys.path:
    # Garantit l'import de app.* dans le runtime Python Embedded Windows.
    sys.path.insert(0, str(INSTALL_DIR))

from app.constants import SIZES, TIMINGS
from app.runtime import (
    bootstrap_dependencies,
    configure_runtime,
    default_log_profile,
    install_global_exception_handler,
    log_app,
    setup_logger,
)
from app.services.sort_service import sort_paths_natural
from app.update import apply_pending_update, check_update

configure_runtime(VERSION, BUILD_ID, CHANNEL, INSTALL_DIR)

_new_version = apply_pending_update(INSTALL_DIR)
if _new_version:
    _RUNNING_VERSION = _new_version

bootstrap_dependencies()

import customtkinter as ctk

from app.ui.main_window import PDFHeaderApp

setup_logger(default_log_profile())
install_global_exception_handler()


def _collect_pdf_args(argv):
    pdf_files = []
    for arg in argv:
        path = Path(arg)
        if path.is_dir():
            pdf_files.extend(sort_paths_natural(path.glob("*.pdf")))
        elif path.suffix.lower() == ".pdf" and path.exists():
            pdf_files.append(path)
    return sort_paths_natural(pdf_files)


def main() -> None:
    print(f"PDF Header Tool version: {VERSION} (build {BUILD_ID})")
    check_update(_RUNNING_VERSION, CHANNEL, GITHUB_REPO, INSTALL_DIR, TIMINGS)
    log_app.info(f"APP_LAUNCH version={VERSION} build={BUILD_ID}")

    pdf_files = _collect_pdf_args(sys.argv[1:])
    if pdf_files:
        print(f"{len(pdf_files)} fichier(s) PDF trouvé(s).")

    root = ctk.CTk()
    root.geometry(f"{SIZES['win_w']}x{SIZES['win_h']}")
    app = PDFHeaderApp(root, pdf_files)
    root.mainloop()


if __name__ == "__main__":
    main()
