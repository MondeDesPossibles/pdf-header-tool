# ==============================================================================
# app/services/font_service.py — Utilitaires couleur et gestion des polices
# Déplacé depuis pdf_header.py lors de l'Étape 4.7 (substep-3)
# Dépendances : os, sys, logging, pathlib (stdlib) + app.constants
# ==============================================================================

import os
import sys
import logging
from pathlib import Path

from app.constants import BUILTIN_FONTS, PRIORITY_FONTS

log_font = logging.getLogger("pdf_header.font")


# ---------------------------------------------------------------------------
# Utilitaires couleur
# ---------------------------------------------------------------------------
def hex_to_rgb_float(hex_color: str) -> tuple:
    """#FF0000 → (1.0, 0.0, 0.0)"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r / 255, g / 255, b / 255


# ---------------------------------------------------------------------------
# Système de polices — hybride : built-in PDF + prioritaires système
# ---------------------------------------------------------------------------
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
    Priorité : BUILTIN_FONTS > font_file (legacy) > fallback Courier.
    """
    if family in BUILTIN_FONTS:
        variants = BUILTIN_FONTS[family]
        if bold and italic:
            key = ("b", "i")
            style = "bold+italic"
        elif bold:
            key = ("b",)
            style = "bold"
        elif italic:
            key = ("i",)
            style = "italic"
        else:
            key = ("r",)
            style = "regular"
        fontname = variants.get(key) or variants.get(("r",), "courier")
        log_font.debug(
            f"FONT_RESOLVE family={family} source=builtin style={style} "
            f"fontname={fontname}"
        )
        return {"fontname": fontname}

    if font_file and Path(str(font_file)).exists():
        log_font.debug(
            f"FONT_RESOLVE family={family} source=fontfile fontfile={font_file} "
            "reason=family_not_builtin"
        )
        return {"fontfile": str(font_file), "fontname": "F0"}

    if font_file:
        log_font.warning(
            f"FONT_RESOLVE_FALLBACK family={family} reason=font_file_missing "
            f"fontfile={font_file}"
        )
    else:
        log_font.warning(f"FONT_RESOLVE_FALLBACK family={family} reason=unknown_family")
    return {"fontname": "courier"}
