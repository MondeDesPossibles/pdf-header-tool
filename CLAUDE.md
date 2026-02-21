# ==============================================================================
# PDF Header Tool — CLAUDE.md
# Version : 0.4.6
# Build   : build-2026.02.21.03
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
├── install.py            # Installateur Windows legacy (non utilisé en v0.4.6+)
├── install.bat           # Wrapper bat legacy (non utilisé en v0.4.6+)
├── lancer.bat            # Point d'entrée Windows portable (double-clic)
├── setup.bat             # Installation dépendances au premier lancement
├── build_dist.py         # Script de build distribution (dev-only)
├── get-pip.py            # Bundlé localement — NON commité (voir .gitignore)
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
│   ├── _tkinter.pyd      # bridge C Tcl/Tk (présent dans embed)
│   ├── tcl86t.dll        # ← extrait du NuGet (fix crash tkinter)
│   ├── tk86t.dll         # ← extrait du NuGet
│   ├── tcl/              # ← extrait du NuGet
│   └── tk/               # ← extrait du NuGet
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

### Mise à jour automatique (lignes ~80-110)
- `check_update()` : thread daemon qui compare `version.txt` local vs GitHub raw
- Repo : `MondeDesPossibles/pdf-header-tool`
- Constante `VERSION` en tête du script + `GITHUB_REPO`
- Mise à jour silencieuse : télécharge le nouveau `pdf_header.py` et remplace le fichier courant

### Constantes et fonctions module-level (v0.4.5)
- `COLORS` : dict de toutes les couleurs hex de l'UI (arrière-plans, texte, accents, états cartes, overlay)
- `SIZES` : dict de toutes les dimensions, espacements et constantes numériques de l'UI (fenêtre, panneaux, canvas, overlay, limites config)
- `TIMINGS` : dict des délais réseau (`update_version_timeout`, `update_download_timeout`)
- `BUILTIN_FONTS` : dict des polices PDF intégrées (Courier/Helvetica/Times) → codes fitz par style (r/b/i/bi)
- `PRIORITY_FONTS` : dict par plateforme (`win32`/`darwin`/`linux`) des polices système prioritaires connues
- `POSITION_PRESETS` : 9 presets de position `{key: (row, col)}` (tl/tc/tr/ml/mc/mr/bl/bc/br)
- `DATE_FORMATS` : 8 formats de date prédéfinis `[(strftime_str, exemple), ...]`
- `_get_font_dirs()` : retourne les dossiers de polices selon la plateforme
- `_find_priority_fonts()` : lookup ciblé (pas de scan exhaustif) → `{display_name: Path}`
- `_get_fitz_font_args(family, font_file, bold, italic)` : retourne `{"fontname": "cour"}` (built-in) ou `{"fontfile": str(path), "fontname": "F0"}` (système)

### Config persistante
- Fichier : `pdf_header_config.json` dans `INSTALL_DIR`
- Clés v0.4.0 : `use_filename`, `use_prefix`, `prefix_text`, `use_suffix`, `suffix_text`, `use_custom`, `custom_text`, `use_date`, `date_position`, `date_source`, `date_format`, `color_hex`, `font_family`, `font_file`, `font_size`, `bold`, `italic`, `underline`, `letter_spacing`, `line_spacing`, `preset_position`, `margin_x_pt`, `margin_y_pt`, `last_x_ratio`, `last_y_ratio`, `rotation`, `use_frame`, `frame_color_hex`, `frame_width`, `frame_style`, `frame_padding`, `frame_opacity`, `use_bg`, `bg_color_hex`, `bg_opacity`, `all_pages`, `ui_font_size`, `debug_enabled`
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
- `_build_sidebar(parent)` : 9 sections — TEXTE DE L'EN-TÊTE, DATE, TYPOGRAPHIE, POSITION (grille 3×3), ROTATION, CADRE, FOND, APPLIQUER SUR, APERÇU
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

---

## Compatibilité
- Windows 11 ✓ (testé Python 3.14.3)
- Linux EndeavourOS ✓ (lancement direct sans install.bat)
- Python 3.8+ requis

---

## Logging et debug

### Principe
- La fonction `_debug_log()` est **toujours présente** dans le code — ne jamais la supprimer
- L'enregistrement est contrôlé par `_DEBUG_ENABLED` (global bool) + clé `"debug_enabled"` dans la config
- Par défaut : **désactivé** — activation prévue dans la fenêtre Préférences (Étape 13)

### Événements à logger (quand activé)
| Événement | Données |
|-----------|---------|
| OPEN_FILES / OPEN_FOLDER | liste des fichiers chargés |
| RENDER | canvas_wh, scale, page_pt, page_px, tk_scaling |
| CLICK | filename, canvas coords, offset, page_px, ratio, canvas_wh |
| APPLY | filename, ratio, page_pt, x_pt, y_pt — puis par page : rect + fitz.Point |
| SKIP | filename, index |

### Fichier log
- Chemin : `INSTALL_DIR / "pdf_header_debug.log"`
- Mode append (pas d'écrasement entre sessions)
- Format : `[YYYY-MM-DD HH:MM:SS] EVENT données`

### Pattern dans le code
```python
_DEBUG_ENABLED = False   # module-level
_DEBUG_LOG     = INSTALL_DIR / "pdf_header_debug.log"

def _debug_log(msg: str):
    if not _DEBUG_ENABLED:
        return
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# Dans PDFHeaderApp.__init__, après load_config() :
global _DEBUG_ENABLED
_DEBUG_ENABLED = self.cfg.get("debug_enabled", False)
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
2. Télécharge Python NuGet package pour extraire les DLLs Tcl/Tk (cache `dist/`)
3. Extrait Python Embedded → `python/`
4. Copie `tcl86t.dll`, `tk86t.dll`, `tcl/`, `tk/` depuis le NuGet → `python/`
   (correction du crash tkinter : Python Embedded n'inclut pas ces DLLs)
5. Patche `python3XX._pth` : décommente `import site` + ajoute `../site-packages`
6. Installe les dépendances Windows dans `site-packages/` via pip cross-compilation :
   `pip install --platform win_amd64 --python-version 311 --only-binary=:all: --target site-packages/ pymupdf pillow customtkinter`
7. Copie les fichiers du projet (pdf_header.py, lancer.bat, version.txt)
8. Crée `dist/PDFHeaderTool-vX.Y.Z.zip` (~35-45 Mo)
- Usage : `python3 build_dist.py [--python-version 3.11.9]`
- Connexion internet requise uniquement sur la machine de build (dev)

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

**`setup.bat` et `get-pip.py` :**
- Conservés dans le repo comme outil de secours (réinstallation manuelle des deps si nécessaire)
- Ne font PAS partie de la distribution zip (plus nécessaires depuis le bundle complet)

### Modèle legacy (v0.4.x avant 4.6) — install.bat + venv système

Les fichiers `install.bat` et `install.py` sont conservés dans le repo pour référence
mais ne sont plus utilisés à partir de v0.4.6.

---

## Corrections à apporter (avant livraison)
- **Croix de positionnement** : indique actuellement le coin supérieur-gauche de la zone de texte.
  Objectif : la croix doit marquer le **centre géométrique** de la zone d'insertion.
  Implémentation : estimer `text_w` via `fitz.Font.text_length()` et `text_h` via `nb_lignes × font_size × line_spacing`,
  puis centrer le rect autour du point cliqué : `[x_pt - text_w/2, y_pt - text_h/2, x_pt + text_w/2, y_pt + text_h/2]`.
  Mettre à jour `_draw_overlay()` en conséquence pour que l'aperçu soit lui aussi centré sur la croix.
- **Libellé `date_source`** : la valeur `"file_mtime"` (interne) ne doit jamais être affichée dans l'UI.
  Remplacer le libellé affiché par "Date de création fichier" tout en conservant la clé interne `"file_mtime"`.

## Problèmes connus et corrections déjà apportées
- `_draw_overlay()` appelée avant que `self.canvas` existe → guard `if not hasattr(self, 'canvas'): return`
- Couleurs tkinter : format `#RRGGBB` uniquement — pas de transparence `#RRGGBBAA`
- VSCode Git : `includeIf` dans `.gitconfig` doit utiliser le chemin absolu, pas `~`
- `install.bat` : encodage console `ÔÇö` → corrigé avec `chcp 65001` + caractères ASCII uniquement
- `install.bat` : logique simplifiée (détection `python --version`, redirection vers python.org si Python absent ou Store)
- `letter_spacing` (v0.4.0) : stocké en config mais **non appliqué au PDF** — `insert_textbox()` n'a pas de paramètre charspacing natif ; sera implémenté via `TextWriter` à l'Étape 11
- `angle=rotation` sur `canvas.create_text()` → protégé dans `try/except tk.TclError` pour compatibilité Tk 8.6+
- Frames masquables (date/cadre/fond) : réinsertion via `pack(after=ref_widget)` et non `pack()` seul pour éviter le déplacement en fin de sidebar
- Champs numériques marge/épaisseur : `tk.StringVar` (pas `DoubleVar`) pour éviter `TclError` quand l'utilisateur vide le champ — valeur parsée avec `try/float()` + fallback

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

### 5. Versioning

- **Incrémenter `VERSION`** dans `pdf_header.py` à chaque étape complétée
- **Mettre à jour `version.txt`** en même temps
- **Format obligatoire du build global** : `build-YYYY.MM.DD.NN` (ex: `build-2026.02.20.04`)
- **À chaque itération**, incrémenter ce build global sur **tous** les fichiers de référence :
  `pdf_header.py`, `install.py`, `install.bat`, `README.md`, `CLAUDE.md`, `ROADMAP.md`
- Conserver ce build visible dans les logs runtime (`Build install.bat: ...`, `install.py version: ...`, `pdf_header.py build ...`)
- **Cycle actuel** : repartir de `v0.0.1` et atteindre `v1.0.0` à l'étape 10 de `ROADMAP.md`
- Rappeler à l'utilisateur de créer le tag git correspondant :
  ```bash
  git tag vX.Y.Z && git push origin vX.Y.Z
  ```

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
