# ==============================================================================
# app/services/layout_service.py — Calculs géométriques canvas/ratio/PDF
# Déplacé depuis pdf_header.py lors de l'Étape 4.7 (substep-3)
# Dépendances : app.constants uniquement (stdlib pure — aucun import lourd)
# ==============================================================================

from app.constants import POSITION_PRESETS, SIZES


def canvas_to_ratio(
    cx: float, cy: float,
    img_offset_x: float, img_offset_y: float,
    page_w_px: float, page_h_px: float,
) -> tuple:
    """Coordonnées canvas (px) → ratio page [0.0-1.0], clampé aux bornes."""
    rx = (cx - img_offset_x) / max(page_w_px, 1)
    ry = (cy - img_offset_y) / max(page_h_px, 1)
    return max(0.0, min(1.0, rx)), max(0.0, min(1.0, ry))


def ratio_to_canvas(
    rx: float, ry: float,
    img_offset_x: float, img_offset_y: float,
    page_w_px: float, page_h_px: float,
) -> tuple:
    """Ratio page [0.0-1.0] → coordonnées canvas (px absolues)."""
    cx = img_offset_x + rx * page_w_px
    cy = img_offset_y + ry * page_h_px
    return cx, cy


def ratio_to_pdf_pt(
    rx: float, ry: float,
    page_w_pt: float, page_h_pt: float,
) -> tuple:
    """Ratio → coordonnées PDF en points (Y=0 en bas, système fitz).
    Système de coordonnées fitz : origine bas-gauche, Y croît vers le haut.
    tkinter : origine haut-gauche, Y croît vers le bas.
    Conversion Y : fitz_y = (1.0 - ratio_y) * page_h_pt
    """
    x_pt = rx * page_w_pt
    y_pt = (1.0 - ry) * page_h_pt
    return x_pt, y_pt


def recalc_ratio_from_preset(
    preset_key: str,
    margin_x_pt: float, margin_y_pt: float,
    page_w_pt: float, page_h_pt: float,
) -> tuple:
    """Calcule les ratios (rx, ry) depuis un preset de position + marges en points PDF.
    Retourne (ratio_x, ratio_y) clampé dans [pos_ratio_min, pos_ratio_max].
    L'appelant est responsable de vérifier que preset_key != 'custom'
    et que preset_key est dans POSITION_PRESETS.
    """
    pw = max(page_w_pt, 1.0)
    ph = max(page_h_pt, 1.0)
    row_n, col_n = POSITION_PRESETS[preset_key]
    if col_n == 0:
        rx = margin_x_pt / pw
    elif col_n == 1:
        rx = 0.5
    else:
        rx = 1.0 - margin_x_pt / pw
    if row_n == 0:
        ry = margin_y_pt / ph
    elif row_n == 1:
        ry = 0.5
    else:
        ry = 1.0 - margin_y_pt / ph
    lo = SIZES["pos_ratio_min"]
    hi = SIZES["pos_ratio_max"]
    return max(lo, min(hi, rx)), max(lo, min(hi, ry))
