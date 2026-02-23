# ==============================================================================
# app/config.py — Chargement, sauvegarde et migration de la configuration
# Déplacé depuis pdf_header.py lors de l'Étape 4.7 (substep-2)
# Dépendances : json, pathlib, logging (stdlib uniquement)
# ==============================================================================

import json
import logging
from pathlib import Path

from app.constants import COLORS

log_config = logging.getLogger("pdf_header.config")

# ---------------------------------------------------------------------------
# Configuration par défaut
# ---------------------------------------------------------------------------
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
    "log_profile"    : "simple",     # "simple" | "medium" | "full"
}


def load_config(install_dir: Path) -> dict:
    """Charge la config JSON depuis install_dir, applique les valeurs par défaut de DEFAULT_CONFIG,
    migre les anciens formats (text_mode < v0.4.0, debug_enabled < v0.4.6.11).
    Retourne le dict cfg complet. Retourne une copie de DEFAULT_CONFIG en cas d'erreur.
    """
    config_file = install_dir / "pdf_header_config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
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
            # Migration debug_enabled (bool) → log_profile (str) depuis v0.4.6.11
            if "debug_enabled" in cfg and "log_profile" not in cfg:
                cfg["log_profile"] = "medium" if cfg.pop("debug_enabled") else "simple"
            elif "debug_enabled" in cfg:
                cfg.pop("debug_enabled")
            log_config.info(f"CONFIG_LOAD ok path={config_file}")
            return cfg
        except Exception as e:
            log_config.error(f"CONFIG_LOAD_ERROR error={e}")
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict, install_dir: Path) -> None:
    """Sauvegarde le dict cfg dans pdf_header_config.json (install_dir).
    Ne lève pas d'exception — log en cas d'erreur d'écriture.
    """
    config_file = install_dir / "pdf_header_config.json"
    try:
        install_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        log_config.info("CONFIG_SAVE ok")
    except Exception as e:
        log_config.error(f"CONFIG_SAVE_ERROR error={e}")
