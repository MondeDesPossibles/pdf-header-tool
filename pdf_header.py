# ==============================================================================
# PDF Header Tool — pdf_header.py
# Version : 0.4.6
# Build   : build-2026.02.23.01
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

VERSION     = "0.4.6.10-beta.1"
BUILD_ID    = "build-2026.02.23.01"
GITHUB_REPO = "MondeDesPossibles/pdf-header-tool"
CHANNEL     = "beta"
_RUNNING_VERSION = VERSION   # mis à jour par _apply_pending_update() si un patch est appliqué

import sys
import os
import subprocess
import json
import shutil
import tempfile
import threading
import datetime
import logging
import logging.handlers
import uuid
import time
from functools import wraps
import urllib.request
import urllib.error
from pathlib import Path

from app.update import apply_pending_update, check_update, set_staged_callback

# ---------------------------------------------------------------------------
# Bootstrap : modèle portable (Étape 4.6+)
# ---------------------------------------------------------------------------
def _get_install_dir():
    """Retourne le dossier de l'application.
    Modèle portable : toujours le dossier du script (Windows et Linux).
    La config, les logs et les polices temporaires sont stockés ici.
    """
    return Path(__file__).parent

def _bootstrap():
    """Vérifie que les dépendances sont disponibles.
    Sur Windows : installées dans site-packages/ par setup.bat (lancer.bat).
    Sur Linux   : installées manuellement via pip install pymupdf Pillow customtkinter
    """
    try:
        import fitz          # noqa: F401
        import customtkinter # noqa: F401
        from PIL import Image # noqa: F401
    except ImportError as e:
        print(f"Dépendance manquante : {e}")
        if sys.platform == "win32":
            print("Lancez lancer.bat pour installer les dépendances automatiquement.")
        else:
            print("Installez les dépendances : pip install pymupdf Pillow customtkinter")
        sys.exit(1)

_new_v = apply_pending_update(_get_install_dir())
if _new_v:
    _RUNNING_VERSION = _new_v
_bootstrap()

# ---------------------------------------------------------------------------
# Imports (disponibles après bootstrap)
# ---------------------------------------------------------------------------
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import customtkinter as ctk
from PIL import Image, ImageTk
import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Chemins et config
# ---------------------------------------------------------------------------
INSTALL_DIR = _get_install_dir()
CONFIG_FILE = INSTALL_DIR / "pdf_header_config.json"

from app.constants import (
    COLORS, SIZES, TIMINGS,
    BUILTIN_FONTS, PRIORITY_FONTS,
    POSITION_PRESETS, PRESET_LABELS,
    DATE_FORMATS, DATE_SOURCE_DISPLAY, DATE_SOURCE_INTERNAL,
    _HIDDEN_UI_FEATURES,
)
from app.config import DEFAULT_CONFIG, load_config, save_config
from app.services.font_service import (
    hex_to_rgb_float, _get_font_dirs, _find_priority_fonts, _get_fitz_font_args,
)
from app.services.layout_service import (
    canvas_to_ratio, ratio_to_canvas, ratio_to_pdf_pt, recalc_ratio_from_preset,
)
from app.services.pdf_service import insert_header


# ---------------------------------------------------------------------------
# Système de logs multi-niveaux (Étape 4.6.3)
# Profils : "simple" (prod) | "medium" (beta/support) | "full" (dev)
# ---------------------------------------------------------------------------
_LOG_PROFILE = "simple"
_APP_LOG     = INSTALL_DIR / "pdf_header_app.log"
_ERROR_LOG   = INSTALL_DIR / "pdf_header_errors.log"
_SESSION_ID  = uuid.uuid4().hex[:8]


def _default_log_profile() -> str:
    """Profil par défaut selon le canal de distribution."""
    if CHANNEL == "beta":
        return "medium"
    return "simple"


def _setup_logger(profile: str) -> None:
    """Configure le logger selon le profil demandé. Peut être rappelé après chargement config."""
    global _LOG_PROFILE
    _LOG_PROFILE = profile
    root = logging.getLogger("pdf_header")
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler app.log — INFO pour "simple", DEBUG pour "medium"/"full"
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

    # Handler error.log — ERROR+ toujours actif, indépendant du profil
    try:
        eh = logging.handlers.RotatingFileHandler(
            str(_ERROR_LOG), maxBytes=500_000, backupCount=3, encoding="utf-8"
        )
        eh.setLevel(logging.ERROR)
        eh.setFormatter(fmt)
        root.addHandler(eh)
    except Exception:
        pass

    # Handler stderr uniquement en profil "full" (dev)
    if profile == "full":
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(fmt)
        root.addHandler(sh)


# Sous-loggers par domaine — réutilisables tels quels lors de la migration app/ (Étape 4.7)
log_app    = logging.getLogger("pdf_header.app")    # lifecycle, démarrage
log_ui     = logging.getLogger("pdf_header.ui")     # interactions utilisateur
log_pdf    = logging.getLogger("pdf_header.pdf")    # opérations PyMuPDF
log_update = logging.getLogger("pdf_header.update") # système de mise à jour
log_config = logging.getLogger("pdf_header.config") # chargement/sauvegarde config
log_font   = logging.getLogger("pdf_header.font")   # découverte des polices


def _debug_log(msg: str, level: int = 1) -> None:
    """Wrapper rétrocompatible. level: 1=INFO (simple+), 2=DEBUG (medium+), 3=DEBUG [VERB] (full).
    À migrer vers les domain loggers lors du refactor 4.7.
    """
    if level == 1:
        log_app.info(msg)
    elif level == 2:
        log_app.debug(msg)
    else:
        log_app.debug(f"[VERB] {msg}")


def _log_timed(logger, label: str = None):
    """Décorateur : log début + fin + elapsed_ms. Actif uniquement en medium/full (DEBUG)."""
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
            except Exception as e:
                elapsed = int((time.perf_counter() - t0) * 1000)
                logger.error(f"{name} FAILED elapsed_ms={elapsed} error={e}")
                raise
        return wrapper
    return decorator


def _log_session_start() -> None:
    """Enregistre le contexte complet de la session — première entrée utile pour le support."""
    import platform
    runtime = (
        "embedded"
        if ("python.exe" in sys.executable.lower() or getattr(sys, "frozen", False))
        else "system"
    )
    log_app.info(
        f"APP_START session={_SESSION_ID} version={VERSION} build={BUILD_ID} "
        f"channel={CHANNEL} profile={_LOG_PROFILE} "
        f"os={platform.system()} {platform.release()} "
        f"python={sys.version.split()[0]} runtime={runtime}"
    )
    log_app.info(f"APP_DIR install_dir={INSTALL_DIR}")


def _global_exception_handler(exc_type, exc_value, exc_tb) -> None:
    """Capture les exceptions non gérées — log dans error.log + message utilisateur sobre."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log_app.critical("UNCAUGHT_EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
    try:
        messagebox.showerror(
            "Erreur inattendue",
            f"Une erreur inattendue s'est produite.\n"
            f"Détails dans :\n{_ERROR_LOG}"
        )
    except Exception:
        pass


sys.excepthook = _global_exception_handler
_setup_logger(_default_log_profile())



# ---------------------------------------------------------------------------
# Thème CustomTkinter
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Application principale
# ---------------------------------------------------------------------------
class PDFHeaderApp:
    def __init__(self, root, pdf_files=None):
        """Initialise l'état de l'app, charge la config, les polices système, construit l'UI.
        Charge le premier PDF si passé en argument, sinon affiche l'écran d'accueil.
        """
        self.root      = root
        self.pdf_files = list(pdf_files) if pdf_files else []
        self.idx       = 0
        self.cfg       = load_config(INSTALL_DIR)

        _setup_logger(self.cfg.get("log_profile", _default_log_profile()))
        _log_session_start()

        # État courant
        self.doc           = None
        self.tk_img        = None
        self.scale         = 1.0
        self.img_offset_x  = 0
        self.img_offset_y  = 0
        self.page_w_pt     = 595.0   # A4 par défaut
        self.page_h_pt     = 842.0
        self.page_w_px     = 1
        self.page_h_px     = 1

        # Position en ratio (0-1)
        self.pos_ratio_x   = self.cfg.get("last_x_ratio", 0.85)
        self.pos_ratio_y   = self.cfg.get("last_y_ratio", 0.03)

        # Preset de position courant
        self.preset_position = self.cfg.get("preset_position", "tr")

        # Polices système disponibles (chargées avant _build_ui)
        self._system_fonts = {}
        self._load_system_fonts()

        self.file_states = {}
        self._build_ui()
        self.root.update_idletasks()

        set_staged_callback(lambda v: self.root.after(0, lambda: self._show_update_notice(v)))

        if self.pdf_files:
            self.file_states = {i: "non_traite" for i in range(len(self.pdf_files))}
            self._populate_file_panel()
            self._load_pdf()
        else:
            self._show_welcome_screen()

    # ---------------------------------------------------------------- Fonts ---

    def _load_system_fonts(self):
        """Charge les polices système prioritaires disponibles."""
        self._system_fonts = _find_priority_fonts()
        log_font.debug(f"FONT_SCAN_DONE count={len(self._system_fonts)} fonts={list(self._system_fonts.keys())}")

    # ------------------------------------------------------------------ UI ---

    def _show_update_notice(self, version: str):
        """Affiche une messagebox informant qu'une mise à jour est disponible.
        Appelée via _update_staged_callback depuis _check_update_thread (thread daemon).
        """
        self.lbl_update.configure(text=f"  Mise a jour v{version} disponible — relancez l'app  ")
        self.lbl_update.pack(side="right", padx=8, pady=6)

    def _build_ui(self):
        """Construit la fenêtre principale : topbar + corps (sidebar + canvas + panneau fichiers) + bottombar.
        Appelle _build_sidebar(), _build_file_panel(). Lie les événements souris au canvas.
        """
        self.root.title("PDF Header Tool")
        self.root.configure(fg_color=COLORS["bg_dark"])
        self.root.minsize(SIZES["win_min_w"], SIZES["win_min_h"])

        # ── Topbar ──
        topbar = ctk.CTkFrame(self.root, fg_color=COLORS["bg_topbar"], height=SIZES["topbar_h"], corner_radius=0)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="PDF HEADER TOOL",
                     fg_color="transparent", text_color=COLORS["accent_red"],
                     font=("Courier New", 14, "bold")).pack(side="left", padx=14)

        ctk.CTkLabel(topbar, text=f"v{VERSION}",
                     fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Courier New", 11)).pack(side="left", padx=(0, 10))

        self.lbl_update = ctk.CTkLabel(topbar, text="",
                                       fg_color=COLORS["badge_bg"], text_color=COLORS["accent_red"],
                                       font=("Courier New", 11), corner_radius=4)
        # Pas de pack() ici — affiché par _show_update_notice() si mise à jour disponible

        self.lbl_filename = ctk.CTkLabel(topbar, text="",
                                         fg_color=COLORS["badge_bg"], text_color=COLORS["accent_blue"],
                                         font=("Courier New", 11), corner_radius=4)
        self.lbl_filename.pack(side="left", padx=8, pady=6)

        self.lbl_progress = ctk.CTkLabel(topbar, text="",
                                         fg_color=COLORS["badge_bg"], text_color=COLORS["text_secondary"],
                                         font=("Courier New", 11), corner_radius=4)
        self.lbl_progress.pack(side="right", padx=14, pady=6)

        # ── Corps ──
        body = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"], corner_radius=0)
        body.pack(fill="both", expand=True)

        # ── Sidebar (outer frame fixe + inner scrollable) ──
        sidebar_outer = ctk.CTkFrame(body, fg_color=COLORS["bg_sidebar"], width=SIZES["sidebar_w"], corner_radius=0)
        sidebar_outer.pack(side="left", fill="y")
        sidebar_outer.pack_propagate(False)

        self._sidebar_interactive = []

        sidebar_scroll = ctk.CTkScrollableFrame(
            sidebar_outer, fg_color=COLORS["bg_sidebar"], corner_radius=0,
            scrollbar_button_color=COLORS["input_border"],
            scrollbar_button_hover_color=COLORS["input_hover"]
        )
        sidebar_scroll.pack(fill="both", expand=True)
        self._build_sidebar(sidebar_scroll)

        # ── Panneau fichiers (droit) ──
        self.file_panel = ctk.CTkFrame(body, fg_color=COLORS["bg_file_panel"], width=SIZES["file_panel_w"], corner_radius=0)
        self.file_panel.pack(side="right", fill="y")
        self.file_panel.pack_propagate(False)
        self._build_file_panel(self.file_panel)

        # ── Canvas ──
        self.canvas_frame = ctk.CTkFrame(body, fg_color=COLORS["bg_canvas"], corner_radius=0)
        self.canvas_frame.pack(side="left", fill="both", expand=True)

        self.hint_lbl = ctk.CTkLabel(
            self.canvas_frame,
            text="Cliquez sur la page pour positionner l'en-tête",
            fg_color=COLORS["bg_topbar"], text_color=COLORS["text_tertiary"],
            font=("Segoe UI", 11), corner_radius=0
        )
        self.hint_lbl.pack(side="top", pady=8, fill="x")

        self.canvas = tk.Canvas(self.canvas_frame, bg=COLORS["bg_canvas"],
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>",   self._on_motion)
        self.canvas.bind("<Configure>", lambda e: self._render_preview())

        # ── Bottombar ──
        bottom = ctk.CTkFrame(self.root, fg_color=COLORS["bg_topbar"], height=SIZES["bottombar_h"], corner_radius=0)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        self.lbl_coords = ctk.CTkLabel(bottom, text="x: — pts  ·  y: — pts",
                                       fg_color="transparent", text_color=COLORS["text_dim"],
                                       font=("Courier New", 11))
        self.lbl_coords.pack(side="left", padx=14)

        self.btn_apply = ctk.CTkButton(bottom, text="✓  Appliquer",
                                  fg_color=COLORS["accent_green"], text_color=COLORS["btn_apply_text"],
                                  hover_color=COLORS["btn_apply_hover"],
                                  font=("Segoe UI", 11, "bold"),
                                  command=self._apply)
        self.btn_apply.pack(side="right", padx=10, pady=8)

        self.btn_skip = ctk.CTkButton(bottom, text="→  Passer",
                                 fg_color=COLORS["input_bg"], text_color=COLORS["text_secondary"],
                                 hover_color=COLORS["input_border"],
                                 font=("Segoe UI", 11),
                                 command=self._skip)
        self.btn_skip.pack(side="right", padx=4, pady=8)

    def _section(self, parent, label):
        """Crée un header de section ALLCAPS dans la sidebar.
        Retourne le CTkLabel créé (utilisé comme ref_widget pour pack(after=...)).
        """
        ctk.CTkLabel(parent, text=label,
                     fg_color="transparent", text_color=COLORS["text_placeholder"],
                     font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkFrame(parent, fg_color=COLORS["input_border"], height=1,
                     corner_radius=0).pack(fill="x", padx=14)

    def _build_sidebar(self, parent):
        """Construit les sections de la sidebar dans un CTkScrollableFrame.
        Respecte _HIDDEN_UI_FEATURES : certaines sections sont omises en v0.4.x.
        """
        cfg = self.cfg

        # ═══════════════════════════════════════════════════════════════
        # TEXTE DE L'EN-TÊTE
        # ═══════════════════════════════════════════════════════════════
        self._section(parent, "TEXTE DE L'EN-TÊTE")

        # Nom du fichier (sans .pdf)
        self.var_use_filename = tk.BooleanVar(value=cfg.get("use_filename", True))
        cb_fn = ctk.CTkCheckBox(parent, text="Nom du fichier (sans .pdf)",
                                variable=self.var_use_filename,
                                text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                command=self._on_text_change)
        cb_fn.pack(anchor="w", padx=14, pady=(6, 2))
        self._sidebar_interactive.append(cb_fn)

        # Texte personnalisé
        self.var_use_custom = tk.BooleanVar(value=cfg.get("use_custom", False))
        cb_cust = ctk.CTkCheckBox(parent, text="Texte personnalisé",
                                  variable=self.var_use_custom,
                                  text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                  command=self._on_use_custom_change)
        cb_cust.pack(anchor="w", padx=14, pady=2)
        self._sidebar_interactive.append(cb_cust)

        self.var_custom_text = tk.StringVar(value=cfg.get("custom_text", ""))
        self.entry_custom = ctk.CTkEntry(parent, textvariable=self.var_custom_text,
                              placeholder_text="ex: Société XYZ",
                              placeholder_text_color=COLORS["text_placeholder"],
                              fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                              border_color=COLORS["input_border"], font=("Courier New", 11))
        self.entry_custom.pack(fill="x", padx=28, pady=(1, 4))
        self._sidebar_interactive.append(self.entry_custom)
        self.var_custom_text.trace_add("write", lambda *_: self._on_text_change())

        # Préfixe
        self.var_use_prefix = tk.BooleanVar(value=cfg.get("use_prefix", False))
        cb_pfx = ctk.CTkCheckBox(parent, text="Préfixe",
                                  variable=self.var_use_prefix,
                                  text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                  command=self._on_text_change)
        cb_pfx.pack(anchor="w", padx=14, pady=(4, 1))
        self._sidebar_interactive.append(cb_pfx)

        self.var_prefix_text = tk.StringVar(value=cfg.get("prefix_text", ""))
        entry_pfx = ctk.CTkEntry(parent, textvariable=self.var_prefix_text,
                      placeholder_text="ex: CONFIDENTIEL –",
                      placeholder_text_color=COLORS["text_placeholder"],
                      fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                      border_color=COLORS["input_border"], font=("Courier New", 11))
        entry_pfx.pack(fill="x", padx=28, pady=(1, 4))
        self._sidebar_interactive.append(entry_pfx)
        self.var_prefix_text.trace_add("write", lambda *_: self._on_text_change())

        # Suffixe
        self.var_use_suffix = tk.BooleanVar(value=cfg.get("use_suffix", False))
        cb_sfx = ctk.CTkCheckBox(parent, text="Suffixe",
                                  variable=self.var_use_suffix,
                                  text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                  command=self._on_text_change)
        cb_sfx.pack(anchor="w", padx=14, pady=(4, 1))
        self._sidebar_interactive.append(cb_sfx)

        self.var_suffix_text = tk.StringVar(value=cfg.get("suffix_text", ""))
        entry_sfx = ctk.CTkEntry(parent, textvariable=self.var_suffix_text,
                      placeholder_text="ex: – v2",
                      placeholder_text_color=COLORS["text_placeholder"],
                      fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                      border_color=COLORS["input_border"], font=("Courier New", 11))
        entry_sfx.pack(fill="x", padx=28, pady=(1, 4))
        self._sidebar_interactive.append(entry_sfx)
        self.var_suffix_text.trace_add("write", lambda *_: self._on_text_change())

        # ═══════════════════════════════════════════════════════════════
        # DATE
        # ═══════════════════════════════════════════════════════════════
        self._section(parent, "DATE")

        self.var_use_date = tk.BooleanVar(value=cfg.get("use_date", False))
        self._cb_date = ctk.CTkCheckBox(parent, text="Inclure la date",
                                        variable=self.var_use_date,
                                        text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                        command=self._on_date_toggle)
        self._cb_date.pack(anchor="w", padx=14, pady=(6, 4))
        self._sidebar_interactive.append(self._cb_date)

        # Options date (affichées/masquées selon checkbox)
        self._date_options_frame = ctk.CTkFrame(parent, fg_color="transparent")

        row_dp = ctk.CTkFrame(self._date_options_frame, fg_color="transparent")
        row_dp.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_dp, text="Position", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
        self.var_date_position = tk.StringVar(value=cfg.get("date_position", "suffix"))
        opt_dp = ctk.CTkOptionMenu(row_dp, values=["suffix", "prefix"],
                                   variable=self.var_date_position,
                                   fg_color=COLORS["input_bg"], button_color=COLORS["input_border"],
                                   button_hover_color=COLORS["input_hover"], text_color=COLORS["text_primary"],
                                   font=("Segoe UI", 11), width=110,
                                   command=lambda _: self._on_text_change())
        opt_dp.pack(side="left", padx=4)
        self._sidebar_interactive.append(opt_dp)

        row_ds = ctk.CTkFrame(self._date_options_frame, fg_color="transparent")
        row_ds.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_ds, text="Source", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
        _ds_display = DATE_SOURCE_DISPLAY.get(cfg.get("date_source", "today"), "Date du jour")
        self.var_date_source = tk.StringVar(value=_ds_display)
        opt_ds = ctk.CTkOptionMenu(row_ds, values=list(DATE_SOURCE_DISPLAY.values()),
                                   variable=self.var_date_source,
                                   fg_color=COLORS["input_bg"], button_color=COLORS["input_border"],
                                   button_hover_color=COLORS["input_hover"], text_color=COLORS["text_primary"],
                                   font=("Segoe UI", 11), width=110,
                                   command=lambda _: self._on_text_change())
        opt_ds.pack(side="left", padx=4)
        self._sidebar_interactive.append(opt_ds)

        row_df = ctk.CTkFrame(self._date_options_frame, fg_color="transparent")
        row_df.pack(fill="x", padx=10, pady=(2, 6))
        ctk.CTkLabel(row_df, text="Format", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
        self._date_format_map = {f"{fmt}  ({ex})": fmt for fmt, ex in DATE_FORMATS}
        date_fmt_labels = list(self._date_format_map.keys())
        current_fmt = cfg.get("date_format", "%d/%m/%Y")
        current_fmt_label = next(
            (d for d, f in self._date_format_map.items() if f == current_fmt),
            date_fmt_labels[0]
        )
        self.var_date_format = tk.StringVar(value=current_fmt)
        opt_df = ctk.CTkOptionMenu(row_df, values=date_fmt_labels,
                                   fg_color=COLORS["input_bg"], button_color=COLORS["input_border"],
                                   button_hover_color=COLORS["input_hover"], text_color=COLORS["text_primary"],
                                   font=("Segoe UI", 9), width=185,
                                   command=self._on_date_format_change)
        opt_df.set(current_fmt_label)
        opt_df.pack(side="left", padx=4)
        self._sidebar_interactive.append(opt_df)

        # ═══════════════════════════════════════════════════════════════
        # TYPOGRAPHIE
        # ═══════════════════════════════════════════════════════════════
        self._section(parent, "TYPOGRAPHIE")

        # Police
        row_font = ctk.CTkFrame(parent, fg_color="transparent")
        row_font.pack(fill="x", padx=14, pady=(6, 2))
        ctk.CTkLabel(row_font, text="Police", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 11), width=52, anchor="w").pack(side="left")
        all_font_names = list(BUILTIN_FONTS.keys()) + list(self._system_fonts.keys())
        current_family = cfg.get("font_family", "Courier")
        if current_family not in all_font_names:
            current_family = "Courier"
        self.var_font_family = tk.StringVar(value=current_family)
        opt_font = ctk.CTkOptionMenu(row_font, values=all_font_names,
                                     variable=self.var_font_family,
                                     fg_color=COLORS["input_bg"], button_color=COLORS["input_border"],
                                     button_hover_color=COLORS["input_hover"], text_color=COLORS["text_primary"],
                                     font=("Segoe UI", 11), width=155,
                                     command=self._on_font_change)
        opt_font.pack(side="left", padx=4)
        self._sidebar_interactive.append(opt_font)

        # Taille
        size_row = ctk.CTkFrame(parent, fg_color="transparent")
        size_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(size_row, text="Taille", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 11), width=52, anchor="w").pack(side="left")
        btn_minus = ctk.CTkButton(size_row, text="−", width=30, height=26,
                                  fg_color=COLORS["input_bg"], hover_color=COLORS["input_border"],
                                  text_color=COLORS["text_primary"],
                                  command=lambda: self._change_size(-1))
        btn_minus.pack(side="left")
        self._sidebar_interactive.append(btn_minus)
        self.var_size = tk.IntVar(value=cfg.get("font_size", 8))
        size_entry = ctk.CTkEntry(size_row, textvariable=self.var_size,
                                  width=46, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                  border_color=COLORS["input_border"], font=("Courier New", 11))
        size_entry.pack(side="left", padx=2)
        self._sidebar_interactive.append(size_entry)
        btn_plus = ctk.CTkButton(size_row, text="+", width=30, height=26,
                                 fg_color=COLORS["input_bg"], hover_color=COLORS["input_border"],
                                 text_color=COLORS["text_primary"],
                                 command=lambda: self._change_size(1))
        btn_plus.pack(side="left", padx=(2, 0))
        self._sidebar_interactive.append(btn_plus)
        ctk.CTkLabel(size_row, text="pts", fg_color="transparent", text_color=COLORS["text_unit"],
                     font=("Segoe UI", 11)).pack(side="left", padx=4)

        # Couleur texte
        color_row = ctk.CTkFrame(parent, fg_color="transparent")
        color_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(color_row, text="Couleur", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 11), width=52, anchor="w").pack(side="left")
        self.color_swatch = tk.Canvas(color_row, width=26, height=18,
                                      bg=cfg["color_hex"],
                                      highlightthickness=0, cursor="hand2")
        self.color_swatch.pack(side="left", padx=4)
        self.lbl_color_hex = ctk.CTkLabel(color_row, text=cfg["color_hex"],
                                          fg_color="transparent", text_color=COLORS["text_tertiary"],
                                          font=("Courier New", 11))
        self.lbl_color_hex.pack(side="left", padx=4)
        self.color_swatch.bind("<Button-1>", self._pick_color)

        # Style : Gras / Italique / Souligné
        style_row = ctk.CTkFrame(parent, fg_color="transparent")
        style_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(style_row, text="Style", fg_color="transparent", text_color=COLORS["text_secondary"],
                     font=("Segoe UI", 11), width=52, anchor="w").pack(side="left")
        self.var_bold      = tk.BooleanVar(value=cfg.get("bold",      False))
        self.var_italic    = tk.BooleanVar(value=cfg.get("italic",    False))
        self.var_underline = tk.BooleanVar(value=cfg.get("underline", False))
        for lbl, var in [("G", self.var_bold), ("I", self.var_italic), ("S", self.var_underline)]:
            btn_style = ctk.CTkCheckBox(style_row, text=lbl, variable=var,
                                        width=42, checkbox_width=20, checkbox_height=20,
                                        text_color=COLORS["text_primary"], font=("Segoe UI", 11, "bold"),
                                        command=self._on_text_change)
            btn_style.pack(side="left", padx=3)
            self._sidebar_interactive.append(btn_style)

        # Espacement lettres et lignes — variables toujours créées (utilisées dans _apply)
        self.var_letter_spacing = tk.StringVar(value=str(cfg.get("letter_spacing", 0.0)))
        self.var_line_spacing   = tk.StringVar(value=str(cfg.get("line_spacing", 1.2)))
        if "letter_spacing" not in _HIDDEN_UI_FEATURES:
            row_lsp = ctk.CTkFrame(parent, fg_color="transparent")
            row_lsp.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row_lsp, text="Esp. lettres", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=80, anchor="w").pack(side="left")
            entry_lsp = ctk.CTkEntry(row_lsp, textvariable=self.var_letter_spacing,
                                     width=55, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                     border_color=COLORS["input_border"], font=("Courier New", 11))
            entry_lsp.pack(side="left", padx=4)
            self._sidebar_interactive.append(entry_lsp)
            ctk.CTkLabel(row_lsp, text="pts", fg_color="transparent", text_color=COLORS["text_unit"],
                         font=("Segoe UI", 10)).pack(side="left")
        if "line_spacing" not in _HIDDEN_UI_FEATURES:
            row_line = ctk.CTkFrame(parent, fg_color="transparent")
            row_line.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row_line, text="Esp. lignes", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=80, anchor="w").pack(side="left")
            entry_line = ctk.CTkEntry(row_line, textvariable=self.var_line_spacing,
                                      width=55, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                      border_color=COLORS["input_border"], font=("Courier New", 11))
            entry_line.pack(side="left", padx=4)
            self._sidebar_interactive.append(entry_line)
            ctk.CTkLabel(row_line, text="×", fg_color="transparent", text_color=COLORS["text_unit"],
                         font=("Segoe UI", 10)).pack(side="left")

        # ═══════════════════════════════════════════════════════════════
        # POSITION
        # ═══════════════════════════════════════════════════════════════
        self._section(parent, "POSITION")

        # Grille preset et marges — variables toujours créées (utilisées dans _recalc_ratio_from_preset)
        self._preset_buttons = {}
        self.var_margin_x = tk.StringVar(value=str(cfg.get("margin_x_pt", 20.0)))
        self.var_margin_y = tk.StringVar(value=str(cfg.get("margin_y_pt", 20.0)))
        self.var_margin_x.trace_add("write", lambda *_: self._on_margins_change())
        self.var_margin_y.trace_add("write", lambda *_: self._on_margins_change())
        if "position_grid" not in _HIDDEN_UI_FEATURES:
            ctk.CTkLabel(parent, text="Preset",
                         fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), anchor="w").pack(anchor="w", padx=14, pady=(6, 2))
            grid_frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_grid"], corner_radius=6)
            grid_frame.pack(padx=20, pady=(0, 6), anchor="w")
            for key, (row_n, col_n) in POSITION_PRESETS.items():
                btn_preset = ctk.CTkButton(grid_frame, text=PRESET_LABELS[key],
                                           width=44, height=32,
                                           fg_color=COLORS["input_bg"], hover_color=COLORS["btn_welcome_hover"],
                                           text_color=COLORS["text_primary"], font=("Segoe UI", 14),
                                           corner_radius=4,
                                           command=lambda k=key: self._on_preset_click(k))
                btn_preset.grid(row=row_n, column=col_n, padx=2, pady=2)
                self._preset_buttons[key] = btn_preset
                self._sidebar_interactive.append(btn_preset)
        if "margins" not in _HIDDEN_UI_FEATURES:
            row_mx = ctk.CTkFrame(parent, fg_color="transparent")
            row_mx.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row_mx, text="Marge X", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
            entry_mx = ctk.CTkEntry(row_mx, textvariable=self.var_margin_x,
                                    width=55, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                    border_color=COLORS["input_border"], font=("Courier New", 11))
            entry_mx.pack(side="left", padx=4)
            self._sidebar_interactive.append(entry_mx)
            ctk.CTkLabel(row_mx, text="pts", fg_color="transparent", text_color=COLORS["text_unit"],
                         font=("Segoe UI", 10)).pack(side="left")
            row_my = ctk.CTkFrame(parent, fg_color="transparent")
            row_my.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row_my, text="Marge Y", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
            entry_my = ctk.CTkEntry(row_my, textvariable=self.var_margin_y,
                                    width=55, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                    border_color=COLORS["input_border"], font=("Courier New", 11))
            entry_my.pack(side="left", padx=4)
            self._sidebar_interactive.append(entry_my)
            ctk.CTkLabel(row_my, text="pts", fg_color="transparent", text_color=COLORS["text_unit"],
                         font=("Segoe UI", 10)).pack(side="left")

        # Label position courante
        self.lbl_pos = ctk.CTkLabel(parent, text="—",
                                    fg_color="transparent", text_color=COLORS["text_tertiary"],
                                    font=("Courier New", 11), justify="left", anchor="w")
        self.lbl_pos.pack(anchor="w", padx=14, pady=(4, 2))

        # ═══════════════════════════════════════════════════════════════
        # ROTATION — variable toujours créée (utilisée dans _draw_overlay et _apply)
        # ═══════════════════════════════════════════════════════════════
        self.var_rotation = tk.IntVar(value=cfg.get("rotation", 0))
        if "rotation" not in _HIDDEN_UI_FEATURES:
            self._section(parent, "ROTATION")
            rotation_frame = ctk.CTkFrame(parent, fg_color="transparent")
            rotation_frame.pack(fill="x", padx=14, pady=(6, 4))
            for angle in [0, 90, 180, 270]:
                rb = ctk.CTkRadioButton(rotation_frame, text=f"{angle}°",
                                        variable=self.var_rotation, value=angle,
                                        text_color=COLORS["text_primary"], font=("Segoe UI", 11),
                                        command=self._on_text_change)
                rb.pack(side="left", padx=6)
                self._sidebar_interactive.append(rb)

        # ═══════════════════════════════════════════════════════════════
        # CADRE — variables toujours créées (utilisées dans _draw_overlay et _apply)
        # ═══════════════════════════════════════════════════════════════
        self.var_use_frame    = tk.BooleanVar(value=cfg.get("use_frame", False))
        self.var_frame_width  = tk.StringVar(value=str(cfg.get("frame_width", 1.0)))
        self.var_frame_style  = tk.StringVar(value=cfg.get("frame_style", "solid"))
        self.var_frame_padding = tk.StringVar(value=str(cfg.get("frame_padding", 3.0)))
        self.var_frame_opacity = tk.DoubleVar(value=cfg.get("frame_opacity", 1.0))
        if "frame" not in _HIDDEN_UI_FEATURES:
            self._section(parent, "CADRE")
            self._cb_frame = ctk.CTkCheckBox(parent, text="Activer le cadre",
                                             variable=self.var_use_frame,
                                             text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                             command=self._on_frame_toggle)
            self._cb_frame.pack(anchor="w", padx=14, pady=(6, 4))
            self._sidebar_interactive.append(self._cb_frame)
            self._frame_options_frame = ctk.CTkFrame(parent, fg_color="transparent")
            row_fc = ctk.CTkFrame(self._frame_options_frame, fg_color="transparent")
            row_fc.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row_fc, text="Couleur", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            self.frame_color_swatch = tk.Canvas(row_fc, width=22, height=16,
                                                bg=cfg.get("frame_color_hex", COLORS["frame_default"]),
                                                highlightthickness=0, cursor="hand2")
            self.frame_color_swatch.pack(side="left", padx=4)
            self.lbl_frame_color = ctk.CTkLabel(row_fc, text=cfg.get("frame_color_hex", COLORS["frame_default"]),
                                                fg_color="transparent", text_color=COLORS["text_tertiary"],
                                                font=("Courier New", 10))
            self.lbl_frame_color.pack(side="left")
            self.frame_color_swatch.bind("<Button-1>", self._pick_frame_color)
            row_fw = ctk.CTkFrame(self._frame_options_frame, fg_color="transparent")
            row_fw.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row_fw, text="Épaisseur", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            entry_fw = ctk.CTkEntry(row_fw, textvariable=self.var_frame_width,
                                    width=50, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                    border_color=COLORS["input_border"], font=("Courier New", 11))
            entry_fw.pack(side="left", padx=4)
            self._sidebar_interactive.append(entry_fw)
            ctk.CTkLabel(row_fw, text="pts", fg_color="transparent", text_color=COLORS["text_unit"],
                         font=("Segoe UI", 10)).pack(side="left")
            row_fs = ctk.CTkFrame(self._frame_options_frame, fg_color="transparent")
            row_fs.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row_fs, text="Style", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            opt_fs = ctk.CTkOptionMenu(row_fs, values=["solid", "dashed"],
                                       variable=self.var_frame_style,
                                       fg_color=COLORS["input_bg"], button_color=COLORS["input_border"],
                                       button_hover_color=COLORS["input_hover"], text_color=COLORS["text_primary"],
                                       font=("Segoe UI", 11), width=110,
                                       command=lambda _: self._on_text_change())
            opt_fs.pack(side="left", padx=4)
            self._sidebar_interactive.append(opt_fs)
            row_fp = ctk.CTkFrame(self._frame_options_frame, fg_color="transparent")
            row_fp.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row_fp, text="Padding", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            entry_fp = ctk.CTkEntry(row_fp, textvariable=self.var_frame_padding,
                                    width=50, fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"],
                                    border_color=COLORS["input_border"], font=("Courier New", 11))
            entry_fp.pack(side="left", padx=4)
            self._sidebar_interactive.append(entry_fp)
            ctk.CTkLabel(row_fp, text="pts", fg_color="transparent", text_color=COLORS["text_unit"],
                         font=("Segoe UI", 10)).pack(side="left")
            row_fo = ctk.CTkFrame(self._frame_options_frame, fg_color="transparent")
            row_fo.pack(fill="x", padx=10, pady=(2, 6))
            ctk.CTkLabel(row_fo, text="Opacité", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            slider_fo = ctk.CTkSlider(row_fo, from_=0.0, to=1.0, variable=self.var_frame_opacity,
                                      width=110, command=lambda _: self._update_opacity_labels())
            slider_fo.pack(side="left", padx=4)
            self._sidebar_interactive.append(slider_fo)
            self.lbl_frame_opacity = ctk.CTkLabel(
                row_fo, text=f"{int(cfg.get('frame_opacity', 1.0)*100)}%",
                fg_color="transparent", text_color=COLORS["text_tertiary"], font=("Courier New", 10))
            self.lbl_frame_opacity.pack(side="left", padx=2)

        # ═══════════════════════════════════════════════════════════════
        # FOND
        # ═══════════════════════════════════════════════════════════════
        self.var_use_bg     = tk.BooleanVar(value=cfg.get("use_bg", False))
        self.var_bg_opacity = tk.DoubleVar(value=cfg.get("bg_opacity", 0.8))
        if "background" not in _HIDDEN_UI_FEATURES:
            self._section(parent, "FOND")
            self._cb_bg = ctk.CTkCheckBox(parent, text="Activer le fond",
                                          variable=self.var_use_bg,
                                          text_color=COLORS["text_primary"], font=("Segoe UI", 12),
                                          command=self._on_bg_toggle)
            self._cb_bg.pack(anchor="w", padx=14, pady=(6, 4))
            self._sidebar_interactive.append(self._cb_bg)

            # Options fond (masquables)
            self._bg_options_frame = ctk.CTkFrame(parent, fg_color="transparent")

            row_bgc = ctk.CTkFrame(self._bg_options_frame, fg_color="transparent")
            row_bgc.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row_bgc, text="Couleur", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            self.bg_color_swatch = tk.Canvas(row_bgc, width=22, height=16,
                                             bg=cfg.get("bg_color_hex", COLORS["bg_default"]),
                                             highlightthickness=0, cursor="hand2")
            self.bg_color_swatch.pack(side="left", padx=4)
            self.lbl_bg_color = ctk.CTkLabel(row_bgc, text=cfg.get("bg_color_hex", COLORS["bg_default"]),
                                             fg_color="transparent", text_color=COLORS["text_tertiary"],
                                             font=("Courier New", 10))
            self.lbl_bg_color.pack(side="left")
            self.bg_color_swatch.bind("<Button-1>", self._pick_bg_color)

            row_bgo = ctk.CTkFrame(self._bg_options_frame, fg_color="transparent")
            row_bgo.pack(fill="x", padx=10, pady=(2, 6))
            ctk.CTkLabel(row_bgo, text="Opacité", fg_color="transparent", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 10), width=65, anchor="w").pack(side="left")
            slider_bgo = ctk.CTkSlider(row_bgo, from_=0.0, to=1.0, variable=self.var_bg_opacity,
                                       width=110, command=lambda _: self._update_opacity_labels())
            slider_bgo.pack(side="left", padx=4)
            self._sidebar_interactive.append(slider_bgo)
            self.lbl_bg_opacity = ctk.CTkLabel(
                row_bgo, text=f"{int(cfg.get('bg_opacity', 0.8)*100)}%",
                fg_color="transparent", text_color=COLORS["text_tertiary"], font=("Courier New", 10))
            self.lbl_bg_opacity.pack(side="left", padx=2)

        # ═══════════════════════════════════════════════════════════════
        # APPLIQUER SUR
        # ═══════════════════════════════════════════════════════════════
        self._section(parent, "APPLIQUER SUR")

        self.var_all_pages = tk.BooleanVar(value=cfg.get("all_pages", True))
        pages_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pages_frame.pack(fill="x", padx=14, pady=(6, 4))
        for text, val in [("Toutes les pages", True), ("Première page uniquement", False)]:
            rb = ctk.CTkRadioButton(pages_frame, text=text,
                                    variable=self.var_all_pages, value=val,
                                    text_color=COLORS["text_primary"], font=("Segoe UI", 12))
            rb.pack(anchor="w", pady=2)
            self._sidebar_interactive.append(rb)

        # ═══════════════════════════════════════════════════════════════
        # APERÇU
        # ═══════════════════════════════════════════════════════════════
        self._section(parent, "APERÇU")
        self.lbl_preview = ctk.CTkLabel(parent, text="",
                                        fg_color=COLORS["bg_grid"], text_color=COLORS["accent_red"],
                                        font=("Courier New", 10),
                                        wraplength=230, justify="left",
                                        anchor="w", corner_radius=4)
        self.lbl_preview.pack(fill="x", padx=14, pady=6)
        ctk.CTkFrame(parent, fg_color="transparent", height=20).pack()

        # ── Synchronisation initiale des sections masquables ──
        self._update_date_options_visibility()
        self._update_frame_options_visibility()
        self._update_bg_options_visibility()
        self._update_preset_highlight()
        self._on_text_change()

    # -------------------------------------------------- Panneau fichiers ---

    def _build_file_panel(self, parent):
        """Construit le panneau scrollable à droite listant les fichiers PDF chargés."""
        ctk.CTkLabel(parent, text="FICHIERS",
                     fg_color="transparent", text_color=COLORS["text_placeholder"],
                     font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkFrame(parent, fg_color=COLORS["input_border"], height=1,
                     corner_radius=0).pack(fill="x", padx=10)

        self.file_cards_scroll = ctk.CTkScrollableFrame(
            parent, fg_color=COLORS["bg_file_panel"], corner_radius=0
        )
        self.file_cards_scroll.pack(fill="both", expand=True)

        self.file_card_frames = {}
        self.file_card_badges = {}

        self.lbl_file_counter = ctk.CTkLabel(
            parent, text="0 / 0 fichiers traités",
            fg_color=COLORS["bg_topbar"], text_color=COLORS["text_placeholder"],
            font=("Segoe UI", 11)
        )
        self.lbl_file_counter.pack(fill="x", pady=4)

    def _populate_file_panel(self):
        """Peuple le panneau fichiers avec une carte par PDF (état initial : non_traite)."""
        for frame in self.file_card_frames.values():
            frame.destroy()
        self.file_card_frames = {}
        self.file_card_badges = {}
        for i, path in enumerate(self.pdf_files):
            self._create_file_card(i, path)
        self._refresh_file_counter()

    def _create_file_card(self, idx, path):
        """Crée le widget carte pour un fichier (nom tronqué + badge état coloré).
        Retourne le frame de la carte (stocké dans self._file_cards[idx]).
        """
        frame = ctk.CTkFrame(self.file_cards_scroll,
                             fg_color=COLORS["input_bg"], corner_radius=6)
        frame.pack(fill="x", padx=6, pady=3)
        frame.bind("<Button-1>", lambda e, i=idx: self._jump_to_file(i))

        name_lbl = ctk.CTkLabel(frame, text=path.stem,
                                 fg_color="transparent", text_color=COLORS["text_primary"],
                                 font=("Segoe UI", 12), anchor="w",
                                 wraplength=180)
        name_lbl.pack(anchor="w", padx=8, pady=(6, 0))
        name_lbl.bind("<Button-1>", lambda e, i=idx: self._jump_to_file(i))

        badge_lbl = ctk.CTkLabel(frame, text="",
                                  fg_color="transparent", text_color=COLORS["text_tertiary"],
                                  font=("Segoe UI", 10), anchor="w")
        badge_lbl.pack(anchor="w", padx=8, pady=(0, 6))
        badge_lbl.bind("<Button-1>", lambda e, i=idx: self._jump_to_file(i))

        self.file_card_frames[idx] = frame
        self.file_card_badges[idx] = badge_lbl

    def _refresh_card(self, idx):
        """Met à jour la couleur de fond et le texte du badge d'une carte selon son état.
        États : non_traite (neutre), traite (vert), passe (gris), erreur (rouge).
        """
        if idx not in self.file_card_frames:
            return
        frame = self.file_card_frames[idx]
        badge = self.file_card_badges[idx]
        state = self.file_states.get(idx, "non_traite")

        if idx == self.idx:
            frame.configure(fg_color=COLORS["card_active_bg"])
            badge.configure(text="▶ En cours", text_color=COLORS["accent_blue"])
        elif state == "traite":
            frame.configure(fg_color=COLORS["card_done_bg"])
            badge.configure(text="✓ Modifié", text_color=COLORS["accent_green"])
        elif state == "passe":
            frame.configure(fg_color=COLORS["card_passe_bg"])
            badge.configure(text="→ Ignoré", text_color=COLORS["text_unit"])
        elif state == "erreur":
            frame.configure(fg_color=COLORS["card_error_bg"])
            badge.configure(text="⚠ Erreur", text_color=COLORS["error_red"])
        else:
            frame.configure(fg_color=COLORS["input_bg"])
            badge.configure(text="", text_color=COLORS["text_tertiary"])

    def _refresh_all_cards(self):
        """Rafraîchit toutes les cartes du panneau fichiers."""
        for i in range(len(self.pdf_files)):
            self._refresh_card(i)
        self._refresh_file_counter()

    def _refresh_file_counter(self):
        """Met à jour le compteur 'X / Y fichiers traités' en bas du panneau."""
        done = sum(1 for s in self.file_states.values() if s in ("traite", "passe"))
        total = len(self.pdf_files)
        self.lbl_file_counter.configure(text=f"{done} / {total} fichiers traités")

    def _find_next_untreated(self):
        """Retourne l'index du prochain fichier en état 'non_traite', ou None si tous traités."""
        n = len(self.pdf_files)
        for offset in range(1, n):
            i = (self.idx + offset) % n
            if self.file_states.get(i, "non_traite") == "non_traite":
                return i
        return None

    def _jump_to_file(self, idx):
        """Charge le PDF à l'index donné et affiche sa prévisualisation sur le canvas."""
        self.idx = idx
        self._load_pdf()

    # --------------------------------------------------- Écran d'accueil ---

    def _show_welcome_screen(self):
        """Affiche l'écran d'accueil (boutons Ouvrir fichiers / Ouvrir dossier) sur le canvas.
        Désactive la sidebar tant qu'aucun PDF n'est chargé.
        """
        self.welcome_frame = ctk.CTkFrame(self.canvas_frame, fg_color=COLORS["bg_canvas"], corner_radius=0)
        self.welcome_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        ctk.CTkFrame(self.welcome_frame, fg_color="transparent", height=120).pack()

        ctk.CTkLabel(self.welcome_frame, text="PDF HEADER TOOL",
                     fg_color="transparent", text_color=COLORS["accent_red"],
                     font=("Courier New", 18, "bold")).pack(pady=(0, 8))

        ctk.CTkLabel(self.welcome_frame,
                     text="Choisissez les fichiers PDF à traiter",
                     fg_color="transparent", text_color=COLORS["text_unit"],
                     font=("Segoe UI", 11)).pack(pady=(0, 40))

        btn_row = ctk.CTkFrame(self.welcome_frame, fg_color="transparent")
        btn_row.pack()

        ctk.CTkButton(btn_row, text="📄  Ouvrir des fichiers",
                      width=200, height=50,
                      fg_color=COLORS["btn_welcome_bg"], hover_color=COLORS["btn_welcome_hover"],
                      text_color=COLORS["accent_blue"], font=("Segoe UI", 12),
                      command=self._open_files).pack(side="left", padx=16)

        ctk.CTkButton(btn_row, text="📁  Ouvrir un dossier",
                      width=200, height=50,
                      fg_color=COLORS["btn_welcome_bg"], hover_color=COLORS["btn_welcome_hover"],
                      text_color=COLORS["accent_blue"], font=("Segoe UI", 12),
                      command=self._open_folder).pack(side="left", padx=16)

        self._set_ui_state(False)

    def _hide_welcome_screen(self):
        """Cache l'écran d'accueil et réactive la sidebar."""
        if hasattr(self, "welcome_frame") and self.welcome_frame.winfo_exists():
            self.welcome_frame.destroy()
        self._set_ui_state(True)

    def _set_ui_state(self, enabled: bool):
        """Active ou désactive tous les contrôles de la sidebar.
        Args: state (str) — "normal" ou "disabled".
        """
        state = "normal" if enabled else "disabled"
        self.btn_apply.configure(state=state)
        self.btn_skip.configure(state=state)
        for w in self._sidebar_interactive:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _open_files(self):
        """Ouvre une boîte de dialogue de sélection de fichiers PDF.
        Charge les fichiers sélectionnés dans la liste et affiche le premier.
        """
        paths = filedialog.askopenfilenames(
            title="Sélectionner des fichiers PDF",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not paths:
            return
        self.pdf_files = [Path(p) for p in paths]
        self.file_states = {i: "non_traite" for i in range(len(self.pdf_files))}
        self.idx = 0
        log_ui.info(f"OPEN_FILES count={len(self.pdf_files)}")
        self._populate_file_panel()
        self._hide_welcome_screen()
        self._load_pdf()

    def _open_folder(self):
        """Ouvre une boîte de dialogue de sélection de dossier.
        Charge tous les fichiers .pdf du dossier (non récursif) et affiche le premier.
        """
        folder = filedialog.askdirectory(title="Sélectionner le dossier contenant les PDFs")
        if not folder:
            return
        self.pdf_files = sorted(Path(folder).glob("*.pdf"))
        if not self.pdf_files:
            messagebox.showwarning("Aucun fichier", "Aucun fichier PDF trouvé dans ce dossier.")
            return
        self.file_states = {i: "non_traite" for i in range(len(self.pdf_files))}
        self.idx = 0
        log_ui.info(f"OPEN_FOLDER count={len(self.pdf_files)}")
        self._populate_file_panel()
        self._hide_welcome_screen()
        self._load_pdf()

    # ------------------------------------------- Callbacks sidebar texte ---

    def _on_text_change(self, *_):
        """Appelée quand la configuration du texte change. Relance _draw_overlay()."""
        self.lbl_preview.configure(text=self._get_header_text())
        self._draw_overlay()

    def _on_use_custom_change(self, *_):
        """Affiche ou cache le champ de texte personnalisé selon l'état de var_use_custom."""
        if self.var_use_custom.get():
            self.var_use_filename.set(False)
        self._on_text_change()

    def _on_date_toggle(self, *_):
        """Affiche ou cache les options de date selon l'état de var_use_date."""
        self._update_date_options_visibility()
        self._on_text_change()

    def _update_date_options_visibility(self):
        """Pack ou unpack les widgets date (position, source, format) selon var_use_date."""
        if self.var_use_date.get():
            self._date_options_frame.pack(fill="x", padx=4, after=self._cb_date)
        else:
            self._date_options_frame.pack_forget()

    def _on_date_format_change(self, display_value: str):
        """Met à jour cfg['date_format'] quand l'utilisateur change le menu déroulant de format."""
        fmt = self._date_format_map.get(display_value, "%d/%m/%Y")
        self.var_date_format.set(fmt)
        self._on_text_change()

    def _on_frame_toggle(self, *_):
        """Affiche ou cache les options de cadre selon l'état de var_use_frame."""
        self._update_frame_options_visibility()
        self._on_text_change()

    def _update_frame_options_visibility(self):
        """Pack ou unpack les widgets cadre. Sans effet si 'frame' in _HIDDEN_UI_FEATURES."""
        if "frame" in _HIDDEN_UI_FEATURES:
            return
        if self.var_use_frame.get():
            self._frame_options_frame.pack(fill="x", padx=4, after=self._cb_frame)
        else:
            self._frame_options_frame.pack_forget()

    def _on_bg_toggle(self, *_):
        """Affiche ou cache les options de fond selon l'état de var_use_bg."""
        self._update_bg_options_visibility()
        self._on_text_change()

    def _update_bg_options_visibility(self):
        """Pack ou unpack les widgets fond. Sans effet si 'background' in _HIDDEN_UI_FEATURES."""
        if "background" in _HIDDEN_UI_FEATURES:
            return
        if self.var_use_bg.get():
            self._bg_options_frame.pack(fill="x", padx=4, after=self._cb_bg)
        else:
            self._bg_options_frame.pack_forget()

    def _update_opacity_labels(self):
        """Met à jour les labels d'opacité affichant la valeur en % (slider 0.0-1.0 → 0-100)."""
        try:
            self.lbl_frame_opacity.configure(text=f"{int(self.var_frame_opacity.get()*100)}%")
            self.lbl_bg_opacity.configure(text=f"{int(self.var_bg_opacity.get()*100)}%")
        except Exception:
            pass
        self._draw_overlay()

    def _on_font_change(self, font_name: str):
        """Met à jour cfg['font_file'] et cfg['font_family'] quand l'utilisateur change la police."""
        if font_name in self._system_fonts:
            self.cfg["font_file"] = str(self._system_fonts[font_name])
            log_ui.debug(f"UI_FONT_CHANGE font={font_name} file={self.cfg['font_file']}")
        else:
            self.cfg["font_file"] = None
            log_ui.debug(f"UI_FONT_CHANGE font={font_name} type=builtin")
        self._on_text_change()

    # --------------------------------------------------- Couleurs (picks) ---

    def _pick_color(self, _=None):
        """Ouvre le sélecteur de couleur tkinter pour la couleur du texte de l'en-tête."""
        color = colorchooser.askcolor(color=self.cfg["color_hex"],
                                      title="Couleur du texte")
        if color and color[1]:
            self.cfg["color_hex"] = color[1].upper()
            self.color_swatch.config(bg=self.cfg["color_hex"])
            self.lbl_color_hex.configure(text=self.cfg["color_hex"])
            self._draw_overlay()

    def _pick_frame_color(self, _=None):
        """Ouvre le sélecteur de couleur tkinter pour la couleur du cadre."""
        color = colorchooser.askcolor(color=self.cfg.get("frame_color_hex", COLORS["frame_default"]),
                                      title="Couleur du cadre")
        if color and color[1]:
            self.cfg["frame_color_hex"] = color[1].upper()
            self.frame_color_swatch.config(bg=self.cfg["frame_color_hex"])
            self.lbl_frame_color.configure(text=self.cfg["frame_color_hex"])
            self._draw_overlay()

    def _pick_bg_color(self, _=None):
        """Ouvre le sélecteur de couleur tkinter pour la couleur du fond."""
        color = colorchooser.askcolor(color=self.cfg.get("bg_color_hex", COLORS["bg_default"]),
                                      title="Couleur du fond")
        if color and color[1]:
            self.cfg["bg_color_hex"] = color[1].upper()
            self.bg_color_swatch.config(bg=self.cfg["bg_color_hex"])
            self.lbl_bg_color.configure(text=self.cfg["bg_color_hex"])
            self._draw_overlay()

    def _change_size(self, delta):
        """Incrémente ou décrémente la taille de police de `delta` points (±1 typiquement)."""
        val = max(SIZES["font_size_min"], min(SIZES["font_size_max"], self.var_size.get() + delta))
        self.var_size.set(val)
        self._on_text_change()

    # ----------------------------------------------- Presets de position ---

    def _on_preset_click(self, preset_key: str):
        """Sélectionne un preset de position (tl/tc/.../br), recalcule les ratios et redessine l'overlay."""
        self.preset_position = preset_key
        self._recalc_ratio_from_preset()
        self._update_preset_highlight()
        self._update_pos_label()
        self._draw_overlay()

    def _recalc_ratio_from_preset(self):
        """Convertit le preset actif + marges (en pts PDF) en ratios canvas (0.0-1.0).
        Stocke le résultat dans self.pos_ratio_x / self.pos_ratio_y.
        Les marges margin_x_pt / margin_y_pt sont en points PDF (1 pt = 1/72 pouce).
        """
        if self.preset_position == "custom":
            return
        if self.preset_position not in POSITION_PRESETS:
            return
        try:
            mx = float(self.var_margin_x.get())
            my = float(self.var_margin_y.get())
        except (ValueError, AttributeError):
            mx, my = 20.0, 20.0
        self.pos_ratio_x, self.pos_ratio_y = recalc_ratio_from_preset(
            self.preset_position, mx, my, self.page_w_pt, self.page_h_pt
        )

    def _on_margins_change(self, *_):
        """Recalcule les ratios depuis le preset actif quand une marge change (trace StringVar)."""
        if self.preset_position != "custom":
            self._recalc_ratio_from_preset()
            self._update_pos_label()
            self._draw_overlay()

    def _update_preset_highlight(self):
        """Surligne le bouton du preset actif en bleu, réinitialise les autres."""
        if not hasattr(self, "_preset_buttons"):
            return
        for key, btn in self._preset_buttons.items():
            if key == self.preset_position:
                btn.configure(fg_color=COLORS["preset_active"], text_color=COLORS["accent_blue"])
            else:
                btn.configure(fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"])

    # ----------------------------------------------- Composition du texte ---

    def _get_header_text(self) -> str:
        """Assemble le texte de l'en-tête depuis la config courante.
        Format : [date_prefix] [prefix] [path.stem | custom_text] [suffix] [date_suffix]
        Utilise path.stem (sans extension) pour le nom de fichier.
        """
        # Base
        if self.var_use_custom.get():
            base = self.var_custom_text.get().strip()
        elif self.var_use_filename.get():
            if self.pdf_files and self.idx < len(self.pdf_files):
                base = self.pdf_files[self.idx].stem
            else:
                base = "fichier"
        else:
            base = ""

        # Date
        date_str = ""
        if self.var_use_date.get():
            fmt    = self.var_date_format.get() or "%d/%m/%Y"
            source = DATE_SOURCE_INTERNAL.get(self.var_date_source.get(), "today")
            if source == "file_mtime" and self.pdf_files and self.idx < len(self.pdf_files):
                try:
                    mtime = self.pdf_files[self.idx].stat().st_mtime
                    dt    = datetime.datetime.fromtimestamp(mtime)
                except Exception:
                    dt = datetime.datetime.today()
            else:
                dt = datetime.datetime.today()
            try:
                date_str = dt.strftime(fmt)
            except Exception:
                date_str = dt.strftime("%d/%m/%Y")

        # Assemblage
        prefix_parts = []
        if date_str and self.var_date_position.get() == "prefix":
            prefix_parts.append(date_str)
        if self.var_use_prefix.get():
            pfx = self.var_prefix_text.get().strip()
            if pfx:
                prefix_parts.append(pfx)

        suffix_parts = []
        if self.var_use_suffix.get():
            sfx = self.var_suffix_text.get().strip()
            if sfx:
                suffix_parts.append(sfx)
        if date_str and self.var_date_position.get() == "suffix":
            suffix_parts.append(date_str)

        parts = prefix_parts + ([base] if base else []) + suffix_parts
        return " ".join(parts).strip()

    # --------------------------------------------------------- PDF courant ---

    def _load_pdf(self):
        """Ouvre le PDF à self.idx, charge la première page, appelle _render_preview().
        Met à jour self.current_path, self.current_doc, self.current_page.
        """
        path = self.pdf_files[self.idx]
        self.lbl_filename.configure(text=f"  {path.name}  ")
        self.lbl_progress.configure(text=f"  {self.idx + 1} / {len(self.pdf_files)}  ")
        if self.doc:
            self.doc.close()
        _t0_load = time.perf_counter()
        self.doc = fitz.open(str(path))
        log_pdf.info(
            f"PDF_OPEN file={path.name} pages={len(self.doc)} idx={self.idx} "
            f"elapsed_ms={int((time.perf_counter() - _t0_load) * 1000)}"
        )
        # Lire les dims dès maintenant pour _recalc_ratio_from_preset()
        page0 = self.doc[0]
        self.page_w_pt = page0.rect.width
        self.page_h_pt = page0.rect.height
        self._recalc_ratio_from_preset()
        self._update_pos_label()
        self._on_text_change()
        self._render_preview()
        self._refresh_all_cards()

    # --------------------------------------------------------- Rendu canvas ---

    def _render_preview(self):
        """Convertit la page PDF courante en image PIL via PyMuPDF puis en ImageTk.
        Met à jour self.scale, self.img_offset_x/y, self.page_w_px/h_px, self.page_w_pt/h_pt.
        Appelée par _load_pdf() et après redimensionnement de fenêtre.
        """
        if not self.doc:
            return
        _t0_render = time.perf_counter()
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(),  10)
        ch = max(self.canvas.winfo_height(), 10)

        page = self.doc[0]
        self.page_w_pt = page.rect.width
        self.page_h_pt = page.rect.height

        scale_w = (cw - SIZES["canvas_pad"]) / self.page_w_pt
        scale_h = (ch - SIZES["canvas_pad"]) / self.page_h_pt
        self.scale = min(scale_w, scale_h, SIZES["canvas_scale_max"])

        mat = fitz.Matrix(self.scale, self.scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        self.page_w_px = pix.width
        self.page_h_px = pix.height
        _debug_log(
            f"RENDER canvas_wh=({cw},{ch}) scale={self.scale:.4f} "
            f"page_pt=({self.page_w_pt:.1f}x{self.page_h_pt:.1f}) "
            f"page_px=({pix.width}x{pix.height}) "
            f"tk_scaling={self.canvas.tk.call('tk','scaling'):.3f}"
        )
        log_pdf.debug(
            f"RENDER scale={self.scale:.4f} "
            f"page_pt=({self.page_w_pt:.1f}x{self.page_h_pt:.1f}) "
            f"page_px=({pix.width}x{pix.height}) "
            f"elapsed_ms={int((time.perf_counter() - _t0_render) * 1000)}"
        )

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)

        self.img_offset_x = (cw - pix.width)  // 2
        self.img_offset_y = (ch - pix.height) // 2

        self.canvas.delete("all")
        self.canvas.create_image(self.img_offset_x, self.img_offset_y,
                                 anchor="nw", image=self.tk_img, tags="page")
        self._draw_overlay()

    def _draw_overlay(self, hover_cx=None, hover_cy=None):
        """Dessine l'aperçu interactif sur le canvas (lignes de guidage, fond/cadre approx, texte, crosshair).
        Args: hover_cx/hover_cy (float|None) — position souris pour les lignes de guidage (None = pas de hover).
        Guard: retour immédiat si self.canvas n'existe pas encore.
        """
        if not hasattr(self, "canvas"):
            return
        # Log uniquement lors des mises à jour de position (pas sur chaque hover)
        if hover_cx is None:
            log_ui.debug(
                f"OVERLAY_UPDATE ratio=({self.pos_ratio_x:.4f},{self.pos_ratio_y:.4f}) "
                f"preset={self.preset_position}"
            )
        self.canvas.delete("overlay")

        # Croix de guidage au survol
        if hover_cx is not None:
            x0 = self.img_offset_x
            x1 = self.img_offset_x + self.page_w_px
            y0 = self.img_offset_y
            y1 = self.img_offset_y + self.page_h_px
            self.canvas.create_line(x0, hover_cy, x1, hover_cy,
                                    fill=COLORS["overlay_guide"], width=1, dash=(4,4), tags="overlay")
            self.canvas.create_line(hover_cx, y0, hover_cx, y1,
                                    fill=COLORS["overlay_guide"], width=1, dash=(4,4), tags="overlay")

        cx, cy  = self._ratio_to_canvas(self.pos_ratio_x, self.pos_ratio_y)
        text    = self._get_header_text()
        size    = max(self.var_size.get(), SIZES["font_size_min"])
        fpx     = max(int(size * self.scale * SIZES["text_scale"]), 7)
        color   = self.cfg.get("color_hex", COLORS["text_default"])
        rotation = self.var_rotation.get()

        # Police canvas (approximation)
        font_family = self.var_font_family.get()
        style_parts = []
        if self.var_bold.get():
            style_parts.append("bold")
        if self.var_italic.get():
            style_parts.append("italic")
        style_str = " ".join(style_parts) if style_parts else "normal"
        canvas_font_map = {
            "Courier": "Courier New",
            "Helvetica": "Helvetica",
            "Times": "Times New Roman"
        }
        canvas_font_name = canvas_font_map.get(font_family, font_family)
        canvas_font = (canvas_font_name, fpx, style_str)

        # Fond et cadre : approximation canvas uniquement (pas de mesure exacte possible avec tkinter).
        # SIZES["text_char_w"] est calibré empiriquement pour Courier 12pt.
        # Fond et cadre approximatifs (avant le texte)
        if self.var_use_bg.get() or self.var_use_frame.get():
            approx_w = max(len(text) * fpx * SIZES["text_char_w"], 20)
            approx_h = fpx * SIZES["text_char_h"]
            try:
                pad_px = max(2, int(float(self.var_frame_padding.get()) * self.scale))
            except (ValueError, AttributeError):
                pad_px = 2
            bg_x0 = cx - approx_w / 2 - pad_px
            bg_y0 = cy - approx_h / 2 - pad_px
            bg_x1 = cx + approx_w / 2 + pad_px
            bg_y1 = cy + approx_h / 2 + pad_px
            if self.var_use_bg.get():
                bg_col = self.cfg.get("bg_color_hex", COLORS["bg_default"])
                self.canvas.create_rectangle(bg_x0, bg_y0, bg_x1, bg_y1,
                                             fill=bg_col, outline="", tags="overlay")
            if self.var_use_frame.get():
                fc_hex = self.cfg.get("frame_color_hex", COLORS["frame_default"])
                try:
                    fw_px = max(1, int(float(self.var_frame_width.get()) * self.scale))
                except (ValueError, AttributeError):
                    fw_px = 1
                f_dash = (4, 4) if self.var_frame_style.get() == "dashed" else ()
                self.canvas.create_rectangle(bg_x0, bg_y0, bg_x1, bg_y1,
                                             outline=fc_hex, width=fw_px,
                                             dash=f_dash, fill="", tags="overlay")

        # Texte avec rotation (ancré au centre)
        try:
            self.canvas.create_text(cx, cy, text=text, anchor="center",
                                    fill=color, font=canvas_font,
                                    angle=rotation, tags="overlay")
        except tk.TclError:
            self.canvas.create_text(cx, cy, text=text, anchor="center",
                                    fill=color, font=canvas_font, tags="overlay")

        # Soulignement approximatif (uniquement si rotation == 0)
        if self.var_underline.get() and rotation == 0:
            approx_w = max(len(text) * fpx * SIZES["text_char_w"], 20)
            approx_h = fpx * SIZES["text_char_h"]
            ul_y = cy + approx_h / 2 + max(1, int(fpx * SIZES["underline_thick"]))
            self.canvas.create_line(cx - approx_w / 2, ul_y, cx + approx_w / 2, ul_y,
                                    fill=color, width=max(1, int(fpx * SIZES["underline_thick"])),
                                    tags="overlay")

        # Croix de repère
        r = SIZES["cross_radius"]
        self.canvas.create_line(cx-r, cy, cx+r, cy, fill=color, width=1, tags="overlay")
        self.canvas.create_line(cx, cy-r, cx, cy+r, fill=color, width=1, tags="overlay")

    # --------------------------------------------------------- Interactions ---

    def _canvas_to_ratio(self, cx, cy):
        """Coordonnées canvas (px) → ratio page (0.0-1.0), clampé aux bornes."""
        return canvas_to_ratio(
            cx, cy, self.img_offset_x, self.img_offset_y, self.page_w_px, self.page_h_px
        )

    def _ratio_to_canvas(self, rx, ry):
        """Ratio page (0.0-1.0) → coordonnées canvas (px absolues)."""
        return ratio_to_canvas(
            rx, ry, self.img_offset_x, self.img_offset_y, self.page_w_px, self.page_h_px
        )

    def _ratio_to_pdf_pt(self, rx, ry):
        """Ratio → coordonnées PDF en points (Y=0 en bas, système fitz)."""
        return ratio_to_pdf_pt(rx, ry, self.page_w_pt, self.page_h_pt)

    def _on_click(self, event):
        """Stocke la position cliquée comme ratio (0.0-1.0), passe preset à 'custom', redessine l'overlay."""
        rx, ry = self._canvas_to_ratio(event.x, event.y)
        self.pos_ratio_x = rx
        self.pos_ratio_y = ry
        # Passer en mode "Personnalisée"
        self.preset_position = "custom"
        self._update_preset_highlight()
        fname = self.pdf_files[self.idx].name if self.pdf_files else "?"
        _debug_log(
            f"CLICK [{fname}] canvas=({event.x},{event.y}) "
            f"offset=({self.img_offset_x},{self.img_offset_y}) "
            f"page_px=({self.page_w_px},{self.page_h_px}) "
            f"ratio=({rx:.4f},{ry:.4f}) "
            f"canvas_wh=({self.canvas.winfo_width()},{self.canvas.winfo_height()})"
        )
        x_pt_c, y_pt_c = self._ratio_to_pdf_pt(rx, ry)
        log_ui.debug(
            f"UI_CLICK file={fname} "
            f"ratio=({rx:.4f},{ry:.4f}) "
            f"pt=({x_pt_c:.1f},{y_pt_c:.1f})"
        )
        self._update_pos_label()
        self._draw_overlay()

    def _on_motion(self, event):
        """Dessine les lignes de guidage pointillées à la position souris et met à jour le label coords."""
        self._draw_overlay(hover_cx=event.x, hover_cy=event.y)
        rx, ry = self._canvas_to_ratio(event.x, event.y)
        x_pt, y_pt = self._ratio_to_pdf_pt(rx, ry)
        self.lbl_coords.configure(text=f"x: {x_pt:.0f} pts  ·  y: {y_pt:.0f} pts")

    def _update_pos_label(self):
        """Met à jour le label de coordonnées affichant x/y en points PDF selon la position courante."""
        x_pt, y_pt = self._ratio_to_pdf_pt(self.pos_ratio_x, self.pos_ratio_y)
        preset_label = PRESET_LABELS.get(self.preset_position, "libre")
        self.lbl_pos.configure(
            text=f"[{preset_label}]  x: {x_pt:.0f} pts  y: {y_pt:.0f} pts"
        )

    # ------------------------------------------------------------ Actions ---

    def _apply(self):
        """Insère l'en-tête dans le PDF courant et sauvegarde dans <dossier>_avec_entete/.

        Pour chaque page (ou première page seulement selon all_pages) :
        - Calcule la position en pts fitz depuis le ratio cliqué
        - Dessine fond et cadre si activés (centrés sur le point cliqué)
        - Insère le texte via insert_textbox() (centré, avec rotation)
        - Dessine le soulignement si activé
        Logue PDF_INSERT_PARAMS et PDF_INSERT_RESULT (profil medium/full).
        Passe au fichier suivant ou affiche 'Terminé' si tous traités.
        """
        path     = self.pdf_files[self.idx]
        out_dir  = path.parent.with_name(path.parent.name + "_avec_entete")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / path.name

        header_text = self._get_header_text()
        _t0_apply = time.perf_counter()
        color_float = hex_to_rgb_float(self.cfg["color_hex"])
        font_size   = max(self.var_size.get(), SIZES["font_size_min"])
        all_pages   = self.var_all_pages.get()
        rotation    = self.var_rotation.get()
        x_pt, y_pt = self._ratio_to_pdf_pt(self.pos_ratio_x, self.pos_ratio_y)

        font_family = self.var_font_family.get()
        font_file   = self.cfg.get("font_file")
        bold        = self.var_bold.get()
        italic      = self.var_italic.get()
        underline   = self.var_underline.get()
        font_args   = _get_fitz_font_args(font_family, font_file, bold, italic)

        try:
            line_spacing = max(SIZES["line_spacing_min"], float(self.var_line_spacing.get()))
        except (ValueError, AttributeError):
            line_spacing = 1.2

        use_frame     = self.var_use_frame.get()
        frame_color   = hex_to_rgb_float(self.cfg.get("frame_color_hex", COLORS["frame_default"]))
        try:
            frame_width = max(SIZES["frame_width_min"], float(self.var_frame_width.get()))
        except (ValueError, AttributeError):
            frame_width = 1.0
        frame_style   = self.var_frame_style.get()
        try:
            frame_padding = max(SIZES["frame_pad_min"], float(self.var_frame_padding.get()))
        except (ValueError, AttributeError):
            frame_padding = 3.0
        frame_opacity = max(0.0, min(1.0, self.var_frame_opacity.get()))

        use_bg     = self.var_use_bg.get()
        bg_color   = hex_to_rgb_float(self.cfg.get("bg_color_hex", COLORS["bg_default"]))
        bg_opacity = max(0.0, min(1.0, self.var_bg_opacity.get()))

        log_pdf.info(
            f"PDF_PROCESS_START file={path.name} "
            f"pages_mode={'all' if all_pages else 'first'} "
            f"font={font_family} size={font_size} rotation={rotation}"
        )
        try:
            doc_out = fitz.open(str(path))
            pages_to_process = range(len(doc_out)) if all_pages else [0]

            _debug_log(
                f"APPLY [{path.name}] ratio=({self.pos_ratio_x:.4f},{self.pos_ratio_y:.4f}) "
                f"x_pt={x_pt:.1f} y_pt={y_pt:.1f} rotation={rotation} font={font_family}"
            )
            log_pdf.debug(
                f"PDF_INSERT_PARAMS file={path.name} "
                f"text_len={len(header_text)} text_preview={header_text[:30]!r} "
                f"font={font_family} size={font_size} bold={bold} italic={italic} "
                f"rotation={rotation} "
                f"click_ratio=({self.pos_ratio_x:.4f},{self.pos_ratio_y:.4f}) "
                f"preset={self.preset_position} "
                f"margin_x={self.cfg.get('margin_x_pt', 20.0):.1f} "
                f"margin_y={self.cfg.get('margin_y_pt', 20.0):.1f}"
            )

            for i in pages_to_process:
                pg = doc_out[i]
                result = insert_header(
                    pg,
                    header_text,
                    x_pt, y_pt,
                    font_args,
                    font_size,
                    line_spacing,
                    color_float,
                    rotation,
                    use_bg, bg_color, bg_opacity,
                    use_frame, frame_color, frame_width,
                    frame_style, frame_padding, frame_opacity,
                    underline,
                )
                log_pdf.debug(
                    f"PDF_INSERT_RESULT file={path.name} page={i} "
                    f"page_dims=({pg.rect.width:.1f},{pg.rect.height:.1f}) "
                    f"x_pt={x_pt:.1f} y_pt={y_pt:.1f} fitz_y={result['fitz_y']:.1f} "
                    f"text_rect=[{result['text_rect'].x0:.1f},{result['text_rect'].y0:.1f},"
                    f"{result['text_rect'].x1:.1f},{result['text_rect'].y1:.1f}] "
                    f"text_w_est={result['text_width']:.1f} "
                    f"text_h_est={font_size * result['lineheight']:.1f} "
                    f"truncated={result['truncated']} remaining_chars={max(0, -int(result['remaining_chars']))} "
                    f"click_ratio=({self.pos_ratio_x:.4f},{self.pos_ratio_y:.4f}) "
                    f"applied_ratio=({x_pt / pg.rect.width:.4f},{1 - result['fitz_y'] / pg.rect.height:.4f})"
                )

            doc_out.save(str(out_path), garbage=4, deflate=True)
            doc_out.close()
            log_pdf.info(
                f"PDF_PROCESS_OK file={path.name} "
                f"elapsed_ms={int((time.perf_counter() - _t0_apply) * 1000)} "
                f"out={out_path.name}"
            )

        except PermissionError:
            log_pdf.error(f"PDF_PROCESS_ERROR file={path.name} error=PermissionError")
            messagebox.showerror("Erreur",
                "Le fichier est ouvert dans un autre programme. Fermez-le et réessayez.")
            self.file_states[self.idx] = "erreur"
            self._refresh_all_cards()
            return
        except Exception as e:
            log_pdf.error(f"PDF_PROCESS_ERROR file={path.name} error={e}")
            messagebox.showerror("Erreur", str(e))
            self.file_states[self.idx] = "erreur"
            self._refresh_all_cards()
            return

        # Sauvegarde config
        try:
            letter_spacing = float(self.var_letter_spacing.get())
        except (ValueError, AttributeError):
            letter_spacing = 0.0
        try:
            margin_x = float(self.var_margin_x.get())
            margin_y = float(self.var_margin_y.get())
        except (ValueError, AttributeError):
            margin_x, margin_y = 20.0, 20.0

        self.cfg.update({
            "use_filename":    self.var_use_filename.get(),
            "use_prefix":      self.var_use_prefix.get(),
            "prefix_text":     self.var_prefix_text.get(),
            "use_suffix":      self.var_use_suffix.get(),
            "suffix_text":     self.var_suffix_text.get(),
            "use_custom":      self.var_use_custom.get(),
            "custom_text":     self.var_custom_text.get(),
            "use_date":        self.var_use_date.get(),
            "date_position":   self.var_date_position.get(),
            "date_source":     DATE_SOURCE_INTERNAL.get(self.var_date_source.get(), "today"),
            "date_format":     self.var_date_format.get(),
            "font_family":     self.var_font_family.get(),
            "font_size":       font_size,
            "bold":            bold,
            "italic":          italic,
            "underline":       underline,
            "letter_spacing":  letter_spacing,
            "line_spacing":    line_spacing,
            "color_hex":       self.cfg["color_hex"],
            "preset_position": self.preset_position,
            "margin_x_pt":     margin_x,
            "margin_y_pt":     margin_y,
            "last_x_ratio":    self.pos_ratio_x,
            "last_y_ratio":    self.pos_ratio_y,
            "rotation":        rotation,
            "use_frame":       use_frame,
            "frame_color_hex": self.cfg.get("frame_color_hex", COLORS["frame_default"]),
            "frame_width":     frame_width,
            "frame_style":     frame_style,
            "frame_padding":   frame_padding,
            "frame_opacity":   frame_opacity,
            "use_bg":          use_bg,
            "bg_color_hex":    self.cfg.get("bg_color_hex", COLORS["bg_default"]),
            "bg_opacity":      bg_opacity,
            "all_pages":       all_pages,
        })
        save_config(self.cfg, INSTALL_DIR)

        self.file_states[self.idx] = "traite"
        next_idx = self._find_next_untreated()
        if next_idx is None:
            self._refresh_all_cards()
            messagebox.showinfo("Terminé", "Tous les fichiers ont été traités !")
            self.root.quit()
            return
        self.idx = next_idx
        self._load_pdf()

    def _skip(self):
        """Marque le fichier courant comme ignoré (état 'passe') et passe au suivant."""
        fname = self.pdf_files[self.idx].name if self.pdf_files else "?"
        log_ui.info(f"PDF_SKIP file={fname} idx={self.idx}")
        self.file_states[self.idx] = "passe"
        next_idx = self._find_next_untreated()
        if next_idx is None:
            self._refresh_all_cards()
            messagebox.showinfo("Terminé", "Tous les fichiers ont été traités !")
            self.root.quit()
            return
        self.idx = next_idx
        self._load_pdf()

# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def main():
    print(f"PDF Header Tool version: {VERSION} (build {BUILD_ID})")
    check_update(_RUNNING_VERSION, CHANNEL, GITHUB_REPO, INSTALL_DIR, TIMINGS)
    log_app.info(f"APP_LAUNCH version={VERSION} build={BUILD_ID}")

    pdf_files = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.is_dir():
                pdf_files.extend(sorted(p.glob("*.pdf")))
            elif p.suffix.lower() == ".pdf" and p.exists():
                pdf_files.append(p)

    if pdf_files:
        print(f"{len(pdf_files)} fichier(s) PDF trouvé(s).")

    root = ctk.CTk()
    root.geometry(f"{SIZES['win_w']}x{SIZES['win_h']}")
    app = PDFHeaderApp(root, pdf_files)
    root.mainloop()

if __name__ == "__main__":
    main()
