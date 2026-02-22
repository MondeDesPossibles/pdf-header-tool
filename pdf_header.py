# ==============================================================================
# PDF Header Tool — pdf_header.py
# Version : 0.4.6
# Build   : build-2026.02.21.07
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

VERSION     = "0.4.6.6"
BUILD_ID    = "build-2026.02.22.01"
GITHUB_REPO = "MondeDesPossibles/pdf-header-tool"

import sys
import os
import json
import shutil
import tempfile
import threading
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap : modèle portable (Étape 4.6+)
# ---------------------------------------------------------------------------
def _get_install_dir():
    """Retourne le dossier de l'application.
    Modèle portable : toujours le dossier du script (Windows et Linux).
    La config, les logs et les polices temporaires sont stockés ici.
    """
    return Path(__file__).parent

def _apply_pending_update():
    """Applique un patch téléchargé lors du lancement précédent.
    Doit être appelée avant _bootstrap() — ne lève jamais d'exception.
    """
    staging = _get_install_dir() / "_update_pending"
    if not staging.exists():
        return
    try:
        import shutil
        install_dir = _get_install_dir()
        for src in staging.iterdir():
            if src.name.startswith("_"):
                continue
            dst = install_dir / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        delete_file = staging / "_delete.json"
        if delete_file.exists():
            for f in json.loads(delete_file.read_text()):
                target = install_dir / f
                if target.exists():
                    target.unlink()
        version_file = staging / "_target_version.txt"
        if version_file.exists():
            (install_dir / "version.txt").write_text(version_file.read_text())
        shutil.rmtree(staging)
    except Exception:
        pass

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

_apply_pending_update()
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

# ---------------------------------------------------------------------------
# Constantes UI — couleurs, dimensions, timings
# ---------------------------------------------------------------------------
COLORS = {
    # Arrière-plans principaux
    "bg_dark":           "#1a1a1f",   # fond principal (root, body)
    "bg_topbar":         "#111116",   # topbar et bottombar
    "bg_canvas":         "#141418",   # zone canvas PDF
    "bg_sidebar":        "#22222a",   # sidebar (outer + scrollable)
    "bg_file_panel":     "#1e1e25",   # panneau fichiers
    "bg_grid":           "#1a1a22",   # grille des préréglages
    # Éléments de formulaire
    "input_bg":          "#2a2a35",   # fond champs, menus, boutons
    "input_border":      "#3a3a4a",   # bordure des éléments
    "input_hover":       "#4a4a5a",   # hover sur les éléments
    # Texte
    "text_primary":      "#dddddd",   # texte principal
    "text_secondary":    "#aaaaaa",   # texte secondaire
    "text_tertiary":     "#888888",   # texte tertiaire / dim
    "text_dim":          "#555555",   # très dim
    "text_placeholder":  "#555566",   # placeholder / section headers
    "text_unit":         "#666677",   # unités ("pts", "×")
    # Accents
    "accent_red":        "#e05555",   # rouge accent (titre topbar)
    "accent_blue":       "#aac4ff",   # bleu accent (filename, highlight)
    "accent_green":      "#55bb77",   # vert (bouton Appliquer, badge)
    "error_red":         "#ee5555",   # rouge erreur (badge Erreur)
    # Boutons spéciaux
    "btn_apply_hover":   "#44aa66",   # hover bouton Appliquer
    "btn_apply_text":    "#0a1a0f",   # texte bouton Appliquer
    "btn_welcome_bg":    "#2a3a5a",   # fond boutons écran d'accueil
    "btn_welcome_hover": "#3a4a6a",   # hover boutons écran d'accueil
    # États des cartes fichiers
    "card_active_bg":    "#1a2a4a",   # en cours
    "card_done_bg":      "#1a3a1a",   # traité
    "card_passe_bg":     "#252528",   # ignoré
    "card_error_bg":     "#3a1a1a",   # erreur
    # Overlay (canvas)
    "overlay_guide":     "#5577ee",   # lignes de guidage (hover)
    "preset_active":     "#2a4a7a",   # fond preset actif
    # Badge topbar
    "badge_bg":          "#222230",   # fond badges (filename, progress)
    # Valeurs par défaut (config)
    "text_default":      "#FF0000",   # couleur texte par défaut
    "frame_default":     "#000000",   # couleur cadre par défaut
    "bg_default":        "#FFFFFF",   # couleur fond par défaut
}

SIZES = {
    # Fenêtre principale
    "win_min_w":         980,
    "win_min_h":         650,
    "win_w":             1100,
    "win_h":             780,
    # Barres horizontales
    "topbar_h":          42,
    "bottombar_h":       50,
    # Panneaux latéraux
    "sidebar_w":         270,
    "file_panel_w":      220,
    # Canvas — calcul d'échelle
    "canvas_pad":        40,     # marge autour de la page (px)
    "canvas_scale_max":  2.5,    # échelle max de prévisualisation
    # Overlay — approximations texte
    "cross_radius":      5,      # rayon de la croix de positionnement (px)
    "text_char_w":       0.65,   # largeur approx. d'un caractère (× font_size)
    "text_char_h":       1.4,    # hauteur approx. d'une ligne (× font_size)
    "text_scale":        1.1,    # facteur d'échelle texte dans l'overlay
    "text_w_fallback":   0.6,    # facteur largeur fallback (sans fitz.Font)
    "underline_thick":   0.06,   # épaisseur soulignement (× font_size)
    "underline_offset":  0.15,   # décalage Y soulignement (× font_size)
    "underline_width":   0.05,   # largeur soulignement (× font_size)
    # Swatches couleur
    "swatch_w":          26,
    "swatch_h":          18,
    "swatch_sm_w":       22,
    "swatch_sm_h":       16,
    # Boutons
    "btn_size_w":        30,     # boutons ± taille police
    "btn_size_h":        26,
    "btn_preset_w":      44,     # boutons grille préréglages
    "btn_preset_h":      32,
    "btn_welcome_w":     200,    # boutons écran d'accueil
    "btn_welcome_h":     50,
    # Champs de saisie
    "entry_size_w":      46,     # champ taille police
    "entry_margin_w":    55,     # champs marges / espacement
    "entry_frame_w":     50,     # champs cadre (largeur, padding)
    "menu_font_w":       155,    # menu sélection police
    "menu_opt_w":        110,    # menus options standard
    "menu_date_fmt_w":   185,    # menu format de date
    # Wrapping texte
    "preview_wrap":      230,    # aperçu texte (sidebar)
    "card_wrap":         180,    # nom fichier dans les cartes
    # Tailles de polices UI
    "font_hint":         8,      # texte hint / coordonnées
    "font_date_fmt":     9,      # menu format de date
    "font_section":      10,     # en-têtes de section (ALLCAPS)
    "font_label":        11,     # labels standard
    "font_main":         12,     # texte principal / checkboxes
    "font_title":        14,     # titre topbar / boutons preset
    "font_welcome":      18,     # titre écran d'accueil
    # Limites config
    "font_size_min":     4,
    "font_size_max":     72,
    "line_spacing_min":  0.5,
    "frame_width_min":   0.1,
    "frame_pad_min":     0.0,
    "pos_ratio_min":     0.01,
    "pos_ratio_max":     0.99,
}

TIMINGS = {
    "update_version_timeout":  5,    # vérification version (s)
    "update_download_timeout": 15,   # téléchargement mise à jour (s)
}

DEFAULT_CONFIG = {
    # Composition du texte
    "use_filename"   : True,
    "use_prefix"     : False,
    "prefix_text"    : "",
    "use_suffix"     : False,
    "suffix_text"    : "",
    "use_custom"     : False,
    "custom_text"    : "",
    # Date
    "use_date"       : False,
    "date_position"  : "suffix",     # "prefix" | "suffix"
    "date_source"    : "today",      # "today" | "file_mtime"
    "date_format"    : "%d/%m/%Y",
    # Typographie
    "color_hex"      : COLORS["text_default"],
    "font_family"    : "Courier",
    "font_file"      : None,         # None = builtin, sinon chemin absolu (str)
    "font_size"      : 8,
    "bold"           : False,
    "italic"         : False,
    "underline"      : False,
    "letter_spacing" : 0.0,          # stocké, non appliqué au PDF en v0.4.0
    "line_spacing"   : 1.2,
    # Position
    "preset_position": "tr",
    "margin_x_pt"    : 20.0,
    "margin_y_pt"    : 20.0,
    "last_x_ratio"   : 0.85,
    "last_y_ratio"   : 0.03,
    # Rotation
    "rotation"       : 0,            # 0 | 90 | 180 | 270
    # Cadre
    "use_frame"      : False,
    "frame_color_hex": COLORS["frame_default"],
    "frame_width"    : 1.0,
    "frame_style"    : "solid",      # "solid" | "dashed"
    "frame_padding"  : 3.0,
    "frame_opacity"  : 1.0,
    # Fond
    "use_bg"         : False,
    "bg_color_hex"   : COLORS["bg_default"],
    "bg_opacity"     : 0.8,
    # Application
    "all_pages"      : True,
    "ui_font_size"   : 12,
    "debug_enabled"  : False,
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            # Migration depuis format < v0.4.0
            if "text_mode" in cfg:
                old_mode = cfg.pop("text_mode", "nom")
                old_pfx  = cfg.pop("prefixe",   "")
                old_sfx  = cfg.pop("suffixe",   "")
                old_cst  = cfg.pop("custom",    "")
                if old_mode == "prefixe" and old_pfx:
                    cfg["use_prefix"]  = True
                    cfg["prefix_text"] = old_pfx
                elif old_mode == "suffixe" and old_sfx:
                    cfg["use_suffix"]  = True
                    cfg["suffix_text"] = old_sfx
                elif old_mode == "custom":
                    cfg["use_custom"]  = True
                    cfg["custom_text"] = old_cst
                cfg.setdefault("use_filename", old_mode != "custom")
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Logging debug (contrôlé par config "debug_enabled")
# ---------------------------------------------------------------------------
_DEBUG_ENABLED = False
_DEBUG_LOG     = INSTALL_DIR / "pdf_header_debug.log"

def _debug_log(msg: str):
    if not _DEBUG_ENABLED:
        return
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Mise à jour automatique (depuis v0.4.6.1)
# Stratégie : GitHub Releases API + metadata.json + app-patch.zip
# Le patch est téléchargé dans _update_pending/ et appliqué au prochain démarrage.
# ---------------------------------------------------------------------------
def _check_update_thread():
    try:
        # 1. Dernière release stable via GitHub Releases API
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "PDFHeaderTool", "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=TIMINGS["update_version_timeout"]) as r:
            release = json.loads(r.read().decode())

        tag_name = release.get("tag_name", "")
        remote_version = tag_name.lstrip("v")
        if not remote_version or remote_version == VERSION:
            return

        # 2. Indexer les assets de la release
        assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
        meta_url = assets.get("metadata.json")
        if not meta_url:
            return  # Release sans metadata.json (ancien format) — ignorer

        # 3. Télécharger metadata.json
        req2 = urllib.request.Request(meta_url, headers={"User-Agent": "PDFHeaderTool"})
        with urllib.request.urlopen(req2, timeout=TIMINGS["update_version_timeout"]) as r:
            meta = json.loads(r.read().decode())

        # 4. Vérifier si une réinstallation complète est requise
        if meta.get("requires_full_reinstall", True):
            _debug_log(f"UPDATE_FULL_REQUIRED {VERSION} -> {remote_version}")
            return  # Futur : notification GUI (Étape 4.7+)

        # 5. Télécharger app-patch.zip
        patch_info = meta.get("patch_zip", {})
        patch_name = patch_info.get("name", "")
        patch_sha256 = patch_info.get("sha256", "")
        patch_url = assets.get(patch_name)
        if not patch_url:
            return

        req3 = urllib.request.Request(patch_url, headers={"User-Agent": "PDFHeaderTool"})
        with urllib.request.urlopen(req3, timeout=TIMINGS["update_download_timeout"]) as r:
            patch_data = r.read()

        # 6. Vérifier SHA256
        import hashlib
        actual_sha256 = hashlib.sha256(patch_data).hexdigest()
        if patch_sha256 and actual_sha256 != patch_sha256:
            _debug_log(f"UPDATE_HASH_MISMATCH expected={patch_sha256} got={actual_sha256}")
            return

        # 7. Extraire dans staging
        import zipfile, io
        staging = INSTALL_DIR / "_update_pending"
        if staging.exists():
            import shutil
            shutil.rmtree(staging)
        staging.mkdir()
        with zipfile.ZipFile(io.BytesIO(patch_data)) as zf:
            zf.extractall(staging)

        # 8. Écrire les métadonnées de contrôle
        delete_list = meta.get("delete", [])
        if delete_list:
            (staging / "_delete.json").write_text(json.dumps(delete_list))
        (staging / "_target_version.txt").write_text(remote_version)

        _debug_log(f"UPDATE_STAGED {VERSION} -> {remote_version}")

        if _update_staged_callback:
            _update_staged_callback(remote_version)

    except Exception:
        pass  # Réseau indisponible ou release malformée — silencieux

_update_staged_callback = None  # callable(version: str) | None — défini par PDFHeaderApp

def check_update():
    t = threading.Thread(target=_check_update_thread, daemon=True)
    t.start()

# ---------------------------------------------------------------------------
# Utilitaires couleur
# ---------------------------------------------------------------------------
def hex_to_rgb_float(hex_color):
    """#FF0000 → (1.0, 0.0, 0.0)"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r / 255, g / 255, b / 255

# ---------------------------------------------------------------------------
# Système de polices — hybride : built-in PDF + prioritaires système
# ---------------------------------------------------------------------------
BUILTIN_FONTS = {
    "Courier":   {("r",): "cour",  ("b",): "courB",  ("i",): "courI",  ("b","i"): "courBI"},
    "Helvetica": {("r",): "helv",  ("b",): "helvB",  ("i",): "helvO",  ("b","i"): "helvBO"},
    "Times":     {("r",): "tiro",  ("b",): "tiroB",  ("i",): "tiroI",  ("b","i"): "tiroBI"},
}

PRIORITY_FONTS = {
    "win32": [
        ("Arial",           "arial"),
        ("Calibri",         "calibri"),
        ("Verdana",         "verdana"),
        ("Georgia",         "georgia"),
        ("Times New Roman", "times new roman"),
    ],
    "darwin": [
        ("Helvetica Neue",  "helveticaneue"),
        ("Arial",           "arial"),
        ("Georgia",         "georgia"),
    ],
    "linux": [
        ("DejaVu Sans",     "DejaVuSans"),
        ("Liberation Sans", "LiberationSans-Regular"),
        ("Noto Sans",       "NotoSans-Regular"),
        ("Ubuntu",          "Ubuntu-R"),
        ("Roboto",          "Roboto-Regular"),
        ("Lato",            "Lato-Regular"),
    ],
}

# Grille 3×3 : clé → (row, col)
POSITION_PRESETS = {
    "tl": (0, 0), "tc": (0, 1), "tr": (0, 2),
    "ml": (1, 0), "mc": (1, 1), "mr": (1, 2),
    "bl": (2, 0), "bc": (2, 1), "br": (2, 2),
}
PRESET_LABELS = {
    "tl": "↖", "tc": "↑", "tr": "↗",
    "ml": "←", "mc": "·", "mr": "→",
    "bl": "↙", "bc": "↓", "br": "↘",
}

DATE_FORMATS = [
    ("%d/%m/%Y",       "ex: 20/02/2026"),
    ("%Y-%m-%d",       "ex: 2026-02-20"),
    ("%d %B %Y",       "ex: 20 février 2026"),
    ("%B %Y",          "ex: février 2026"),
    ("%Y",             "ex: 2026"),
    ("%d/%m/%Y %H:%M", "ex: 20/02/2026 14:30"),
    ("%d %b %Y",       "ex: 20 fév. 2026"),
    ("%A %d %B %Y",    "ex: vendredi 20 février 2026"),
]

# Libellés UI pour les sources de date (interne → affiché)
DATE_SOURCE_DISPLAY = {
    "today":      "Date du jour",
    "file_mtime": "Date de création fichier",
}
DATE_SOURCE_INTERNAL = {v: k for k, v in DATE_SOURCE_DISPLAY.items()}

# Fonctionnalités masquées dans l'UI pour la v0.4.x (logique conservée)
_HIDDEN_UI_FEATURES = {
    "letter_spacing",
    "line_spacing",
    "position_grid",
    "margins",
    "rotation",
    "frame",
    "background",
}

def _get_font_dirs() -> list:
    """Retourne les dossiers de polices système selon la plateforme."""
    if sys.platform == "win32":
        win_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        dirs = [win_fonts]
        local_fonts = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
        if local_fonts.exists():
            dirs.append(local_fonts)
        return dirs
    elif sys.platform == "darwin":
        return [
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ]
    else:
        return [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local" / "share" / "fonts",
        ]

def _find_priority_fonts() -> dict:
    """
    Cherche les polices prioritaires connues sur le système.
    Retourne {display_name: Path}. Pas de scan exhaustif.
    """
    platform_key = sys.platform if sys.platform in PRIORITY_FONTS else "linux"
    candidates   = PRIORITY_FONTS[platform_key]
    font_dirs    = _get_font_dirs()
    found        = {}
    extensions   = (".ttf", ".otf", ".TTF", ".OTF")
    for display_name, filename_stem in candidates:
        for font_dir in font_dirs:
            if not font_dir.exists():
                continue
            for ext in extensions:
                candidate = font_dir / (filename_stem + ext)
                if candidate.exists():
                    found[display_name] = candidate
                    break
            if display_name in found:
                break
    return found

def _get_fitz_font_args(family: str, font_file, bold: bool, italic: bool) -> dict:
    """
    Retourne les kwargs de police pour insert_textbox().
    Priorité : font_file (système) > BUILTIN_FONTS > fallback Courier.
    """
    if font_file and Path(str(font_file)).exists():
        return {"fontfile": str(font_file), "fontname": "F0"}
    if family in BUILTIN_FONTS:
        variants = BUILTIN_FONTS[family]
        if bold and italic:
            key = ("b", "i")
        elif bold:
            key = ("b",)
        elif italic:
            key = ("i",)
        else:
            key = ("r",)
        fontname = variants.get(key) or variants.get(("r",), "cour")
        return {"fontname": fontname}
    return {"fontname": "cour"}

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
        self.root      = root
        self.pdf_files = list(pdf_files) if pdf_files else []
        self.idx       = 0
        self.cfg       = load_config()

        global _DEBUG_ENABLED
        _DEBUG_ENABLED = self.cfg.get("debug_enabled", False)

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

        global _update_staged_callback
        _update_staged_callback = lambda v: self.root.after(0, lambda: self._show_update_notice(v))

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

    # ------------------------------------------------------------------ UI ---

    def _show_update_notice(self, version: str):
        """Affiche un badge dans la topbar quand un patch est stagé et prêt."""
        self.lbl_update.configure(text=f"  Mise a jour v{version} disponible — relancez l'app  ")
        self.lbl_update.pack(side="right", padx=8, pady=6)

    def _build_ui(self):
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
        """Séparateur de section dans la sidebar."""
        ctk.CTkLabel(parent, text=label,
                     fg_color="transparent", text_color=COLORS["text_placeholder"],
                     font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkFrame(parent, fg_color=COLORS["input_border"], height=1,
                     corner_radius=0).pack(fill="x", padx=14)

    def _build_sidebar(self, parent):
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
        for frame in self.file_card_frames.values():
            frame.destroy()
        self.file_card_frames = {}
        self.file_card_badges = {}
        for i, path in enumerate(self.pdf_files):
            self._create_file_card(i, path)
        self._refresh_file_counter()

    def _create_file_card(self, idx, path):
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
        for i in range(len(self.pdf_files)):
            self._refresh_card(i)
        self._refresh_file_counter()

    def _refresh_file_counter(self):
        done = sum(1 for s in self.file_states.values() if s in ("traite", "passe"))
        total = len(self.pdf_files)
        self.lbl_file_counter.configure(text=f"{done} / {total} fichiers traités")

    def _find_next_untreated(self):
        n = len(self.pdf_files)
        for offset in range(1, n):
            i = (self.idx + offset) % n
            if self.file_states.get(i, "non_traite") == "non_traite":
                return i
        return None

    def _jump_to_file(self, idx):
        self.idx = idx
        self._load_pdf()

    # --------------------------------------------------- Écran d'accueil ---

    def _show_welcome_screen(self):
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
        if hasattr(self, "welcome_frame") and self.welcome_frame.winfo_exists():
            self.welcome_frame.destroy()
        self._set_ui_state(True)

    def _set_ui_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.btn_apply.configure(state=state)
        self.btn_skip.configure(state=state)
        for w in self._sidebar_interactive:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _open_files(self):
        paths = filedialog.askopenfilenames(
            title="Sélectionner des fichiers PDF",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not paths:
            return
        self.pdf_files = [Path(p) for p in paths]
        self.file_states = {i: "non_traite" for i in range(len(self.pdf_files))}
        self.idx = 0
        self._populate_file_panel()
        self._hide_welcome_screen()
        self._load_pdf()

    def _open_folder(self):
        folder = filedialog.askdirectory(title="Sélectionner le dossier contenant les PDFs")
        if not folder:
            return
        self.pdf_files = sorted(Path(folder).glob("*.pdf"))
        if not self.pdf_files:
            messagebox.showwarning("Aucun fichier", "Aucun fichier PDF trouvé dans ce dossier.")
            return
        self.file_states = {i: "non_traite" for i in range(len(self.pdf_files))}
        self.idx = 0
        self._populate_file_panel()
        self._hide_welcome_screen()
        self._load_pdf()

    # ------------------------------------------- Callbacks sidebar texte ---

    def _on_text_change(self, *_):
        """Rafraîchit l'aperçu texte et le canvas overlay."""
        self.lbl_preview.configure(text=self._get_header_text())
        self._draw_overlay()

    def _on_use_custom_change(self, *_):
        """Quand 'Texte personnalisé' est activé, désactive 'Nom du fichier'."""
        if self.var_use_custom.get():
            self.var_use_filename.set(False)
        self._on_text_change()

    def _on_date_toggle(self, *_):
        self._update_date_options_visibility()
        self._on_text_change()

    def _update_date_options_visibility(self):
        if self.var_use_date.get():
            self._date_options_frame.pack(fill="x", padx=4, after=self._cb_date)
        else:
            self._date_options_frame.pack_forget()

    def _on_date_format_change(self, display_value: str):
        fmt = self._date_format_map.get(display_value, "%d/%m/%Y")
        self.var_date_format.set(fmt)
        self._on_text_change()

    def _on_frame_toggle(self, *_):
        self._update_frame_options_visibility()
        self._on_text_change()

    def _update_frame_options_visibility(self):
        if "frame" in _HIDDEN_UI_FEATURES:
            return
        if self.var_use_frame.get():
            self._frame_options_frame.pack(fill="x", padx=4, after=self._cb_frame)
        else:
            self._frame_options_frame.pack_forget()

    def _on_bg_toggle(self, *_):
        self._update_bg_options_visibility()
        self._on_text_change()

    def _update_bg_options_visibility(self):
        if "background" in _HIDDEN_UI_FEATURES:
            return
        if self.var_use_bg.get():
            self._bg_options_frame.pack(fill="x", padx=4, after=self._cb_bg)
        else:
            self._bg_options_frame.pack_forget()

    def _update_opacity_labels(self):
        try:
            self.lbl_frame_opacity.configure(text=f"{int(self.var_frame_opacity.get()*100)}%")
            self.lbl_bg_opacity.configure(text=f"{int(self.var_bg_opacity.get()*100)}%")
        except Exception:
            pass
        self._draw_overlay()

    def _on_font_change(self, font_name: str):
        if font_name in self._system_fonts:
            self.cfg["font_file"] = str(self._system_fonts[font_name])
        else:
            self.cfg["font_file"] = None
        self._on_text_change()

    # --------------------------------------------------- Couleurs (picks) ---

    def _pick_color(self, _=None):
        color = colorchooser.askcolor(color=self.cfg["color_hex"],
                                      title="Couleur du texte")
        if color and color[1]:
            self.cfg["color_hex"] = color[1].upper()
            self.color_swatch.config(bg=self.cfg["color_hex"])
            self.lbl_color_hex.configure(text=self.cfg["color_hex"])
            self._draw_overlay()

    def _pick_frame_color(self, _=None):
        color = colorchooser.askcolor(color=self.cfg.get("frame_color_hex", COLORS["frame_default"]),
                                      title="Couleur du cadre")
        if color and color[1]:
            self.cfg["frame_color_hex"] = color[1].upper()
            self.frame_color_swatch.config(bg=self.cfg["frame_color_hex"])
            self.lbl_frame_color.configure(text=self.cfg["frame_color_hex"])
            self._draw_overlay()

    def _pick_bg_color(self, _=None):
        color = colorchooser.askcolor(color=self.cfg.get("bg_color_hex", COLORS["bg_default"]),
                                      title="Couleur du fond")
        if color and color[1]:
            self.cfg["bg_color_hex"] = color[1].upper()
            self.bg_color_swatch.config(bg=self.cfg["bg_color_hex"])
            self.lbl_bg_color.configure(text=self.cfg["bg_color_hex"])
            self._draw_overlay()

    def _change_size(self, delta):
        val = max(SIZES["font_size_min"], min(SIZES["font_size_max"], self.var_size.get() + delta))
        self.var_size.set(val)
        self._on_text_change()

    # ----------------------------------------------- Presets de position ---

    def _on_preset_click(self, preset_key: str):
        self.preset_position = preset_key
        self._recalc_ratio_from_preset()
        self._update_preset_highlight()
        self._update_pos_label()
        self._draw_overlay()

    def _recalc_ratio_from_preset(self):
        """Recalcule pos_ratio_x/y depuis le preset actif et les marges."""
        if self.preset_position == "custom":
            return
        if self.preset_position not in POSITION_PRESETS:
            return
        try:
            mx = float(self.var_margin_x.get())
            my = float(self.var_margin_y.get())
        except (ValueError, AttributeError):
            mx, my = 20.0, 20.0
        pw = max(self.page_w_pt, 1.0)
        ph = max(self.page_h_pt, 1.0)
        row_n, col_n = POSITION_PRESETS[self.preset_position]
        if col_n == 0:
            rx = mx / pw
        elif col_n == 1:
            rx = 0.5
        else:
            rx = 1.0 - mx / pw
        if row_n == 0:
            ry = my / ph
        elif row_n == 1:
            ry = 0.5
        else:
            ry = 1.0 - my / ph
        self.pos_ratio_x = max(SIZES["pos_ratio_min"], min(SIZES["pos_ratio_max"], rx))
        self.pos_ratio_y = max(SIZES["pos_ratio_min"], min(SIZES["pos_ratio_max"], ry))

    def _on_margins_change(self, *_):
        """Recalcule la position si on est en mode preset."""
        if self.preset_position != "custom":
            self._recalc_ratio_from_preset()
            self._update_pos_label()
            self._draw_overlay()

    def _update_preset_highlight(self):
        """Met en surbrillance le bouton preset actif."""
        if not hasattr(self, "_preset_buttons"):
            return
        for key, btn in self._preset_buttons.items():
            if key == self.preset_position:
                btn.configure(fg_color=COLORS["preset_active"], text_color=COLORS["accent_blue"])
            else:
                btn.configure(fg_color=COLORS["input_bg"], text_color=COLORS["text_primary"])

    # ----------------------------------------------- Composition du texte ---

    def _get_header_text(self) -> str:
        """Assemble le texte d'en-tête selon les options actives."""
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
        path = self.pdf_files[self.idx]
        self.lbl_filename.configure(text=f"  {path.name}  ")
        self.lbl_progress.configure(text=f"  {self.idx + 1} / {len(self.pdf_files)}  ")
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(str(path))
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
        if not self.doc:
            return
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

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)

        self.img_offset_x = (cw - pix.width)  // 2
        self.img_offset_y = (ch - pix.height) // 2

        self.canvas.delete("all")
        self.canvas.create_image(self.img_offset_x, self.img_offset_y,
                                 anchor="nw", image=self.tk_img, tags="page")
        self._draw_overlay()

    def _draw_overlay(self, hover_cx=None, hover_cy=None):
        if not hasattr(self, "canvas"):
            return
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
        rx = (cx - self.img_offset_x) / max(self.page_w_px, 1)
        ry = (cy - self.img_offset_y) / max(self.page_h_px, 1)
        return max(0.0, min(1.0, rx)), max(0.0, min(1.0, ry))

    def _ratio_to_canvas(self, rx, ry):
        cx = self.img_offset_x + rx * self.page_w_px
        cy = self.img_offset_y + ry * self.page_h_px
        return cx, cy

    def _ratio_to_pdf_pt(self, rx, ry):
        """Ratio → coordonnées PDF en points (Y=0 en bas)."""
        x_pt = rx * self.page_w_pt
        y_pt = (1.0 - ry) * self.page_h_pt
        return x_pt, y_pt

    def _on_click(self, event):
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
        self._update_pos_label()
        self._draw_overlay()

    def _on_motion(self, event):
        self._draw_overlay(hover_cx=event.x, hover_cy=event.y)
        rx, ry = self._canvas_to_ratio(event.x, event.y)
        x_pt, y_pt = self._ratio_to_pdf_pt(rx, ry)
        self.lbl_coords.configure(text=f"x: {x_pt:.0f} pts  ·  y: {y_pt:.0f} pts")

    def _update_pos_label(self):
        x_pt, y_pt = self._ratio_to_pdf_pt(self.pos_ratio_x, self.pos_ratio_y)
        preset_label = PRESET_LABELS.get(self.preset_position, "libre")
        self.lbl_pos.configure(
            text=f"[{preset_label}]  x: {x_pt:.0f} pts  y: {y_pt:.0f} pts"
        )

    # ------------------------------------------------------------ Actions ---

    def _apply(self):
        path     = self.pdf_files[self.idx]
        out_dir  = path.parent.with_name(path.parent.name + "_avec_entete")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / path.name

        header_text = self._get_header_text()
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

        try:
            doc_out = fitz.open(str(path))
            pages_to_process = range(len(doc_out)) if all_pages else [0]

            _debug_log(
                f"APPLY [{path.name}] ratio=({self.pos_ratio_x:.4f},{self.pos_ratio_y:.4f}) "
                f"x_pt={x_pt:.1f} y_pt={y_pt:.1f} rotation={rotation} font={font_family}"
            )

            for i in pages_to_process:
                pg   = doc_out[i]
                pg_w = pg.rect.width
                pg_h = pg.rect.height
                # Conversion Y : fitz (Y=0 en haut)
                fitz_y = pg_h - y_pt

                # Estimation largeur texte pour fond/cadre/soulignement
                text_width = len(header_text) * font_size * SIZES["text_w_fallback"]  # fallback
                if use_bg or use_frame or underline:
                    try:
                        if "fontfile" in font_args:
                            font_obj = fitz.Font(fontfile=font_args["fontfile"])
                        else:
                            font_obj = fitz.Font(fontname=font_args.get("fontname", "cour"))
                        text_width = font_obj.text_length(header_text, font_size)
                    except Exception:
                        pass

                # half_h : demi-hauteur d'une ligne — sert à centrer texte/cadre/fond sur fitz_y
                lineheight = line_spacing  # facteur multiplicateur de fontsize (ex: 1.2 → 1.2×12=14.4 pts)
                half_h = font_size * lineheight / 2

                # Fond et cadre (avant le texte) — centrés sur (x_pt, fitz_y)
                if use_bg or use_frame:
                    pad = frame_padding
                    bg_rect = fitz.Rect(
                        x_pt - text_width / 2 - pad,
                        fitz_y - half_h - pad,
                        x_pt + text_width / 2 + pad,
                        fitz_y + half_h + pad
                    )
                    if use_bg:
                        pg.draw_rect(bg_rect,
                                     fill=bg_color,
                                     fill_opacity=bg_opacity,
                                     color=None,
                                     width=0)
                    if use_frame:
                        dashes = "[3 3] 0" if frame_style == "dashed" else None
                        pg.draw_rect(bg_rect,
                                     color=frame_color,
                                     width=frame_width,
                                     stroke_opacity=frame_opacity,
                                     fill=None,
                                     dashes=dashes)

                # Rect d'insertion du texte — centré sur (x_pt, fitz_y)
                # y0 = fitz_y - half_h → insert_textbox remplit vers le bas sur font_size*lineheight
                # → centre visuel du texte ≈ fitz_y, cohérent avec l'overlay (anchor="center")
                half_w = max(pg_w / 2, text_width / 2 + 10)
                text_rect = fitz.Rect(
                    max(0, x_pt - half_w),
                    fitz_y - half_h,
                    min(pg_w, x_pt + half_w),
                    fitz_y + half_h * 2   # marge extra en bas pour éviter toute troncature
                )
                _debug_log(
                    f"  page[{i}] pg=({pg_w:.1f}x{pg_h:.1f}) "
                    f"fitz_y={fitz_y:.1f} text_rect={text_rect}"
                )

                pg.insert_textbox(
                    text_rect,
                    header_text,
                    fontsize=font_size,
                    color=color_float,
                    rotate=rotation,
                    lineheight=lineheight,
                    align=fitz.TEXT_ALIGN_CENTER,
                    **font_args,
                )

                # Soulignement — centré sur x_pt
                if underline:
                    ul_y = fitz_y + font_size * SIZES["underline_offset"]
                    pg.draw_line(
                        fitz.Point(x_pt - text_width / 2, ul_y),
                        fitz.Point(x_pt + text_width / 2, ul_y),
                        color=color_float,
                        width=max(0.5, font_size * SIZES["underline_width"])
                    )

            doc_out.save(str(out_path), garbage=4, deflate=True)
            doc_out.close()

        except PermissionError:
            messagebox.showerror("Erreur",
                "Le fichier est ouvert dans un autre programme. Fermez-le et réessayez.")
            self.file_states[self.idx] = "erreur"
            self._refresh_all_cards()
            return
        except Exception as e:
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
        save_config(self.cfg)

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
    check_update()

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
