# ==============================================================================
# app/services/pdf_service.py — Insertion de l'en-tête sur une page PyMuPDF
# Déplacé depuis pdf_header.py/_apply() lors de l'Étape 4.7 (substep-4)
# Dépendances : fitz (PyMuPDF), logging, app.constants
# ==============================================================================

import logging

import fitz

from app.constants import SIZES

log_pdf = logging.getLogger("pdf_header.pdf")


def insert_header(
    page,
    header_text: str,
    x_pt: float, y_pt: float,
    font_args: dict,
    font_size: float,
    line_spacing: float,
    color_float: tuple,
    rotation: int,
    use_bg: bool, bg_color: tuple, bg_opacity: float,
    use_frame: bool, frame_color: tuple, frame_width: float,
    frame_style: str, frame_padding: float, frame_opacity: float,
    underline: bool,
) -> dict:
    """Insère l'en-tête sur une page PyMuPDF.

    Retourne un dict :
      remaining_chars (float)  — valeur brute de insert_textbox() (<0 si tronqué)
      truncated       (bool)
      text_width      (float)  — largeur en pts (précise si fitz.Font disponible, fallback sinon)
      text_rect       (fitz.Rect)
      fitz_y          (float)  — Y insertion dans l'espace fitz (bas-gauche)
      lineheight      (float)  — facteur multiplicateur de font_size
    """
    pg_w = page.rect.width
    pg_h = page.rect.height
    # y_pt = (1.0 - ratio_y) * pg_h → espace coords fitz (Y inversé vs tkinter)
    # fitz_y = pg_h - y_pt → position absolue depuis le bas de la page
    fitz_y = pg_h - y_pt

    # Calcul précis de la largeur du texte (fallback si fitz.Font indisponible)
    text_width = len(header_text) * font_size * SIZES["text_w_fallback"]
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
            page.draw_rect(bg_rect,
                           fill=bg_color,
                           fill_opacity=bg_opacity,
                           color=None,
                           width=0)
        if use_frame:
            dashes = "[3 3] 0" if frame_style == "dashed" else None
            page.draw_rect(bg_rect,
                           color=frame_color,
                           width=frame_width,
                           stroke_opacity=frame_opacity,
                           fill=None,
                           dashes=dashes)

    # half_w : min = moitié de page pour éviter troncature si texte long.
    # L'alignement CENTER dans insert_textbox() centre le texte dans ce rect.
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
    log_pdf.debug(
        f"PAGE pg=({pg_w:.1f}x{pg_h:.1f}) "
        f"fitz_y={fitz_y:.1f} text_rect={text_rect}"
    )

    remaining = page.insert_textbox(
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
        page.draw_line(
            fitz.Point(x_pt - text_width / 2, ul_y),
            fitz.Point(x_pt + text_width / 2, ul_y),
            color=color_float,
            width=max(0.5, font_size * SIZES["underline_width"])
        )

    return {
        "remaining_chars": remaining,
        "truncated":        remaining < 0,
        "text_width":       text_width,
        "text_rect":        text_rect,
        "fitz_y":           fitz_y,
        "lineheight":       lineheight,
    }
