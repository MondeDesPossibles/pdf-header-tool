# ==============================================================================
# PDF Header Tool — pdf_header.py
# Version : 0.0.1
# Build   : build-2026.02.20.16
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

VERSION     = "0.0.1"
BUILD_ID    = "build-2026.02.20.16"
GITHUB_REPO = "MondeDesPossibles/pdf-header-tool"

import sys
import os
import json
import shutil
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap : venv + dépendances
# ---------------------------------------------------------------------------
def _get_install_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PDFHeaderTool"
    return Path(__file__).parent

def _bootstrap():
    install_dir = _get_install_dir()
    venv_dir    = install_dir / ".venv"
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    # Déjà dans le venv ?
    if Path(sys.executable).resolve() == venv_python.resolve():
        return

    # Créer le venv si nécessaire
    if not venv_python.exists():
        import venv as _venv
        print("Création de l'environnement virtuel…")
        _venv.create(str(venv_dir), with_pip=True)

    # Installer les dépendances manquantes
    import subprocess
    pkgs = ["pymupdf", "Pillow", "customtkinter"]
    for pkg in pkgs:
        try:
            dist_name = {"pymupdf": "fitz", "Pillow": "PIL", "customtkinter": "customtkinter"}.get(pkg, pkg.lower())
            subprocess.check_call(
                [str(venv_python), "-c", f"import {dist_name}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            print(f"Installation de {pkg}…")
            subprocess.check_call(
                [str(venv_python), "-m", "pip", "install", pkg, "--quiet"],
            )

    # Relancer dans le venv
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

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
INSTALL_DIR  = _get_install_dir()
CONFIG_FILE  = INSTALL_DIR / "pdf_header_config.json"

DEFAULT_CONFIG = {
    "text_mode"   : "nom",       # nom | prefixe | suffixe | custom
    "prefixe"     : "",
    "suffixe"     : "",
    "custom"      : "",
    "color_hex"   : "#FF0000",
    "font_size"   : 8,
    "all_pages"   : True,
    "last_x_ratio": 0.85,        # position mémorisée en ratio (0-1)
    "last_y_ratio": 0.97,
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Fusionner avec les valeurs par défaut pour les clés manquantes
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
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
# Mise à jour automatique
# ---------------------------------------------------------------------------
def _check_update_thread():
    """Vérifie GitHub en arrière-plan, met à jour si nouvelle version."""
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.txt"
        req = urllib.request.Request(url, headers={"User-Agent": "PDFHeaderTool"})
        with urllib.request.urlopen(req, timeout=5) as r:
            remote_version = r.read().decode().strip()

        if remote_version == VERSION:
            return

        # Nouvelle version disponible — télécharger pdf_header.py
        script_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/pdf_header.py"
        req2 = urllib.request.Request(script_url, headers={"User-Agent": "PDFHeaderTool"})
        with urllib.request.urlopen(req2, timeout=15) as r:
            new_content = r.read()

        # Écrire dans un fichier temporaire puis remplacer
        script_path = Path(__file__).resolve()
        tmp = script_path.with_suffix(".tmp")
        tmp.write_bytes(new_content)
        tmp.replace(script_path)
        print(f"Mise à jour effectuée : {VERSION} → {remote_version}. Relancez l'application.")

    except Exception:
        pass  # Pas de réseau ou repo indisponible, on ignore silencieusement

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
# Thème CustomTkinter
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Application principale
# ---------------------------------------------------------------------------
class PDFHeaderApp:
    def __init__(self, root, pdf_files):
        self.root      = root
        self.pdf_files = pdf_files
        self.idx       = 0
        self.cfg       = load_config()

        # État courant
        self.doc           = None
        self.tk_img        = None
        self.scale         = 1.0
        self.img_offset_x  = 0
        self.img_offset_y  = 0
        self.page_w_pt     = 1.0   # largeur page en points PDF
        self.page_h_pt     = 1.0   # hauteur page en points PDF
        self.page_w_px     = 1     # largeur rendu en pixels
        self.page_h_px     = 1

        # Position en ratio (0-1) de la page PDF
        self.pos_ratio_x = self.cfg.get("last_x_ratio", 0.85)
        self.pos_ratio_y = self.cfg.get("last_y_ratio", 0.97)

        self._build_ui()
        self.root.update_idletasks()
        self._load_pdf()

    # ------------------------------------------------------------------ UI ---

    def _build_ui(self):
        self.root.title("PDF Header Tool")
        self.root.configure(fg_color="#1a1a1f")
        self.root.minsize(900, 650)

        # ── Topbar ──
        topbar = ctk.CTkFrame(self.root, fg_color="#111116", height=42, corner_radius=0)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="PDF HEADER TOOL",
                     fg_color="transparent", text_color="#e05555",
                     font=("Courier New", 12, "bold")).pack(side="left", padx=14)

        self.lbl_filename = ctk.CTkLabel(topbar, text="",
                                         fg_color="#222230", text_color="#aac4ff",
                                         font=("Courier New", 11), corner_radius=4)
        self.lbl_filename.pack(side="left", padx=8, pady=6)

        self.lbl_progress = ctk.CTkLabel(topbar, text="",
                                         fg_color="#222230", text_color="#aaaaaa",
                                         font=("Courier New", 10), corner_radius=4)
        self.lbl_progress.pack(side="right", padx=14, pady=6)

        # ── Corps ──
        body = ctk.CTkFrame(self.root, fg_color="#1a1a1f", corner_radius=0)
        body.pack(fill="both", expand=True)

        # ── Sidebar ──
        sidebar = ctk.CTkFrame(body, fg_color="#22222a", width=260, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # ── Canvas ──
        canvas_frame = ctk.CTkFrame(body, fg_color="#141418", corner_radius=0)
        canvas_frame.pack(side="left", fill="both", expand=True)

        self.hint_lbl = ctk.CTkLabel(
            canvas_frame,
            text="Cliquez sur la page pour positionner l'en-tête",
            fg_color="#111116", text_color="#888888",
            font=("Segoe UI", 9), corner_radius=0
        )
        self.hint_lbl.pack(side="top", pady=8, fill="x")

        self.canvas = tk.Canvas(canvas_frame, bg="#141418",
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>",   self._on_motion)
        self.canvas.bind("<Configure>", lambda e: self._render_preview())

        # ── Bottombar ──
        bottom = ctk.CTkFrame(self.root, fg_color="#111116", height=50, corner_radius=0)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        self.lbl_coords = ctk.CTkLabel(bottom, text="x: — pts  ·  y: — pts",
                                       fg_color="transparent", text_color="#555555",
                                       font=("Courier New", 10))
        self.lbl_coords.pack(side="left", padx=14)

        btn_apply = ctk.CTkButton(bottom, text="✓  Appliquer",
                                  fg_color="#55bb77", text_color="#0a1a0f",
                                  hover_color="#44aa66",
                                  font=("Segoe UI", 11, "bold"),
                                  command=self._apply)
        btn_apply.pack(side="right", padx=10, pady=8)

        btn_skip = ctk.CTkButton(bottom, text="→  Passer",
                                 fg_color="#2a2a35", text_color="#aaaaaa",
                                 hover_color="#3a3a4a",
                                 font=("Segoe UI", 11),
                                 command=self._skip)
        btn_skip.pack(side="right", padx=4, pady=8)

    def _build_sidebar(self, parent):
        cfg = self.cfg

        def section(label):
            ctk.CTkLabel(parent, text=label,
                         fg_color="transparent", text_color="#555566",
                         font=("Segoe UI", 8, "bold"),
                         anchor="w").pack(anchor="w", padx=14, pady=(14, 4))
            ctk.CTkFrame(parent, fg_color="#3a3a4a", height=1,
                         corner_radius=0).pack(fill="x", padx=14)

        # ── Texte de l'en-tête ──
        section("TEXTE DE L'EN-TÊTE")

        self.text_mode = tk.StringVar(value=cfg["text_mode"])

        modes = [
            ("nom",     "Nom du fichier"),
            ("prefixe", "Préfixe  +  nom"),
            ("suffixe", "Nom  +  suffixe"),
            ("custom",  "Texte personnalisé"),
        ]
        for val, label in modes:
            rb = ctk.CTkRadioButton(parent, text=label,
                                    variable=self.text_mode, value=val,
                                    text_color="#dddddd",
                                    font=("Segoe UI", 10),
                                    command=self._on_mode_change)
            rb.pack(anchor="w", padx=14, pady=1)

        # Champs de saisie
        self.var_prefixe = tk.StringVar(value=cfg.get("prefixe", ""))
        self.var_suffixe = tk.StringVar(value=cfg.get("suffixe", ""))
        self.var_custom  = tk.StringVar(value=cfg.get("custom",  ""))

        self.entry_prefixe = self._make_entry(parent, self.var_prefixe, "ex: CONFIDENTIEL –")
        self.entry_suffixe = self._make_entry(parent, self.var_suffixe, "ex: – DRAFT")
        self.entry_custom  = self._make_entry(parent, self.var_custom,  "ex: Société XYZ")

        for v in [self.var_prefixe, self.var_suffixe, self.var_custom]:
            v.trace_add("write", lambda *_: self._on_mode_change())

        # Aperçu
        ctk.CTkLabel(parent, text="Aperçu :",
                     fg_color="transparent", text_color="#666677",
                     font=("Segoe UI", 8),
                     anchor="w").pack(anchor="w", padx=14, pady=(8, 0))
        self.lbl_preview = ctk.CTkLabel(parent, text="",
                                        fg_color="#1a1a22", text_color="#e05555",
                                        font=("Courier New", 8),
                                        wraplength=220, justify="left",
                                        anchor="w", corner_radius=4)
        self.lbl_preview.pack(fill="x", padx=14, pady=(2, 0))

        # ── Style ──
        section("STYLE")

        color_row = ctk.CTkFrame(parent, fg_color="transparent")
        color_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(color_row, text="Couleur",
                     fg_color="transparent", text_color="#aaaaaa",
                     font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
        self.color_swatch = tk.Canvas(color_row, width=26, height=18,
                                      bg=cfg["color_hex"],
                                      highlightthickness=0, cursor="hand2")
        self.color_swatch.pack(side="left", padx=4)
        self.lbl_color_hex = ctk.CTkLabel(color_row, text=cfg["color_hex"],
                                          fg_color="transparent", text_color="#888888",
                                          font=("Courier New", 9))
        self.lbl_color_hex.pack(side="left", padx=4)
        self.color_swatch.bind("<Button-1>", self._pick_color)

        size_row = ctk.CTkFrame(parent, fg_color="transparent")
        size_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(size_row, text="Taille",
                     fg_color="transparent", text_color="#aaaaaa",
                     font=("Segoe UI", 10), width=60, anchor="w").pack(side="left")
        btn_minus = ctk.CTkButton(size_row, text="−", width=30, height=26,
                                  fg_color="#2a2a35", hover_color="#3a3a4a",
                                  text_color="#dddddd",
                                  command=lambda: self._change_size(-1))
        btn_minus.pack(side="left", padx=(0, 2))
        self.var_size = tk.IntVar(value=cfg.get("font_size", 8))
        ctk.CTkEntry(size_row, textvariable=self.var_size,
                     width=46, fg_color="#2a2a35", text_color="#dddddd",
                     border_color="#3a3a4a",
                     font=("Courier New", 10)).pack(side="left")
        btn_plus = ctk.CTkButton(size_row, text="+", width=30, height=26,
                                 fg_color="#2a2a35", hover_color="#3a3a4a",
                                 text_color="#dddddd",
                                 command=lambda: self._change_size(1))
        btn_plus.pack(side="left", padx=(2, 0))
        ctk.CTkLabel(size_row, text="pts",
                     fg_color="transparent", text_color="#666677",
                     font=("Segoe UI", 9)).pack(side="left", padx=4)

        # ── Pages ──
        section("APPLIQUER SUR")

        self.var_all_pages = tk.BooleanVar(value=cfg.get("all_pages", True))
        pages_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pages_frame.pack(fill="x", padx=14, pady=4)

        for text, val in [("Toutes les pages", True), ("Première page", False)]:
            rb = ctk.CTkRadioButton(pages_frame, text=text,
                                    variable=self.var_all_pages, value=val,
                                    text_color="#dddddd",
                                    font=("Segoe UI", 10))
            rb.pack(anchor="w", pady=1)

        # ── Position mémorisée ──
        section("POSITION MÉMORISÉE")
        self.lbl_pos = ctk.CTkLabel(parent, text="—",
                                    fg_color="transparent", text_color="#888888",
                                    font=("Courier New", 9),
                                    justify="left", anchor="w")
        self.lbl_pos.pack(anchor="w", padx=14, pady=4)
        ctk.CTkLabel(parent,
                     text="Cliquez sur la page pour\ndéplacer l'en-tête",
                     fg_color="transparent", text_color="#444455",
                     font=("Segoe UI", 8),
                     justify="left", anchor="w").pack(anchor="w", padx=14)

        self._on_mode_change()
        self._update_pos_label()

    def _make_entry(self, parent, var, placeholder):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=28, pady=1)
        ctk.CTkEntry(frame, textvariable=var,
                     placeholder_text=placeholder,
                     placeholder_text_color="#555566",
                     fg_color="#2a2a35", text_color="#dddddd",
                     border_color="#3a3a4a",
                     font=("Courier New", 9)).pack(fill="x")
        return frame

    # --------------------------------------------------------- Logique texte ---

    def _get_header_text(self, filename=""):
        mode = self.text_mode.get()
        name = filename or (self.pdf_files[self.idx].name if self.pdf_files else "fichier.pdf")
        pfx  = self.var_prefixe.get()
        sfx  = self.var_suffixe.get()
        cst  = self.var_custom.get()

        # Ignorer les placeholders
        for ph in ["ex: CONFIDENTIEL –", "ex: – DRAFT", "ex: Société XYZ"]:
            if pfx == ph: pfx = ""
            if sfx == ph: sfx = ""
            if cst == ph: cst = ""

        if mode == "nom":     return name
        if mode == "prefixe": return f"{pfx} {name}".strip() if pfx else name
        if mode == "suffixe": return f"{name} {sfx}".strip() if sfx else name
        if mode == "custom":  return cst if cst else name
        return name

    def _change_size(self, delta):
        val = max(4, min(72, self.var_size.get() + delta))
        self.var_size.set(val)
        self._on_mode_change()

    def _on_mode_change(self, *_):
        self.lbl_preview.configure(text=self._get_header_text())
        self._draw_overlay()

    # --------------------------------------------------------- Couleur --------

    def _pick_color(self, _=None):
        color = colorchooser.askcolor(
            color=self.cfg["color_hex"],
            title="Choisir la couleur de l'en-tête"
        )
        if color and color[1]:
            self.cfg["color_hex"] = color[1].upper()
            self.color_swatch.config(bg=self.cfg["color_hex"])
            self.lbl_color_hex.configure(text=self.cfg["color_hex"])
            self._draw_overlay()

    # --------------------------------------------------------- PDF courant ----

    def _load_pdf(self):
        if self.idx >= len(self.pdf_files):
            messagebox.showinfo("Terminé", "Tous les fichiers ont été traités !")
            self.root.quit()
            return

        path = self.pdf_files[self.idx]
        self.lbl_filename.configure(text=f"  {path.name}  ")
        self.lbl_progress.configure(
            text=f"  {self.idx + 1} / {len(self.pdf_files)}  "
        )
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(str(path))
        self._on_mode_change()
        self._render_preview()

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

        scale_w = (cw - 40) / self.page_w_pt
        scale_h = (ch - 40) / self.page_h_pt
        self.scale = min(scale_w, scale_h, 2.5)

        mat = fitz.Matrix(self.scale, self.scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        self.page_w_px = pix.width
        self.page_h_px = pix.height

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

        # Croix de guidage
        if hover_cx is not None:
            x0 = self.img_offset_x
            x1 = self.img_offset_x + self.page_w_px
            y0 = self.img_offset_y
            y1 = self.img_offset_y + self.page_h_px
            self.canvas.create_line(x0, hover_cy, x1, hover_cy,
                                    fill="#5577ee44", width=1, dash=(4,4), tags="overlay")
            self.canvas.create_line(hover_cx, y0, hover_cx, y1,
                                    fill="#5577ee44", width=1, dash=(4,4), tags="overlay")

        # Texte positionné
        cx, cy = self._ratio_to_canvas(self.pos_ratio_x, self.pos_ratio_y)
        text   = self._get_header_text()
        size   = max(self.var_size.get(), 4)
        fpx    = max(int(size * self.scale * 1.1), 7)

        self.canvas.create_text(
            cx, cy, text=text,
            anchor="sw",
            fill=self.cfg["color_hex"],
            font=("Courier New", fpx, "bold"),
            tags="overlay"
        )
        # Petite croix de repère
        r = 5
        self.canvas.create_line(cx-r, cy, cx+r, cy, fill=self.cfg["color_hex"],
                                 width=1, tags="overlay")
        self.canvas.create_line(cx, cy-r, cx, cy+r, fill=self.cfg["color_hex"],
                                 width=1, tags="overlay")

    # --------------------------------------------------------- Interactions ---

    def _canvas_to_ratio(self, cx, cy):
        """Canvas pixels → ratio (0-1) sur la page."""
        rx = (cx - self.img_offset_x) / self.page_w_px
        ry = (cy - self.img_offset_y) / self.page_h_px
        rx = max(0.0, min(1.0, rx))
        ry = max(0.0, min(1.0, ry))
        return rx, ry

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
        self._update_pos_label()
        self._draw_overlay()

    def _on_motion(self, event):
        self._draw_overlay(hover_cx=event.x, hover_cy=event.y)
        # Coordonnées en points PDF
        rx, ry = self._canvas_to_ratio(event.x, event.y)
        x_pt, y_pt = self._ratio_to_pdf_pt(rx, ry)
        self.lbl_coords.configure(text=f"x: {x_pt:.0f} pts  ·  y: {y_pt:.0f} pts")

    def _update_pos_label(self):
        x_pt, y_pt = self._ratio_to_pdf_pt(self.pos_ratio_x, self.pos_ratio_y)
        self.lbl_pos.configure(text=f"x : {x_pt:.0f} pts\ny : {y_pt:.0f} pts")

    # --------------------------------------------------------- Actions --------

    def _apply(self):
        path = self.pdf_files[self.idx]
        # Dossier de sortie
        out_dir = path.parent.parent / (path.parent.name + "_avec_entete") \
                  if path.parent.name != path.parent.parent.name \
                  else path.parent / (path.parent.name + "_avec_entete")
        out_dir = path.parent.with_name(path.parent.name + "_avec_entete")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / path.name

        header_text = self._get_header_text()
        color_float = hex_to_rgb_float(self.cfg["color_hex"])
        font_size   = max(self.var_size.get(), 4)
        all_pages   = self.var_all_pages.get()
        x_pt, y_pt  = self._ratio_to_pdf_pt(self.pos_ratio_x, self.pos_ratio_y)

        try:
            doc_out = fitz.open(str(path))
            pages_to_process = range(len(doc_out)) if all_pages else [0]
            for i in pages_to_process:
                pg = doc_out[i]
                pg.insert_text(
                    fitz.Point(x_pt, pg.rect.height - y_pt),
                    header_text,
                    fontname="cour",
                    fontsize=font_size,
                    color=color_float,
                )
            doc_out.save(str(out_path), garbage=4, deflate=True)
            doc_out.close()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return

        # Sauvegarder la config
        self.cfg.update({
            "text_mode"   : self.text_mode.get(),
            "prefixe"     : self.var_prefixe.get(),
            "suffixe"     : self.var_suffixe.get(),
            "custom"      : self.var_custom.get(),
            "color_hex"   : self.cfg["color_hex"],
            "font_size"   : font_size,
            "all_pages"   : all_pages,
            "last_x_ratio": self.pos_ratio_x,
            "last_y_ratio": self.pos_ratio_y,
        })
        save_config(self.cfg)

        print(f"  ✓ {out_path}")
        self.idx += 1
        self._load_pdf()

    def _skip(self):
        print(f"  → Ignoré : {self.pdf_files[self.idx].name}")
        self.idx += 1
        self._load_pdf()

# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def main():
    print(f"PDF Header Tool version: {VERSION} (build {BUILD_ID})")
    check_update()

    # Collecte des PDFs
    if len(sys.argv) > 1:
        pdf_files = []
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.is_dir():
                pdf_files.extend(sorted(p.glob("*.pdf")))
            elif p.suffix.lower() == ".pdf" and p.exists():
                pdf_files.append(p)
    else:
        root_tmp = ctk.CTk()
        root_tmp.withdraw()
        folder = filedialog.askdirectory(title="Sélectionner le dossier contenant les PDFs")
        root_tmp.destroy()
        if not folder:
            sys.exit(0)
        pdf_files = sorted(Path(folder).glob("*.pdf"))

    if not pdf_files:
        root_tmp = ctk.CTk()
        root_tmp.withdraw()
        messagebox.showwarning("Aucun fichier", "Aucun fichier PDF trouvé.")
        root_tmp.destroy()
        sys.exit(0)

    print(f"{len(pdf_files)} fichier(s) PDF trouvé(s).")

    root = ctk.CTk()
    root.geometry("1050x750")
    app = PDFHeaderApp(root, list(pdf_files))
    root.mainloop()

if __name__ == "__main__":
    main()
