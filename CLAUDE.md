# ==============================================================================
# PDF Header Tool — CLAUDE.md
# Version : 0.4.0
# Build   : build-2026.02.20.20
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

# CLAUDE.md — Contexte du projet PDF Header Tool

## Ce que fait ce projet

Outil GUI Python qui permet d'insérer le nom d'un fichier PDF en en-tête de ses pages.
L'utilisateur visualise la première page de chaque PDF, clique pour positionner le texte,
puis valide. Les fichiers originaux ne sont jamais modifiés.

---

## Architecture

```
pdf-header-tool/
├── pdf_header.py     # Script principal — toute la logique est ici
├── install.py        # Installateur Windows (AppData, venv, raccourcis)
├── install.bat       # Wrapper bat : vérifie Python, ouvre python.org si absent/Store, lance install.py
├── version.txt       # Numéro de version (ex: 0.0.1) — lu par le système de MAJ
├── ROADMAP.md        # Évolutions prévues, à lire avant toute modification
├── CLAUDE.md         # Ce fichier
└── README.md         # Documentation utilisateur
```

---

## pdf_header.py — Structure interne

### Bootstrap (lignes ~20-60)
- `_get_install_dir()` : retourne `%LOCALAPPDATA%/PDFHeaderTool` sur Windows, dossier du script sur Linux
- `_bootstrap()` : crée le venv dans `install_dir/.venv/`, installe les dépendances, se relance dans le venv

### Mise à jour automatique (lignes ~80-110)
- `check_update()` : thread daemon qui compare `version.txt` local vs GitHub raw
- Repo : `MondeDesPossibles/pdf-header-tool`
- Constante `VERSION` en tête du script + `GITHUB_REPO`
- Mise à jour silencieuse : télécharge le nouveau `pdf_header.py` et remplace le fichier courant

### Constantes et fonctions module-level (v0.4.0)
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

## install.bat — Structure et comportement

### Fonctionnement général
1. Active UTF-8 (`chcp 65001`) pour éviter les problèmes d'encodage en console Windows
2. Crée immédiatement un fichier log : `<dossier_install>\pdf_header_install.log`
3. Vérifie Python simplement avec `python --version`
4. Si Python absent : ouvre `https://www.python.org/downloads/` et demande une installation manuelle
5. Si Python Microsoft Store détecté : stoppe l'installation et redirige aussi vers `python.org`
6. Lance `install.py` une fois un Python standard détecté
7. Ferme automatiquement en cas de succès (pause uniquement en cas d'erreur)

### Méthode de téléchargement Python
1. Vérification unique via `python --version`
2. Installation manuelle Python via `https://www.python.org/downloads/`
3. Python Microsoft Store non supporté pour l'installation de l'outil

### Fichier log
- Chemin : `<dossier_install>\pdf_header_install.log`
- Affiché à l'écran dès le début et à chaque erreur
- Contient : horodatage, OS, utilisateur, répertoire, toutes les étapes, codes de retour

### Points d'attention pour toute modification de install.bat
- Ne jamais utiliser de caractères Unicode dans les `echo` — risque d'encodage même avec `chcp 65001`
- Toujours logger avant ET après chaque opération critique
- Tester sur une machine sans Python ET sur une machine avec Python ancien
- La variable `PYTHON_CMD` doit être définie avant `:run_installer`
- Cible d'installation: `%LOCALAPPDATA%\\PDFHeaderTool`
- Python Microsoft Store est explicitement refusé par `install.bat` pour éviter la virtualisation des chemins

---

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

- Modifier `pdf_header.py` en priorité — c'est le fichier central
- Ne modifier `install.py` ou `install.bat` que si la tâche le requiert explicitement
- Pour `install.bat` : ne jamais utiliser de caractères Unicode dans les `echo`, toujours logger avant/après chaque étape critique
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
- Toute nouvelle dépendance doit être ajoutée dans `_bootstrap()` ET dans la section Dépendances de ce fichier

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
| Venv corrompu | Détecter (`venv_python` inexistant après création), proposer de le recréer en supprimant `.venv/` |

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

- Tout le code dans un seul fichier `pdf_header.py` (portable, auto-suffisant)
- GUI : CustomTkinter (à partir de v1.1.0) + `tk.Canvas` pour la prévisualisation
- Langue de l'interface : français
- Messages d'erreur : français, clairs, sans jargon technique
- Incrémenter `VERSION` à chaque étape et créer le tag git correspondant
- Pour le cycle en cours, respecter la progression `0.0.1` -> `1.0.0` définie dans `ROADMAP.md`
- Taille UI par défaut : **12 pt** — clé `ui_font_size` dans `DEFAULT_CONFIG`
- Logs debug : toujours conserver `_debug_log()` dans le code — toggle activable via Préférences (Étape 13)
