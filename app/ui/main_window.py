# ==============================================================================
# app/ui/main_window.py — Main window class
# [CODEX] Step 4.7.6: lifecycle/canvas/apply logic moved from pdf_header.py
# ==============================================================================

import datetime
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import fitz
from PIL import Image, ImageTk

from app.config import load_config, save_config
from app.constants import (
    COLORS,
    DATE_SOURCE_INTERNAL,
    PRESET_LABELS,
    SIZES,
)
from app.runtime import (
    debug_log as _debug_log,
    default_log_profile as _default_log_profile,
    get_install_dir,
    get_version,
    log_font,
    log_pdf,
    log_session_start as _log_session_start,
    log_ui,
    setup_logger as _setup_logger,
)
from app.services.font_service import (
    _find_priority_fonts,
    _get_fitz_font_args,
    hex_to_rgb_float,
)
from app.services.layout_service import canvas_to_ratio, ratio_to_canvas, ratio_to_pdf_pt
from app.services.pdf_service import insert_header
from app.ui.file_panel import FilePanelMixin
from app.ui.sidebar import SidebarMixin
from app.update import set_staged_callback

INSTALL_DIR = get_install_dir()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PDFHeaderApp(FilePanelMixin, SidebarMixin):
    def __init__(self, root, pdf_files=None):
        """Initialise l'état de l'app, charge la config, les polices système, construit l'UI.
        Charge le premier PDF si passé en argument, sinon affiche l'écran d'accueil.
        """
        self.root      = root
        self.pdf_files = list(pdf_files) if pdf_files else []
        self.idx       = 0
        self.version   = get_version()
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

        ctk.CTkLabel(topbar, text=f"v{self.version}",
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
