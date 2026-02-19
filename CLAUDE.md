# CLAUDE.md — Contexte du projet PDF Header Tool

## Ce que fait ce projet

Outil GUI Python qui permet d'insérer le nom d'un fichier PDF en en-tête de ses pages.
L'utilisateur visualise la première page de chaque PDF, clique pour positionner le texte,
puis valide. Les fichiers originaux ne sont jamais modifiés.

## Architecture

```
pdf-header-tool/
├── pdf_header.py     # Script principal — toute la logique est ici
├── install.py        # Installateur Windows (AppData, venv, raccourcis)
├── install.bat       # Wrapper bat : vérifie Python, lance install.py
├── version.txt       # Numéro de version (ex: 1.0.0) — lu par le système de MAJ
├── CLAUDE.md         # Ce fichier
└── README.md         # Documentation utilisateur
```

## pdf_header.py — Structure interne

### Bootstrap (lignes ~20-60)
- `_get_install_dir()` : retourne `%LOCALAPPDATA%/PDFHeaderTool` sur Windows, dossier du script sur Linux
- `_bootstrap()` : crée le venv dans `install_dir/.venv/`, installe pymupdf + Pillow, se relance dans le venv

### Mise à jour automatique (lignes ~80-110)
- `check_update()` : thread daemon qui compare `version.txt` local vs GitHub raw
- Repo : `MondeDesPossibles/pdf-header-tool`
- Constante `VERSION` en tête du script + `GITHUB_REPO`
- Mise à jour silencieuse : télécharge le nouveau `pdf_header.py` et remplace le fichier courant

### Config persistante
- Fichier : `pdf_header_config.json` dans `INSTALL_DIR`
- Clés : `text_mode`, `prefixe`, `suffixe`, `custom`, `color_hex`, `font_size`, `all_pages`, `last_x_ratio`, `last_y_ratio`
- La position est stockée en **ratio (0.0 à 1.0)** de la page pour être indépendante de la résolution

### Classe PDFHeaderApp (tkinter)
Interface principale. Cycle de vie :
1. `__init__` → `_build_ui()` → `_load_pdf()`
2. Pour chaque PDF : rendu via PyMuPDF → `_render_preview()` → interaction souris → `_apply()` ou `_skip()`
3. `_apply()` : écrit le PDF dans `<dossier_source>_avec_entete/<meme_nom>.pdf`

**Méthodes clés :**
- `_build_ui()` : construit topbar + sidebar + canvas + bottombar
- `_build_sidebar()` : 4 radio boutons texte, color picker, spinbox taille, toggle pages
- `_render_preview()` : convertit page PDF → image PIL → ImageTk, calcule scale + offsets
- `_draw_overlay()` : dessine croix de guidage + aperçu texte rouge sur le canvas tkinter
- `_on_click()` : stocke la position en ratio X/Y
- `_on_motion()` : rafraîchit l'overlay + affiche coordonnées en pts PDF
- `_apply()` : appelle `fitz.Page.insert_text()` avec police "cour" (Courier), sauvegarde config
- `_get_header_text()` : retourne le texte selon le mode radio (nom/préfixe/suffixe/custom)

**Coordonnées :**
- Canvas tkinter : origine haut-gauche, Y croît vers le bas
- PDF (fitz) : origine bas-gauche, Y croît vers le haut
- Conversion : `x_pt = ratio_x * page_w_pt` / `y_pt = (1 - ratio_y) * page_h_pt`

## Dépendances
- `pymupdf` (import `fitz`) — rendu PDF + écriture
- `Pillow` (import `PIL`) — conversion pixmap → ImageTk
- `tkinter` — GUI (inclus dans Python standard)

## Compatibilité
- Windows 11 ✓ (testé Python 3.14.3)
- Linux EndeavourOS ✓ (lancement direct sans install.bat)
- Python 3.8+ requis

## Problèmes connus et corrections déjà apportées
- `_draw_overlay()` appelée avant que `self.canvas` existe → guard `if not hasattr(self, 'canvas'): return`
- Couleurs tkinter : format `#RRGGBB` uniquement, pas de transparence `#RRGGBBAA`

## Conventions de développement
- Pas de framework externe pour la GUI (tkinter pur)
- Tout le code dans un seul fichier `pdf_header.py` (portable, auto-suffisant)
- Incrémenter `VERSION` à chaque modification et créer le tag git correspondant :
  ```bash
  git tag v1.0.1
  git push origin v1.0.1
  ```
- Mettre à jour `version.txt` en même temps que `VERSION` dans le script

## Points d'amélioration identifiés
- Installer Python automatiquement depuis install.bat de façon plus robuste (version dynamique)
- Ajouter une icône .ico pour les raccourcis Windows
- Gérer les PDFs protégés par mot de passe
- Prévisualiser plusieurs pages avant d'appliquer
