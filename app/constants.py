# ==============================================================================
# app/constants.py — Constantes UI, polices et configuration
# Déplacé depuis pdf_header.py lors de l'Étape 4.7 (substep-1)
# Aucune dépendance externe — stdlib seulement (aucun import requis)
# ==============================================================================

# ---------------------------------------------------------------------------
# Constantes UI — couleurs
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

# ---------------------------------------------------------------------------
# Constantes UI — dimensions et espacements
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Constantes réseau — timeouts
# ---------------------------------------------------------------------------
TIMINGS = {
    "update_version_timeout":  5,    # vérification version (s)
    "update_download_timeout": 15,   # téléchargement mise à jour (s)
}

# ---------------------------------------------------------------------------
# Polices PDF intégrées (built-in fitz) et polices système prioritaires
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

# ---------------------------------------------------------------------------
# Préréglages de position (grille 3×3) et symboles UI
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Formats de date et libellés UI
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Fonctionnalités masquées dans l'UI pour la v0.4.x (logique conservée)
# ---------------------------------------------------------------------------
_HIDDEN_UI_FEATURES = {
    "letter_spacing",
    "line_spacing",
    "position_grid",
    "margins",
    "rotation",
    "frame",
    "background",
}
