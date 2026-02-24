# ==============================================================================
# app/ui/sidebar.py — Sidebar builder + callbacks mixin
# [CODEX] Step 4.7.6: methods extracted from PDFHeaderApp
# ==============================================================================

import tkinter as tk
from tkinter import colorchooser

import customtkinter as ctk

from app.constants import (
    BUILTIN_FONTS,
    COLORS,
    DATE_FORMATS,
    DATE_SOURCE_DISPLAY,
    DATE_SOURCE_INTERNAL,
    POSITION_PRESETS,
    PRESET_LABELS,
    SIZES,
    _HIDDEN_UI_FEATURES,
)
from app.runtime import log_ui
from app.services.layout_service import recalc_ratio_from_preset


class SidebarMixin:
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
        all_font_names = list(BUILTIN_FONTS.keys())
        current_family = cfg.get("font_family", "Courier")
        if current_family not in all_font_names:
            current_family = "Courier"
            self.cfg["font_file"] = None
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
