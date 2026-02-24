# ==============================================================================
# PDF Header Tool — CLAUDE.md
# Version : 0.4.6
# Build   : build-2026.02.23.01
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

# CLAUDE.md — Contexte du projet PDF Header Tool

## Ce que fait ce projet

Outil GUI Python qui permet d'insérer le nom d'un fichier PDF en en-tête de ses pages.
L'utilisateur visualise la première page de chaque PDF, clique pour positionner le texte,
puis valide. Les fichiers originaux ne sont jamais modifiés.

---

## Architecture

### Actuelle (v0.4.6 — fichier unique + distribution portable)

```
pdf-header-tool/          # repo git
├── pdf_header.py         # Script principal — toute la logique est ici
├── lancer.bat            # Point d'entrée Windows portable (double-clic)
├── setup.bat             # Installation dépendances au premier lancement
├── build_dist.py         # Script de build distribution (dev-only)
├── version.txt           # Numéro de version — lu par le système de MAJ
├── ROADMAP.md            # Évolutions prévues, à lire avant toute modification
├── CLAUDE.md             # Ce fichier
└── README.md             # Documentation utilisateur
```

Distribution Windows générée par `build_dist.py` (bundle complet, offline) :

```
PDFHeaderTool/            # dossier de distribution (zippé pour livraison)
├── python/               # Python Embeddable 3.11.x (python3XX._pth patché)
│   ├── python.exe        # interpréteur
│   ├── python311.dll
│   ├── python311.zip     # stdlib Python
│   ├── _tkinter.pyd      # ABSENT de l'embed — copier depuis Python311\DLLs\_tkinter.pyd
│   ├── tcl86t.dll        # copier depuis Python311\tcl86t.dll
│   ├── tk86t.dll         # copier depuis Python311\tk86t.dll
│   ├── tkinter/          # ABSENT de l'embed — copier depuis Python311\Lib\tkinter\
│   └── tcl/              # copier Python311\tcl\ EN ENTIER (contient tcl8.6/ ET tk8.6/)
│                         # _tkinter.pyd cherche TK_LIBRARY dans python/tcl/tk8.6/
├── site-packages/        # dépendances pré-installées (pymupdf, pillow, customtkinter)
│                         # installées via pip cross-compilation par build_dist.py
├── pdf_header.py         # script principal (copie)
├── version.txt
└── lancer.bat            # double-clic pour lancer → app démarre directement
```

### Cible (à partir de v0.4.7 — distribution portable + package)

Distribution portable Windows — aucun Python système requis :

```
PDFHeaderTool/        # dossier de distribution (zippé pour livraison)
├── python/           # Python Embeddable 3.11.x (Windows uniquement)
├── site-packages/    # dépendances pip (pymupdf, pillow, customtkinter)
├── app/              # package Python (à partir de v0.4.7)
│   ├── config.py     # chargement/sauvegarde/migration config
│   ├── models.py     # dataclasses : Config, Position, FontDescriptor
│   ├── constants.py  # COLORS, SIZES, TIMINGS, BUILTIN_FONTS, PRIORITY_FONTS
│   ├── update.py     # check_update(), logique GitHub
│   ├── services/
│   │   ├── pdf_service.py     # fitz : ouverture, insertion, sauvegarde
│   │   ├── layout_service.py  # calculs position, rotation, ratio ↔ pts
│   │   └── font_service.py    # découverte et sélection des polices
│   └── ui/
│       ├── main_window.py     # PDFHeaderApp (classe principale)
│       ├── sidebar.py         # _build_sidebar() et sections
│       └── file_panel.py      # panneau liste des fichiers
├── pdf_header.py     # point d'entrée léger (5-10 lignes)
├── version.txt
├── lancer.bat        # double-clic pour lancer (Windows)
├── setup.bat         # installation dépendances au premier lancement
└── README.md
```

Linux (inchangé) : Python système, lancement direct via `python3 pdf_header.py`.

---

## pdf_header.py — Structure interne

### Bootstrap (lignes ~20-50)
- `_get_install_dir()` : retourne `Path(__file__).parent` (portable, identique Windows et Linux depuis v0.4.6)
- `_bootstrap()` : vérifie que fitz, customtkinter et PIL sont importables — affiche un message d'erreur et quitte si une dépendance est manquante (plus de création de venv depuis v0.4.6)

### Mise à jour automatique (depuis v0.4.6.1, amélioré en v0.4.6.2+)
- `_apply_pending_update()` : s'exécute **avant** `_bootstrap()` au démarrage
  - Applique le patch de `_update_pending/` (déplace les fichiers vers leur destination)
  - Met à jour `_RUNNING_VERSION` en mémoire avec la version appliquée
  - **Redémarre le process immédiatement** après application (Windows: `subprocess.Popen + DETACHED_PROCESS`, Linux: `os.execv`) → la nouvelle version est active dès ce lancement
  - Traces timestampées dans stdout → capturées par `lancer.bat` dans `pdf_header_launch.log`
- `check_update()` : thread daemon (non bloquant) lancé au démarrage
- Constantes : `GITHUB_REPO`, `CHANNEL` (`"release"` | `"beta"`)
- Endpoint selon `CHANNEL` :
  - `"release"` → `/releases/latest` (stable uniquement — jamais affecté par les pre-releases)
  - `"beta"` → `/releases[0]` (toutes releases, pre-releases incluses)
- SSL : `ssl.create_default_context(cafile=certifi.where())` — nécessaire sur Python Embedded (pas de certs Windows)
- Si `_RUNNING_VERSION == remote_version` → rien (évite le double téléchargement)
- Si nouvelle version : télécharge `metadata.json` depuis les assets de la release
- Si `requires_full_reinstall: false` : télécharge `app-patch-vX.Y.Z.zip`, vérifie SHA256,
  extrait dans `_update_pending/` → sera appliqué au **prochain démarrage** (puis restart auto)
- Si `requires_full_reinstall: true` : log uniquement (futur : notification GUI Étape 4.7+)
- Champ `delete` du manifest : fichiers à supprimer lors de l'application
- Tout échec réseau est silencieux — ne jamais bloquer le démarrage de l'app

### Constantes et fonctions module-level (v0.4.5)
- `COLORS` : dict de toutes les couleurs hex de l'UI (arrière-plans, texte, accents, états cartes, overlay)
- `SIZES` : dict de toutes les dimensions, espacements et constantes numériques de l'UI (fenêtre, panneaux, canvas, overlay, limites config)
- `TIMINGS` : dict des délais réseau (`update_version_timeout`, `update_download_timeout`)
- `BUILTIN_FONTS` : dict des polices PDF intégrées (Courier/Helvetica/Times) → codes fitz par style (r/b/i/bi)
- `PRIORITY_FONTS` : dict par plateforme (`win32`/`darwin`/`linux`) des polices système prioritaires connues
- `POSITION_PRESETS` : 9 presets de position `{key: (row, col)}` (tl/tc/tr/ml/mc/mr/bl/bc/br)
- `PRESET_LABELS` : symboles Unicode pour les boutons de la grille 3×3 (↖↑↗←·→↙↓↘)
- `DATE_FORMATS` : 8 formats de date prédéfinis `[(strftime_str, exemple), ...]`
- `DATE_SOURCE_DISPLAY` : `{clé_interne → libellé_UI}` — mappe les valeurs de `date_source` vers leur affichage français ("today" → "Date du jour", "file_mtime" → "Date de création fichier")
- `DATE_SOURCE_INTERNAL` : inverse de `DATE_SOURCE_DISPLAY` (parsing UI → clé interne)
- `_HIDDEN_UI_FEATURES` : set des features présentes dans le code mais masquées dans l'UI en v0.4.x (letter_spacing, line_spacing, position_grid, margins, rotation, frame, background). Consulté dans `_build_sidebar()` et les callbacks d'options pour décider quels widgets construire.
- `_get_font_dirs()` : retourne les dossiers de polices selon la plateforme
- `_find_priority_fonts()` : lookup ciblé (pas de scan exhaustif) → `{display_name: Path}`
- `_get_fitz_font_args(family, font_file, bold, italic)` : retourne `{"fontname": "cour"}` (built-in) ou `{"fontfile": str(path), "fontname": "F0"}` (système)

### Config persistante
- Fichier : `pdf_header_config.json` dans `INSTALL_DIR`
- Clés v0.4.0 : `use_filename`, `use_prefix`, `prefix_text`, `use_suffix`, `suffix_text`, `use_custom`, `custom_text`, `use_date`, `date_position`, `date_source`, `date_format`, `color_hex`, `font_family`, `font_file`, `font_size`, `bold`, `italic`, `underline`, `letter_spacing`, `line_spacing`, `preset_position`, `margin_x_pt`, `margin_y_pt`, `last_x_ratio`, `last_y_ratio`, `rotation`, `use_frame`, `frame_color_hex`, `frame_width`, `frame_style`, `frame_padding`, `frame_opacity`, `use_bg`, `bg_color_hex`, `bg_opacity`, `all_pages`, `ui_font_size`, `log_profile`
- Note : `debug_enabled` (bool, < v0.4.6.11) remplacé par `log_profile` ("simple"|"medium"|"full") lors de l'Étape 4.6.3. Migration automatique dans `load_config()`.
- Migration automatique depuis le format < v0.4.0 : ancienne clé `text_mode` → nouvelles clés `use_filename`/`use_custom` etc. (dans `load_config()`)
- La position est stockée en **ratio (0.0 à 1.0)** de la page pour être indépendante de la résolution

### Classe PDFHeaderApp
Interface principale. Cycle de vie :
1. `__init__` → `_load_system_fonts()` → `_build_ui()` → `_load_pdf()`
2. Pour chaque PDF : rendu via PyMuPDF → `_render_preview()` → interaction souris → `_apply()` ou `_skip()`
3. `_apply()` : écrit le PDF dans `<dossier_source>_avec_entete/<meme_nom>.pdf`

**Méthodes clés :**
- `_load_system_fonts()` : cherche les polices PRIORITY_FONTS sur disque, **doit être appelée avant `_build_ui()`**
- `_build_ui()` : construit topbar + sidebar scrollable (`CTkScrollableFrame` dans outer frame 270px) + canvas + bottombar
- `_section(parent, label)` : crée un header de section ALLCAPS dans la sidebar (converti de closure en méthode)
- `_build_sidebar(parent)` : 9 sections dans le code — TEXTE DE L'EN-TÊTE, DATE, TYPOGRAPHIE, POSITION, ROTATION, CADRE, FOND, APPLIQUER SUR, APERÇU. En v0.4.x, seules ~4 sont visibles : ROTATION, CADRE, FOND et les sous-options espacement/grille/marges sont masquées via `_HIDDEN_UI_FEATURES`.
- `_render_preview()` : convertit page PDF → image PIL → ImageTk, calcule scale + offsets
- `_draw_overlay()` : dessine croix + aperçu texte avec rotation/bg/cadre approximatifs sur le canvas
- `_on_click()` : stocke la position en ratio X/Y, puis `preset_position = "custom"`
- `_on_motion()` : rafraîchit l'overlay + affiche coordonnées en pts PDF
- `_apply()` : utilise `fitz.Page.insert_textbox()` avec `lineheight`, bg rect, frame rect, underline, rotation
- `_get_header_text()` : assemble `[date_prefix] [prefix] [stem|custom] [suffix] [date_suffix]` — utilise `path.stem` (sans extension)
- `_on_preset_click(key)` / `_recalc_ratio_from_preset()` : gestion grille 3×3 + calcul ratio depuis marges
- `_on_margins_change()` : trace sur `var_margin_x/y` → recalcule si preset actif
- `_update_preset_highlight()` : surligne le bouton preset actif en bleu
- `_on_text_change()` : recalcule le texte et rafraîchit l'overlay
- `_update_date_options_visibility()` / `_update_frame_options_visibility()` / `_update_bg_options_visibility()` : masque/affiche les sous-sections avec `pack_forget()` / `pack(after=ref_widget)`
- `_pick_frame_color()` / `_pick_bg_color()` : sélecteur de couleur tkinter
- `_on_font_change(font_name)` : met à jour `cfg["font_file"]` selon la police sélectionnée

**Coordonnées :**
- Canvas tkinter : origine haut-gauche, Y croît vers le bas
- PDF (fitz) : origine bas-gauche, Y croît vers le haut
- Conversion : `x_pt = ratio_x * page_w_pt` / `y_pt = (1 - ratio_y) * page_h_pt`

---

## Dépendances
- `pymupdf` (import `fitz`) — rendu PDF + écriture
- `Pillow` (import `PIL`) — conversion pixmap → ImageTk
- `customtkinter` — GUI moderne (remplace tkinter à partir de v1.1.0)
- `tkinter` — conservé pour `tk.Canvas` (CustomTkinter n'a pas de canvas natif)
- `certifi` — certificats CA pour SSL (Python Embedded n'inclut pas les certs Windows)

---

## Compatibilité
- Windows 11 ✓ (testé Python 3.14.3)
- Linux EndeavourOS ✓ (lancement direct sans install.bat)
- Python 3.8+ requis

---

## Logging et debug (depuis v0.4.6.11 — Étape 4.6.3)

### Profils de verbosité
- `"simple"` (prod) — INFO : démarrage, actions majeures, erreurs. **Défaut en canal `release`**
- `"medium"` (beta/support) — DEBUG : + timings, fonctions clés. **Défaut en canal `beta`**
- `"full"` (dev) — DEBUG + stderr : + traces UI, états, calculs, PDF_INSERT_*
- Clé config : `"log_profile": "simple"|"medium"|"full"` (remplace `"debug_enabled"`)
- Sélecteur dans la fenêtre Préférences prévu à l'Étape 13

### Fichiers de log
- `INSTALL_DIR / "pdf_header_app.log"` — niveau selon profil, rotation 1MB × 5 backups
- `INSTALL_DIR / "pdf_header_errors.log"` — ERROR+ toujours actif, rotation 500KB × 3 backups

### Sous-loggers par domaine
```python
log_app    = logging.getLogger("pdf_header.app")    # lifecycle, session
log_ui     = logging.getLogger("pdf_header.ui")     # interactions utilisateur
log_pdf    = logging.getLogger("pdf_header.pdf")    # opérations PyMuPDF
log_update = logging.getLogger("pdf_header.update") # système de mise à jour
log_config = logging.getLogger("pdf_header.config") # chargement/sauvegarde config
log_font   = logging.getLogger("pdf_header.font")   # découverte des polices
```
Ces loggers sont réutilisables tels quels lors du découpage en `app/` (Étape 4.7).

### `_debug_log()` — wrapper rétrocompatible (NE JAMAIS SUPPRIMER)
```python
def _debug_log(msg: str, level: int = 1) -> None:
    # level: 1=INFO (simple+), 2=DEBUG (medium+), 3=DEBUG [VERB] (full)
    # Sera migré vers les domain loggers lors du refactor 4.7
```
Tous les appels existants (RENDER, CLICK, APPLY) conservent `level=1` par défaut.

### Décorateur `_log_timed(logger, label)`
Ajoute automatiquement START / OK elapsed_ms / FAILED elapsed_ms sur une fonction.
Utilisé sur les fonctions à instrumenter en mode medium/full.

### Événements structurés (profil full — format `key=value` stable)
| Event | Données |
|---|---|
| `PDF_INSERT_PARAMS` | text_len, text_preview, font, size, bold, italic, rotation, click_ratio, preset, margins |
| `PDF_INSERT_RESULT` | page, page_dims, x_pt/y_pt/fitz_y, text_rect, text_w_est, truncated, remaining_chars, applied_ratio |

Ces events définissent les champs de la future dataclass `InsertResult` (Étape 4.9 / pytest).

### Initialisation
```python
# Module-level (early) :
_setup_logger(_default_log_profile())   # avant check_update()

# Dans PDFHeaderApp.__init__, après load_config() :
_setup_logger(self.cfg.get("log_profile", _default_log_profile()))
_log_session_start()   # APP_START session=XXXXXXXX version=... os=... runtime=...
```

### Exception handler global
```python
sys.excepthook = _global_exception_handler
# → log_app.critical("UNCAUGHT_EXCEPTION", exc_info=...) + messagebox.showerror
```

---

## Taille de l'interface (ui_font_size)

- Taille de base par défaut : **12 pt** — clé `"ui_font_size"` dans la config (plage 8–18)
- Correspondance (actuellement hardcodée, sera dynamique à l'Étape 13) :
  - Section headers (ALLCAPS) : `ui_font_size - 2`
  - Labels standards : `ui_font_size`
  - Texte monospace (Courier) : `ui_font_size - 1`
  - Texte secondaire / badges : `ui_font_size - 2`

---

## Distribution et lancement

### Modèle actuel (v0.4.6+) — bundle complet offline

L'utilisateur dézipe et double-clique sur `lancer.bat`. Aucun Python, aucun internet requis.
Toutes les dépendances (pymupdf, Pillow, customtkinter) et Tcl/Tk sont pré-installées dans le zip.

**`lancer.bat` — point d'entrée utilisateur :**
1. Active UTF-8 (`chcp 65001`)
2. Vérifie la présence de `python\python.exe` (sanity check)
3. Lance `python\python.exe pdf_header.py` directement
4. Log dans `pdf_header_launch.log`

**`build_dist.py` — script de build (dev-only) :**
1. Télécharge Python Embeddable 3.11.x depuis python.org (cache `dist/`)
2. Source Tcl/Tk : dossier local `tcltk/` en priorité, NuGet en fallback
3. Extrait Python Embedded → `python/`
4. Copie `_tkinter.pyd`, `tcl86t.dll`, `tk86t.dll`, `tkinter/`, `tcl/` → `python/`
   (correction du crash tkinter : Python Embedded n'inclut pas ces DLLs)
5. Patche `python3XX._pth` : décommente `import site` + ajoute `../site-packages`
6. Installe les dépendances Windows dans `site-packages/` via pip cross-compilation :
   `pip install --platform win_amd64 --python-version 311 --only-binary=:all: --target site-packages/ pymupdf pillow customtkinter`
7. Copie les fichiers du projet (pdf_header.py, lancer.bat, version.txt)
8. Génère dans `dist/` :
   - `PDFHeaderTool-vX.Y.Z-windows.zip` (~40 MB — dossier interne `PDFHeaderTool/`)
   - `app-patch-vX.Y.Z.zip` (~50-300 KB — sources Python uniquement)
   - `metadata.json` (version, flags, hashes)
- Usage : `python3 build_dist.py [--python-version 3.11.9] [--full-reinstall]`
- Connexion internet requise uniquement sur la machine de build (dev)

**Nommage des fichiers de distribution (depuis v0.4.6.6) :**
- Zip complet : `PDFHeaderTool-vX.Y.Z-windows.zip` (sans build ID — nom stable)
- Dossier interne du zip : `PDFHeaderTool/` (stable — cohérent avec les mises à jour auto)
- Patch zip : `app-patch-vX.Y.Z.zip` (avec `v` — correspond exactement au TAG git)
- Le build ID est conservé dans le nom du dossier de travail local (`dist/PDFHeaderTool-vX.Y.Z-build-YYYY.MM.DD.NN/`) mais n'apparaît plus dans le zip livré à l'utilisateur

**Pourquoi Tcl/Tk depuis NuGet :**
Python Embedded inclut `_tkinter.pyd` mais pas les DLLs runtime (`tcl86t.dll`, `tk86t.dll`)
ni les bibliothèques de scripts (`tcl/`, `tk/`). Sans ces fichiers, `import tkinter` échoue
avec exit code 1. Le NuGet Python (.nupkg = ZIP) contient l'installation complète et permet
d'extraire ces fichiers de façon fiable depuis Linux.

**`_get_install_dir()` :**
- Retourne `Path(__file__).parent` dans tous les cas (Windows et Linux — portable USB/réseau)

**`_bootstrap()` :**
- Vérifie que fitz, customtkinter, PIL sont importables — message d'erreur clair si absent
- Sur Windows : dépendances dans `site-packages/` (pré-installées par build_dist.py)
- Sur Linux : dépendances installées manuellement via `pip install pymupdf Pillow customtkinter`

**Points d'attention pour toute modification des .bat :**
- Ne jamais utiliser de caractères Unicode dans les `echo` — risque d'encodage même avec `chcp 65001`
- Toujours logger avant ET après chaque opération critique
- `python\python3XX._pth` doit avoir `import site` décommenté et `../site-packages` présent

**`setup.bat` :**
- Conservé dans le repo comme outil de secours (réinstallation manuelle des deps si nécessaire)
- Ne fait PAS partie de la distribution zip (plus nécessaire depuis le bundle complet)

**`get-pip.py` :**
- NON commité (présent dans `.gitignore`) — à récupérer manuellement si besoin
- Ne fait PAS partie de la distribution zip

### Workflow de release (depuis v0.4.6.1)

**Script `release.sh` (dev uniquement) :**
```bash
./release.sh                          # stable auto-bump (recommandé)
./release.sh X.Y.Z                    # stable version explicite
./release.sh X.Y.Z --full-reinstall  # si site-packages/ ou python/ ont changé
./release.sh --beta                   # beta auto-bump (0.4.7-beta.1 → .2...)
./release.sh X.Y.Z-beta.N --beta     # beta version explicite
```

Comportement `release.sh` :
- Sans argument : lit `version.txt`, auto-bump (stable → stable, beta → beta)
- `--beta` : version `X.Y.Z-beta.N`, `CHANNEL = "beta"`, GitHub Release marquée pre-release
- Sans `--beta` : `CHANNEL = "release"`, GitHub Release stable
- Met à jour `VERSION`, `BUILD_ID` **et `CHANNEL`** dans `pdf_header.py` via `sed`
- Si le tag existe déjà : menu interactif (Écraser / Bump / Annuler)
- Attend jusqu'à 60s que GitHub Actions crée la Release avant d'uploader les assets

Le script automatise dans l'ordre :
1. Mise à jour `VERSION`, `BUILD_ID`, `CHANNEL` dans `pdf_header.py` et `version.txt`
2. Mise à jour `BUILD_ID` dans `build_dist.py`
3. Validation syntaxe Python (`ast.parse`)
4. `git commit + tag vX.Y.Z + push origin main + push origin vX.Y.Z`
5. `python3 build_dist.py` → génère dans `dist/` :
   - `PDFHeaderTool-vX.Y.Z-windows.zip` (~40 MB — installation fraîche)
   - `app-patch-vX.Y.Z.zip` (~50-300 KB — sources Python uniquement)
   - `metadata.json` (version, flags, hashes)
6. Si beta : `gh release edit vX.Y.Z-beta.N --prerelease`
7. `gh release upload vX.Y.Z ...` (si `gh` CLI disponible, sinon instructions manuelles)

**Format `metadata.json` (asset de chaque GitHub Release) :**
```json
{
  "manifest_version": 1,
  "version": "X.Y.Z",
  "requires_full_reinstall": false,
  "patch_zip": {"name": "app-patch-vX.Y.Z.zip", "sha256": "...", "size": 0},
  "delete": []
}
```

**GitHub Actions (`.github/workflows/release.yml`) :**
- Déclenché sur push tag `v*.*.*`
- Crée la GitHub Release avec release notes auto-générées depuis les commits
- Pas de build sur CI (tcltk/ non versionné → build via release.sh en local)

### Modèle legacy (v0.4.x avant 4.6) — install.bat + venv système

Les fichiers `install.bat` et `install.py` ne sont plus dans le repo (supprimés — absents depuis v0.4.6+).
Ils ne sont plus utilisés et ne font pas partie de la distribution.

---

## Problèmes connus et corrections déjà apportées
- **Croix de positionnement centrée** (v0.4.6.11) : `_draw_overlay()` utilise `anchor="center"` sur le canvas ; `_apply()` centre le rect PDF via `fitz.Font.text_length()` et `half_h = font_size * line_spacing / 2`. Overlay et insertion PDF sont cohérents.
- **Libellé `date_source`** (v0.4.6.11) : `DATE_SOURCE_DISPLAY` dict mappe `"file_mtime"` → `"Date de création fichier"` dans l'UI. La clé interne `"file_mtime"` est conservée dans la config.
- `_draw_overlay()` appelée avant que `self.canvas` existe → guard `if not hasattr(self, 'canvas'): return`
- Couleurs tkinter : format `#RRGGBB` uniquement — pas de transparence `#RRGGBBAA`
- VSCode Git : `includeIf` dans `.gitconfig` doit utiliser le chemin absolu, pas `~`
- `install.bat` : encodage console `ÔÇö` → corrigé avec `chcp 65001` + caractères ASCII uniquement
- `install.bat` : logique simplifiée (détection `python --version`, redirection vers python.org si Python absent ou Store)
- `letter_spacing` (v0.4.0) : stocké en config mais **non appliqué au PDF** — `insert_textbox()` n'a pas de paramètre charspacing natif ; sera implémenté via `TextWriter` à l'Étape 11
- `angle=rotation` sur `canvas.create_text()` → protégé dans `try/except tk.TclError` pour compatibilité Tk 8.6+
- Frames masquables (date/cadre/fond) : réinsertion via `pack(after=ref_widget)` et non `pack()` seul pour éviter le déplacement en fin de sidebar
- Champs numériques marge/épaisseur : `tk.StringVar` (pas `DoubleVar`) pour éviter `TclError` quand l'utilisateur vide le champ — valeur parsée avec `try/float()` + fallback
- **[B-001 — open] Police système introuvable** (v0.4.6.11) : si `cfg["font_file"]` est `None` ou le fichier absent du disque, `_get_fitz_font_args()` passe `fontfile=None` à fitz → erreur "need font file or buffer". Fix prévu : valider l'existence du fichier avant `insert_textbox()`, fallback sur Courier avec `log_font.warning`. Voir BUGS.md.
- **[B-002 — open] En-tête mal positionnée sur PDFs avec `/Rotate`** (v0.4.6.11) : PyMuPDF `page.rect` est déjà pivoté par la rotation de la page, mais `insert_textbox()` travaille dans l'espace de coordonnées pré-rotation → décalage et rotation parasite. Fix prévu : lire `page.rotation`, appliquer une compensation matricielle ou recalculer `x_pt`/`y_pt`. Voir BUGS.md.

---

## ══════════════════════════════════════════
## RÈGLES STRICTES POUR CLAUDE CODE
## ══════════════════════════════════════════

### 1. Avant d'écrire du code

- **Lire `ROADMAP.md` en entier** avant toute modification
- **N'implémenter que l'étape demandée**, rien de plus — pas d'anticipation
- **Signaler explicitement** si l'étape demandée dépend d'une étape non encore implémentée
- **Ne jamais modifier** une étape déjà validée sans instruction explicite de l'utilisateur
- **Annoncer** les fichiers qui seront modifiés et les changements prévus avant de coder

### 2. Périmètre des modifications

- **Avant l'Étape 4.7** : modifier `pdf_header.py` — c'est le fichier central.
  À partir de l'Étape 4.7 : modifier le module concerné dans `app/` (voir Architecture cible)
- Ne modifier `install.bat` / `setup.bat` / `lancer.bat` que si la tâche le requiert explicitement
- Pour tout `.bat` : ne jamais utiliser de caractères Unicode dans les `echo`, toujours logger avant/après chaque étape critique
- Toujours mettre à jour `CLAUDE.md` si l'architecture ou les méthodes changent
- Toujours mettre à jour `ROADMAP.md` pour marquer l'étape comme terminée

### 3. Qualité du code

- **Vérifier la syntaxe** après chaque modification :
  ```bash
  python3 -c "import ast; ast.parse(open('pdf_header.py').read()); print('OK')"
  ```
- **Aucun `print()` de debug** dans le code final — utiliser le logger
- **Aucun code commenté** laissé en place — supprimer proprement
- **Aucune fonction inutilisée** — nettoyer après refactoring
- Jusqu'à l'Étape 4.6 : toute nouvelle dépendance doit être dans `_bootstrap()` ET dans la section Dépendances de ce fichier.
  À partir de l'Étape 4.6 : les dépendances sont déclarées dans `setup.bat` (Python Embarqué)

### 4. Compatibilité obligatoire

- Tester mentalement le code sur **Windows ET Linux** avant de proposer
- **Toujours utiliser `pathlib.Path`** pour les chemins — jamais de `\` ou de concaténation de strings
- **Jamais de couleurs RGBA** (`#RRGGBBAA`) dans tkinter/CustomTkinter — format `#RRGGBB` uniquement
- **Jamais appeler une méthode** qui dépend d'un widget avant que ce widget soit créé dans `_build_ui()`
- Vérifier que les widgets mixtes `tkinter` + `customtkinter` sont compatibles

### 5. Versioning et release

- **Format obligatoire du build global** : `build-YYYY.MM.DD.NN` (ex: `build-2026.02.20.04`)
- **À chaque itération**, incrémenter ce build global sur : `pdf_header.py`, `README.md`, `CLAUDE.md`, `ROADMAP.md`
- Conserver ce build visible dans les logs runtime (`pdf_header.py build ...`)
- **Cycle actuel** : repartir de `v0.0.1` et atteindre `v1.0.0` à l'étape 10 de `ROADMAP.md`
- **Ne jamais créer de tag git manuellement** — utiliser `release.sh` qui gère tout :
  ```bash
  ./release.sh X.Y.Z
  ```
- Passer `--full-reinstall` si `site-packages/` ou `python/` ont changé dans cette version

### 6. Ce que Claude Code ne doit JAMAIS faire

- ❌ Réécrire le fichier entier quand une modification partielle suffit
- ❌ Combiner plusieurs étapes de la roadmap en une seule fois
- ❌ Modifier le style visuel sans instruction explicite
- ❌ Supprimer des fonctionnalités existantes pour en ajouter de nouvelles
- ❌ Utiliser `except Exception: pass` — toujours logger et informer
- ❌ Bloquer le thread principal pour une opération longue (réseau, traitement PDF)
- ❌ Hardcoder des chemins système (`C:\`, `/home/user/`, etc.)

---

## GESTION DES ERREURS — RÈGLES OBLIGATOIRES

### Principe général
- Les erreurs **utilisateur** (fichier manquant, format invalide) → message en français dans l'interface
- Les erreurs **techniques** (stacktrace complète) → fichier log uniquement, jamais dans l'interface
- **Ne jamais crasher silencieusement** — toute exception non gérée doit être catchée au niveau global
- Le fichier log est : `INSTALL_DIR / "pdf_header_errors.log"`

### Format du log
```python
import logging
logging.basicConfig(
    filename=str(INSTALL_DIR / "pdf_header_errors.log"),
    level=logging.ERROR,
    format="%(asctime)s — %(levelname)s — %(message)s"
)
```

### Erreurs liées aux fichiers PDF

| Situation | Comportement attendu |
|-----------|---------------------|
| PDF corrompu ou illisible | Message dans l'interface + passer au suivant + marquer la carte "⚠ Erreur" en rouge dans la liste |
| PDF protégé par mot de passe | Détecter avant ouverture, proposer saisie du mot de passe ou ignorer |
| Fichier supprimé entre chargement et traitement | Détecter au moment de l'Appliquer, message clair |
| PDF en lecture seule | Détecter avant d'écrire, informer l'utilisateur |
| PDF avec 0 page | Ignorer avec message |

```python
# Pattern obligatoire pour tout fitz.open()
try:
    doc = fitz.open(str(path))
    if doc.is_encrypted:
        # proposer mot de passe ou ignorer
    if len(doc) == 0:
        raise ValueError("Le PDF ne contient aucune page")
except fitz.FileDataError:
    _log_and_notify("PDF corrompu", path)
except Exception as e:
    logging.error(f"Erreur ouverture {path}: {e}", exc_info=True)
    _log_and_notify(str(e), path)
```

### Erreurs liées à la sauvegarde

| Situation | Comportement attendu |
|-----------|---------------------|
| Dossier destination inaccessible | Message + proposer de choisir un autre emplacement |
| Disque plein | Message explicite |
| Fichier destination déjà ouvert (Windows) | Détecter le `PermissionError`, message "Fermez le fichier et réessayez" |
| Conflit de nom (fichier de sortie existe déjà) | Proposer : Écraser / Renommer automatiquement / Ignorer |

```python
# Pattern obligatoire pour toute écriture de fichier
try:
    doc.save(str(out_path), garbage=4, deflate=True)
except PermissionError:
    _notify_user("Le fichier est ouvert dans un autre programme. Fermez-le et réessayez.")
except OSError as e:
    logging.error(f"Erreur sauvegarde {out_path}: {e}", exc_info=True)
    _notify_user(f"Impossible de sauvegarder : {e.strerror}")
```

### Erreurs liées à la mise à jour (réseau)

- Pas de connexion → **ignorer silencieusement**, ne jamais bloquer le lancement
- GitHub indisponible → idem
- Fichier téléchargé corrompu → vérifier la syntaxe Python avant de remplacer l'ancien fichier
- Timeout → 5 secondes maximum, puis abandon silencieux

```python
# Pattern obligatoire pour la mise à jour
try:
    # ... téléchargement ...
    # Vérifier avant de remplacer
    ast.parse(new_content.decode())  # valider que c'est du Python valide
    tmp.replace(script_path)
except SyntaxError:
    logging.error("Fichier de mise à jour invalide, abandon")
    tmp.unlink(missing_ok=True)
except Exception:
    pass  # Réseau indisponible — silencieux
```

### Erreurs liées à l'environnement

| Situation | Comportement attendu |
|-----------|---------------------|
| Python < 3.8 | Message explicite avec lien `python.org/downloads` |
| Dépendance impossible à installer | Message avec instructions manuelles : `pip install pymupdf Pillow customtkinter` |
| Venv corrompu | (v0.4.x) Détecter (`venv_python` inexistant après création), proposer de le recréer en supprimant `.venv/`. À partir de l'Étape 4.6 : plus de venv — Python Embarqué |

### Gestionnaire global d'exceptions non catchées

```python
import traceback

def _global_exception_handler(exc_type, exc_value, exc_tb):
    logging.error(
        "Exception non gérée",
        exc_info=(exc_type, exc_value, exc_tb)
    )
    # Afficher un message sobre à l'utilisateur
    try:
        messagebox.showerror(
            "Erreur inattendue",
            f"Une erreur inattendue s'est produite.\n"
            f"Détails enregistrés dans :\n{INSTALL_DIR / 'pdf_header_errors.log'}"
        )
    except Exception:
        pass

sys.excepthook = _global_exception_handler
```

---

## Conventions de développement

- Jusqu'à l'Étape 4.7 : tout le code dans un seul fichier `pdf_header.py`.
  À partir de l'Étape 4.7 : code découpé en package `app/` (voir Architecture cible)
- GUI : CustomTkinter (à partir de v1.1.0) + `tk.Canvas` pour la prévisualisation
- Langue de l'interface : français
- Messages d'erreur : français, clairs, sans jargon technique
- Incrémenter `VERSION` à chaque étape et créer le tag git correspondant
- Pour le cycle en cours, respecter la progression `0.0.1` -> `1.0.0` définie dans `ROADMAP.md`
- Taille UI par défaut : **12 pt** — clé `ui_font_size` dans `DEFAULT_CONFIG`
- Logs debug : toujours conserver `_debug_log()` dans le code — toggle activable via Préférences (Étape 13)

---

## [CODEX] Addendum — Architecture effective sous-etape 4.7.6

[CODEX ORIGINAL]
- `PDFHeaderApp` etait documentee comme classe centrale du monolithe `pdf_header.py`.
- L'architecture cible 4.7 mentionnait `app/ui/main_window.py`, `app/ui/sidebar.py`, `app/ui/file_panel.py`.

[CODEX MODIFICATION]
- La separation UI est maintenant effective :
  - `app/ui/file_panel.py` : panneau fichiers (cartes + compteur)
  - `app/ui/sidebar.py` : construction sidebar + callbacks/options
  - `app/ui/main_window.py` : `PDFHeaderApp` (lifecycle, rendu, apply/skip)
- Nouveau module runtime ajoute pour decoupler le point d'entree :
  - `app/runtime.py` : bootstrap dependances, setup logger, profil par canal, exception handler global
- `pdf_header.py` est allege et limite a :
  - constantes version/build/channel
  - application update pending
  - bootstrap dependances
  - lancement `PDFHeaderApp`

[CODEX JUSTIFICATION]
- Ce decoupage permet d'aligner l'etat reel du code avec la cible 4.7 sans casser l'ordre critique update/bootstrap.
- Le module runtime evite les imports circulaires entre entrypoint et UI tout en conservant les loggers de domaine.

[CODEX]
- Note documentaire : la reference `COMMAND.md` du prompt de reprise ne correspond pas au repo actuel.
  Le fichier present est `COMMANDS.md`.

---

## [CODEX] Addendum — Release flow stable/beta (scripts)

[CODEX ORIGINAL]
- `release.sh` poussait historiquement `main` + tag.
- `build_dist.py` copiait des fichiers projet via une liste simple.

[CODEX MODIFICATION]
- `release.sh` supporte maintenant:
  - `--branch <name>` (defaut: branche courante)
  - `--dry-run` (validation sans mutation)
  - `--list-package` (affichage whitelist packaging)
  - validations explicites de coherence version/build + etat de branche.
- `build_dist.py` expose une whitelist runtime explicite (`RUNTIME_FILES`, `RUNTIME_GLOBS`) et
  un mode `--list-files` pour inspection sans build.

[CODEX JUSTIFICATION]
- Rend la publication stable/beta reproductible et auditable.
- Reduit le risque de pousser la mauvaise branche ou de publier un package incoherent.

---

## [CODEX] Addendum — Limitations temporaires polices (post `v0.4.7-beta.2`)

[CODEX MODIFICATION]
- Le selecteur de police UI expose temporairement uniquement les polices built-in PyMuPDF:
  `Courier`, `Helvetica`, `Times`.
- Les polices systeme detectees (ex: Arial/Calibri/DejaVu) sont masquees pour eviter les faux positifs
  de style (apercu OK mais rendu PDF KO).
- Le tri des fichiers PDF est desormais naturel (`fichier_2` avant `fichier_10`) dans UI + CLI.

[LIMITE CONNUE]
- Support complet des polices systeme avec variantes TTF (`regular`, `bold`, `italic`, `bold-italic`)
  reporte a une iteration ulterieure.
