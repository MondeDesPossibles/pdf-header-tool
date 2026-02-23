# ==============================================================================
# PDF Header Tool — ROADMAP.md
# Version : 0.4.6
# Build   : build-2026.02.22.03
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

# ROADMAP — PDF Header Tool

Ce fichier liste les évolutions prévues dans l'ordre d'implémentation.
Chaque étape doit être validée avant de passer à la suivante.

---

## Cadre de versionnement (reset)

- Point de départ de reprise : `v0.0.1`
- Objectif de cette roadmap : livrer une release fonctionnelle `v1.0.0`
- Principe : appliquer les étapes dans l'ordre, avec incrément de version à chaque étape
- Jalons :
  - Étape 1 -> `v0.1.0`
  - Étape 2 -> `v0.2.0`
  - Étape 3 -> `v0.3.0`
  - Étape 4 -> `v0.4.0`
  - Étape 4.5 -> `v0.4.5`
  - Étape 4.6 -> `v0.4.6`
  - Étape 4.7 -> `v0.4.7`
  - Étape 4.8 -> `v0.4.8`
  - Étape 4.9 -> `v0.4.9`
  - Étape 5 -> `v0.5.0`
  - Étape 6 -> `v0.6.0`
  - Étape 7 -> `v0.7.0`
  - Étape 8 -> `v0.8.0`
  - Étape 9 -> `v0.9.0`
  - Étape 10 -> `v1.0.0` (release cible)
  - Étapes 11+ -> post-`1.0.0`

---

## Base de départ (hors étapes)

### install.bat — v0.0.1 (baseline)
**Statut : Terminé ✓** — point de départ avant reprise des étapes roadmap

- Encodage console : ajout `chcp 65001`, suppression des caractères Unicode dans les `echo`
- Vérification Python via `python --version`
- Si Python absent : ouvrir `https://www.python.org/downloads/` et demander une installation manuelle
- Si Python Microsoft Store détecté : refuser ce runtime et rediriger vers `python.org`
- Si Python standard détecté : lancer `install.py`
- Cible d'installation : `%LOCALAPPDATA%\\PDFHeaderTool`
- Fermeture automatique de `install.bat` en cas de succès (pause uniquement en erreur)
- Log complet dans `pdf_header_install.log` (dossier de `install.bat`)

---

## Étape 1 — Migration CustomTkinter
**Statut : Terminé ✓**
**Version livrée : 0.1.0**

Remplacer tkinter par CustomTkinter pour un rendu moderne.

- Remplacer `import tkinter as tk` par `import customtkinter as ctk` ✓
- Remplacer `tk.Tk()` par `ctk.CTk()` ✓
- Remplacer tous les widgets tk par leurs équivalents ctk
  (`ctk.CTkFrame`, `ctk.CTkLabel`, `ctk.CTkButton`, `ctk.CTkRadioButton`, etc.) ✓
- Remplacer `tk.Spinbox` → `ctk.CTkEntry` avec validation numérique ✓
- Garder `tk.Canvas` pour la prévisualisation PDF ✓
- Définir un thème global : `ctk.set_appearance_mode("dark")`
  et `ctk.set_default_color_theme("blue")` ✓
- Ajouter `customtkinter` à la liste des dépendances dans `_bootstrap()` ✓

---

## Étape 2 — Écran d'accueil avec choix fichier / dossier
**Statut : Terminé ✓**
**Version livrée : 0.2.0**

Remplacer la boîte de dialogue automatique au lancement par un écran d'accueil
intégré dans la fenêtre principale.

### Comportement actuel
Au lancement, une boîte de dialogue système s'ouvre immédiatement pour choisir
un dossier. Si l'utilisateur annule, l'app quitte.

### Nouveau comportement
L'app s'ouvre et affiche dans la zone de prévisualisation deux grands boutons :
- **📄 Ouvrir des fichiers** → boîte de dialogue, sélection multiple de PDFs possible
- **📁 Ouvrir un dossier** → boîte de dialogue, traite tous les PDFs du dossier

Une fois la sélection faite, l'écran d'accueil disparaît et le premier PDF
s'affiche. Si l'utilisateur annule, l'écran d'accueil reste affiché (l'app
ne quitte plus).

### Détails d'implémentation
- Créer `_show_welcome_screen()` et `_hide_welcome_screen()`
- Modifier `main()` pour ne plus appeler `filedialog` avant l'ouverture
- La sidebar reste visible mais désactivée tant qu'aucun PDF n'est chargé

---

## Étape 3 — Panneau liste des fichiers
**Statut : Terminé ✓**
**Version livrée : 0.3.0**

Ajouter un panneau à droite de la prévisualisation listant tous les PDFs chargés.

### Comportement
- Chaque fichier est affiché sous forme de carte avec son nom (sans extension)
  et son nombre de pages
- L'utilisateur peut cliquer sur n'importe quelle carte pour traiter ce fichier
  directement, dans n'importe quel ordre
- Après "Appliquer", le fichier suivant non traité dans la liste est
  automatiquement sélectionné
- Après "Passer", idem

### États visuels des cartes
- **Non traité** : couleur neutre, texte normal
- **En cours** : surligné / bordure colorée
- **Traité** : fond vert foncé + badge "✓ Modifié"
- **Passé (ignoré)** : fond gris + badge "→ Ignoré"
- **Erreur** : fond rouge foncé + badge "⚠ Erreur"

### Détails d'implémentation
- Nouveau panneau `ctk.CTkScrollableFrame` à droite du canvas
- Largeur fixe ~220px
- Compteur en bas du panneau : "X / Y fichiers traités"

---

## Étape 4 — Refonte du texte de l'en-tête
**Statut : Terminé ✓**
**Version livrée : 0.4.0**

Refonte complète de la section "Texte de l'en-tête" dans la sidebar.

### Composition du texte
- **Supprimer l'extension `.pdf`** du texte injecté par défaut
  (ex : `rapport_2024` au lieu de `rapport_2024.pdf`)
- **Préfixe**, **nom de fichier** (lecture seule), **suffixe**, **texte personnalisé**
  avec activation indépendante
- Préfixe et suffixe activables simultanément
- Insertion de **date** via date picker
- Option date du jour par défaut
- Date utilisable en préfixe ou suffixe
- Personnalisation du format de date
- Source de date configurable (date du jour ou date de création fichier)
- Aperçu temps réel conservé

### Typographie
- Sélecteur de police basé sur les polices disponibles sur le système utilisateur
- Priorité d'affichage: polices Microsoft par défaut, Linux par défaut, Apple par défaut
- Ajouter les polices Google présentes sur le système (ex: Roboto, Lato)
- Style **gras**
- Style *italique*
- Style souligné
- Réglage de l'espacement des lettres
- Réglage de l'espacement des lignes

### Position et orientation
- Liste de positions prédéfinies:
  - haut-gauche, haut-centre, haut-droite
  - milieu-gauche, milieu-centre, milieu-droite
  - bas-gauche, bas-centre, bas-droite
- Ajustement fin via marges et offsets X/Y
- Orientation horizontale ou verticale
- Rotation par angle prédéfini (0, 90, 180, 270)
- Direction du texte en mode vertical configurable

### Cadre et fond
- Option cadre activable
- Choix de la couleur du cadre
- Épaisseur du trait configurable
- Style de bord configurable
- Padding interne autour du texte
- Option fond activable (plein ou non)
- Choix de la couleur du fond
- Opacité du fond configurable
- Opacité du contour configurable

### Gestion des limites
- Retour automatique à la ligne en respectant les mots (pas de coupure au milieu d'un mot)

---

## Étape 4.5 — Centralisation des constantes et valeurs en dur
**Statut : Terminé ✓**
**Version livrée : 0.4.5**

Objectif : améliorer la lisibilité et la maintenabilité de `pdf_header.py` sans changer
le comportement ni la structure des fichiers. Zéro risque de régression.

### Constantes UI
- Déplacer toutes les couleurs hex dans un bloc `COLORS = {}` en tête de script
- Déplacer toutes les tailles et espacements fixes dans un bloc `SIZES = {}`
  (`SIDEBAR_WIDTH`, `FILE_PANEL_WIDTH`, `TOPBAR_HEIGHT`, etc.)
- Déplacer les durées et délais dans `TIMINGS = {}` (débounce overlay, timeout réseau, etc.)

### Suppression des magic numbers
- Remplacer toutes les constantes numériques non nommées (coordonnées, offsets, tailles fixes)
  par des références aux blocs ci-dessus
- Supprimer les chaînes de couleur dupliquées

### Périmètre strict
- Aucun découpage de fichier — tout reste dans `pdf_header.py`
- Aucun changement de comportement ou d'interface visible

---

## Étape 4.6 — Distribution Windows portable, bundle complet (zero-install, offline)
**Statut : Terminé ✓**
**Version livrée : 0.4.6**

Distribution Windows entièrement auto-contenue : Python Embarqué + Tcl/Tk + toutes les
dépendances pré-installées. L'utilisateur dézipe et double-clique. Aucun internet requis.

### Structure de distribution réelle (bundle complet pré-installé)
```
PDFHeaderTool-vX.Y.Z-build-YYYY.MM.DD.NN/
├── python/                    # Python Embeddable 3.11.x
│   ├── python.exe
│   ├── python311.dll
│   ├── python311.zip          # stdlib Python (sans tkinter ni _tkinter)
│   ├── python311._pth         # patché : "import site" + "../site-packages"
│   ├── _tkinter.pyd           # pont C Tcl/Tk (absent de l'embed — ajouté par build_dist.py)
│   ├── tcl86t.dll             # runtime Tcl
│   ├── tk86t.dll              # runtime Tk
│   ├── tkinter/               # module Python tkinter (absent de python311.zip — ajouté)
│   └── tcl/                   # scripts Tcl + Tk (tcl8.6/ ET tk8.6/ côte à côte)
├── site-packages/             # dépendances pré-installées (pymupdf, pillow, customtkinter)
├── pdf_header.py              # script principal
├── version.txt
└── lancer.bat                 # double-clic → lance directement (aucune install requise)
```

### lancer.bat — comportement réel
1. Active UTF-8 (`chcp 65001`)
2. Vérifie la présence de `python\python.exe` (sanity check)
3. Lance `python\python.exe pdf_header.py` → stdout+stderr redirigés dans `pdf_header_launch.log`
4. Log du code retour dans `pdf_header_launch.log`

### build_dist.py — script de build (dev only, Linux)
1. Télécharge Python Embeddable 3.11.x depuis python.org (cache `dist/`)
2. Source Tcl/Tk : dossier local `tcltk/` en priorité, NuGet en fallback
3. Extrait Python Embedded → `python/`
4. Copie `_tkinter.pyd`, `tcl86t.dll`, `tk86t.dll`, `tkinter/`, `tcl/` → `python/`
5. Patche `python311._pth`
6. Installe les dépendances Windows via pip cross-compilation → `site-packages/`
7. Copie les fichiers du projet
8. Crée `dist/PDFHeaderTool-vX.Y.Z-build-YYYY.MM.DD.NN.zip`

**Point critique Tcl/Tk :** `_tkinter.pyd` et `tkinter/` sont absents du Python Embedded officiel.
Ils doivent être copiés depuis une installation Windows standard dans `tcltk/` (non versionné).
`tcltk/tcl/` doit être copié en entier : `_tkinter.pyd` cherche `TK_LIBRARY` dans `python/tcl/tk8.6/`.

### pdf_header.py — changements
- `_get_install_dir()` : retourne `Path(__file__).parent` dans tous les cas (portable USB/réseau)
- `_bootstrap()` : vérifie uniquement que fitz, customtkinter, PIL sont importables

### Linux (inchangé)
- Python système utilisé directement, lancement via `python3 pdf_header.py`
- Dépendances installées manuellement : `pip install pymupdf pillow customtkinter`

---

## Étape 4.6.1 — Infrastructure de release et mise à jour automatique v2
**Statut : Terminé ✓**
**Version cible : v0.4.6.1**
**Prérequis : Étape 4.6 terminée**

Mettre en place un workflow de release reproductible et un mécanisme de mise à jour
robuste, compatible avec l'architecture multi-fichiers de l'étape 4.7.

### Problème résolu

L'ancien `check_update()` lisait depuis la branche `main` et ne téléchargeait que
`pdf_header.py`. Ces deux comportements sont incorrects et incompatibles avec 4.7 :
- Lire depuis `main` signifie qu'un commit en cours de travail peut déclencher une MAJ
- Un seul fichier ne fonctionnera plus quand l'app sera découpée en `app/*.py`

### Stratégie choisie : manifest JSON + patch zip

Chaque release GitHub publie 3 assets :
```
PDFHeaderTool-vX.Y.Z-windows.zip     (~40 MB — installation fraîche)
app-patch-vX.Y.Z.zip                 (~50-300 KB — sources Python uniquement)
metadata.json                        (version, flags, hashes)
```

### Format metadata.json

```json
{
  "manifest_version": 1,
  "version": "0.4.7",
  "requires_full_reinstall": false,
  "patch_zip": {
    "name": "app-patch-v0.4.7.zip",
    "sha256": "...",
    "size": 180000
  },
  "delete": []
}
```

- `requires_full_reinstall: true` si `site-packages/` ou `python/` changent
- `delete` liste les fichiers à supprimer (ex : module renommé entre deux versions)
- `patch_zip` contient uniquement les fichiers sources modifiés

### Logique de mise à jour dans l'app (au démarrage)

1. `_apply_pending_update()` s'exécute en premier — applique un patch téléchargé lors
   du lancement précédent (si `_update_pending/` existe)
2. `check_update()` tourne en thread daemon :
   - Interroge GitHub Releases API → dernière release stable
   - Si même version → rien
   - Si nouvelle version → télécharge `metadata.json` depuis les assets
   - Si `requires_full_reinstall: true` → log (futur : notification GUI Étape 4.7+)
   - Sinon → télécharge `app-patch.zip`, vérifie SHA256, extrait dans `_update_pending/`
3. Au **prochain démarrage**, `_apply_pending_update()` déplace les fichiers en place
   et supprime les fichiers listés dans `delete`

Ce mécanisme en deux temps évite tout problème de fichiers verrouillés sous Windows.

### Workflow développeur (release.sh)

```bash
./release.sh X.Y.Z              # release standard (sources uniquement)
./release.sh X.Y.Z --full-reinstall  # si site-packages/ ou python/ changent
```

`release.sh` automatise :
1. Mise à jour `VERSION` dans `pdf_header.py` et `version.txt`
2. Mise à jour `BUILD_ID` (date du jour)
3. Validation syntaxe Python (`ast.parse`)
4. `git commit + tag vX.Y.Z + push`
5. `python3 build_dist.py` → génère le zip + `metadata.json` + `app-patch-vX.Y.Z.zip`
6. `gh release upload vX.Y.Z ...` (si `gh` CLI disponible, sinon instructions manuelles)

### GitHub Actions (.github/workflows/release.yml)

Déclenché sur push tag `v*.*.*`. Crée automatiquement la GitHub Release avec les
release notes générées depuis les commits. Le build et l'upload des assets sont
gérés localement via `release.sh` (le dossier `tcltk/` n'est pas disponible sur CI).

### Changements dans build_dist.py

- Génère `metadata.json` avec version, `requires_full_reinstall`, hash SHA256 du patch zip
- Génère `app-patch-vX.Y.Z.zip` contenant uniquement les fichiers `.py` du projet
- Argument CLI `--full-reinstall` pour forcer `requires_full_reinstall: true`

---

## Étape 4.6.2 — Corrections post-release et canal beta
**Statut : Terminé ✓**
**Version livrée : v0.4.6.6 → v0.4.6.10+**
**Prérequis : Étape 4.6.1 terminée**

Série de corrections identifiées après le premier déploiement chez un utilisateur réel.

### Corrections critiques (v0.4.6.6)

**Bug 1 : app-patch manquant dans les releases GitHub**
`release.sh` cherchait `app-patch-{VERSION}.zip` (sans `v`) mais `build_dist.py`
génère `app-patch-v{VERSION}.zip` (avec `v`). Le fichier n'était jamais uploadé →
mécanisme de mise à jour silencieusement cassé depuis v0.4.6.1.
Fix : `PATCH_ZIP="dist/app-patch-${TAG}.zip"` dans `release.sh`.

**Bug 2 : Version affichée deux fois dans l'UI**
`self.root.title()` et le label topbar affichaient tous les deux la version.
Fix : `self.root.title("PDF Header Tool")` — version uniquement dans la topbar.

**Bug 3 : Nom du dossier dans le ZIP incohérent après auto-update**
Le zip contenait `PDFHeaderTool-vX.Y.Z-build-.../` — nom stale après mise à jour.
Fix : dossier interne = `PDFHeaderTool/` (stable), zip = `PDFHeaderTool-vX.Y.Z-windows.zip`.

### Logging des mises à jour (v0.4.6.7)

`_apply_pending_update()` et `_check_update_thread()` écrivent désormais des traces
timestampées sur stdout, capturées par `lancer.bat` dans `pdf_header_launch.log`.
Events : `UPDATE_APPLY dossier detecte`, `UPDATE_APPLY fichier applique: X`,
`UPDATE_APPLY succes`, `UPDATE_CHECK version courante: X`,
`UPDATE_CHECK nouvelle version disponible: X`, `UPDATE_CHECK patch mis en attente`,
`UPDATE_CHECK ERREUR: ...`.

### SSL certificate verify failed sur Python Embedded (v0.4.6.8 — full-reinstall)

Python Embedded n'inclut pas les certificats CA Windows → `urllib` échouait sur
toutes les requêtes HTTPS vers l'API GitHub.
Fix :
- `certifi` ajouté aux dépendances pip cross-compilées dans `build_dist.py`
- `_check_update_thread()` crée `ssl.create_default_context(cafile=certifi.where())`
- Fallback sur `ssl.create_default_context()` si `certifi` absent

### Amélioration UX du mécanisme de mise à jour (v0.4.6.9+)

**`_RUNNING_VERSION`** — variable module-level initialisée à `VERSION` et mise à jour
par `_apply_pending_update()`. `_check_update_thread()` compare contre `_RUNNING_VERSION`
au lieu de `VERSION` → évite le double téléchargement quand un patch vient d'être appliqué.

**Redémarrage immédiat après patch** — après application d'un patch, le process est
relancé avant que la GUI ne soit créée (Windows : `subprocess.Popen + DETACHED_PROCESS`,
Linux : `os.execv`). Résultat : la nouvelle version est active dès ce lancement (2 étapes
au lieu de 3).

### Canal de distribution beta/release (v0.4.6.11+)

**Objectif :** protéger les utilisateurs "release" des mises à jour en cours de dev.

**Mécanisme :** constante `CHANNEL = "release" | "beta"` dans `pdf_header.py`.
- Canal `release` → `GET /releases/latest` (stable uniquement — ignore les pre-releases)
- Canal `beta` → `GET /releases[0]` (toutes releases, pre-releases incluses)

GitHub `/releases/latest` ignore nativement les pre-releases → les utilisateurs stables
ne voient jamais les betas.

**`release.sh --beta` :**
- Versionnement : `X.Y.Z-beta.N` (ex: `0.4.7-beta.1`)
- Auto-bump beta : `0.4.7-beta.1` → `0.4.7-beta.2`
- Met à jour `CHANNEL = "beta"` dans `pdf_header.py` via `sed`
- Marque la GitHub Release comme pre-release (`gh release edit --prerelease`)

```bash
./release.sh              # stable (utilisateurs finaux)
./release.sh --beta       # beta (testeurs) — auto-bump
./release.sh 0.4.7-beta.1 # beta explicite
```

---

## Étape 4.6.3 — Système de logs multi-niveaux
**Statut : Terminé ✓**
**Version livrée : v0.4.6.11**
**Prérequis : Étape 4.6.2 terminée**

Mise en place d'un système de logs solide avant le découpage modulaire (Étape 4.7).
Sources consultées : recommandations Gemini + ChatGPT + analyse Claude.

### Architecture

**3 profils de verbosité :**
- `simple` (prod) → INFO — démarrage, actions majeures, erreurs, check update
- `medium` (beta/support) → DEBUG — + entrée/sortie fonctions clés, timings
- `full` (dev) → DEBUG + stderr — + traces UI, états internes, calculs layout, PDF_INSERT_*

**Défaut automatique par canal :** `release=simple`, `beta=medium`

**2 fichiers de log** (dans `INSTALL_DIR`) :
- `pdf_header_app.log` — tous niveaux selon profil, rotation 1MB × 5 backups
- `pdf_header_errors.log` — ERROR+ toujours actif, rotation 500KB × 3 backups

**6 sous-loggers par domaine** (prépare la migration vers `app/` à l'Étape 4.7) :
- `pdf_header.app`, `.ui`, `.pdf`, `.update`, `.config`, `.font`

### Changements dans pdf_header.py

- `_setup_logger(profile)` + `_default_log_profile()`
- `_log_timed(logger, label)` décorateur START/OK/FAILED + elapsed_ms
- `_log_session_start()` : session_id, version, OS, Python, runtime, profile
- `_global_exception_handler` : sys.excepthook → log_app.critical + messagebox
- `_debug_log(msg, level)` conservé comme wrapper rétrocompatible (CLAUDE.md)
- Migration config : `"debug_enabled"` (bool) → `"log_profile"` (str)
- Events structurés `PDF_INSERT_PARAMS` + `PDF_INSERT_RESULT` (profil full)
  → prépare la future dataclass `InsertResult` pour les tests pytest (Étape 4.9)
- Capture retour `insert_textbox()` → `remaining_chars` (troncature détectée)

### Instrumentation (par profil)

| Profil | Events |
|---|---|
| simple | CONFIG_LOAD/SAVE, OPEN_FILES/FOLDER, PDF_OPEN, PDF_PROCESS_*, PDF_SKIP, UPDATE_* |
| medium | + RENDER (elapsed_ms), FONT_SCAN_DONE, UPDATE_CHECK_START, timings |
| full | + UI_CLICK, UI_FONT_CHANGE, OVERLAY_UPDATE, PDF_INSERT_PARAMS/RESULT |

---

## Étape 4.7 — Découpage modulaire (multi-fichiers)
**Statut : À faire — dépend de l'Étape 4.6.1**
**Version cible : 0.4.7**
**Prérequis : structure Python Embarqué en place (Étape 4.6)**

Migrer `pdf_header.py` d'un script monolithique vers un package structuré `app/`.

### Nouvelle arborescence
```
PDFHeaderTool/
├── python/                    # Python Embarqué (inchangé)
├── site-packages/             # dépendances (inchangées)
├── app/
│   ├── __init__.py
│   ├── config.py              # load_config(), save_config(), migration, DEFAULT_CONFIG
│   ├── models.py              # dataclasses : Config, Position, FontDescriptor
│   ├── constants.py           # COLORS, SIZES, TIMINGS, BUILTIN_FONTS, PRIORITY_FONTS, etc.
│   ├── update.py              # check_update(), logique GitHub
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_service.py     # fitz.open(), insert_textbox(), sauvegarde
│   │   ├── layout_service.py  # calculs position/rotation, wrapping, ratio ↔ points
│   │   └── font_service.py    # _get_font_dirs(), _find_priority_fonts(), _get_fitz_font_args()
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py     # PDFHeaderApp (classe principale)
│       ├── sidebar.py         # _build_sidebar() et toutes ses sections
│       └── file_panel.py      # panneau liste des fichiers
├── pdf_header.py              # point d'entrée léger (5-10 lignes)
├── version.txt
├── lancer.bat
└── setup.bat
```

### Principes de découpage
- Fonctions **pures** (calculs, wrapping, layout) → `services/` — testables sans GUI
- Config (chargement, sauvegarde, migration JSON) → `config.py`
- Constantes globales (issues de l'Étape 4.5) → `constants.py`
- Dataclasses → `models.py`
- `PDFHeaderApp` reste dans `ui/main_window.py`, délègue aux services

### Point d'entrée `pdf_header.py` (allégé)
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.ui.main_window import PDFHeaderApp
import customtkinter as ctk

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    PDFHeaderApp().mainloop()
```

### Rétrocompatibilité
- La config JSON (`pdf_header_config.json`) n'est pas modifiée
- La logique de migration existante est déplacée vers `config.py` sans changement

### Mise à jour `CLAUDE.md`
- Mettre à jour la section Architecture complète avec la nouvelle arborescence
- Supprimer la contrainte "fichier unique"
- Documenter les méthodes clés par module

---

## Étape 4.8 — Préparation i18n (traduction)
**Statut : À faire — dépend de l'Étape 4.7**
**Version cible : 0.4.8**
**Prérequis : découpage modulaire terminé (Étape 4.7)**

Introduire une couche de traduction sans modifier le comportement visible.
Langue par défaut : français.

### Système de traduction
- `app/i18n/__init__.py` : fonction `t(key, **kwargs)` avec fallback FR si clé absente
- `app/i18n/fr.py` : dictionnaire de toutes les chaînes UI (clés stables)
- `app/i18n/en.py` : traduction anglaise (à compléter progressivement)
- Clé de config : `"language"` (`"fr"` par défaut)

### Convention de clés
```python
t("sidebar.section.header_text")  # → "TEXTE DE L'EN-TÊTE"
t("sidebar.apply_button")         # → "Appliquer"
t("error.pdf_corrupt")            # → "Le fichier PDF est corrompu."
```

### Règles de remplacement
- Toutes les chaînes UI → `t("clé")`
- Chaînes internes (log, config keys, fitz args) → conservées en dur

### Sélecteur de langue
- Ajout dans Préférences (Étape 13) : `fr` / `en`
- Rechargement dynamique des chaînes à la volée ou relance de l'app

---

## Étape 4.9 — Tests unitaires, typing et qualité
**Statut : À faire — dépend de l'Étape 4.7**
**Version cible : 0.4.9**
**Prérequis : découpage modulaire terminé (Étape 4.7)**

### Tests unitaires
- Framework : `pytest` (dépendance dev uniquement — non bundlé dans la distribution)
- Dossier : `tests/`
- Priorité :
  - `layout_service` : calcul position depuis preset + marges, conversion ratio ↔ pts
  - `config.py` : migration ancienne → nouvelle config
  - `services/` : composition texte (préfixe/suffixe/date), wrapping par mots

### Type hints
- `typing` sur toutes les fonctions des `services/` et `config.py`
- Méthodes critiques de `PDFHeaderApp` (`_apply`, `_render_preview`)
- Callbacks UI : non typés (trop verbeux pour peu de valeur)

### Dataclasses
- `models.py` : `Config` (remplace le dict `cfg`), `FontDescriptor`, `Position`
- Préparer `Element` (sera utilisé à l'Étape 10)
- `Config` expose `.get(key, default)` pour la migration douce

### Logs structurés
- `logging.getLogger(__name__)` par module, niveaux `DEBUG` / `INFO` / `WARNING` / `ERROR`
- `_debug_log()` conservé comme wrapper (alias vers le logger du module principal)

### Validation de config
- Types et plages vérifiés au chargement (`font_size` in [4, 72], `rotation` in [0, 90, 180, 270])
- `config_version` dans le JSON pour versionner les migrations futures

---

## Étape 5 — Options de sauvegarde
**Statut : À faire — dépend de l'Étape 1**
**Version cible : 0.5.0**

Remplacer le comportement fixe de sauvegarde par des options configurables.

### Comportement actuel
Sauvegarde toujours dans `<dossier_source>_avec_entete/` au même niveau.

### Nouvelles options (boutons radio dans la sidebar)
- **Écraser le fichier original** — remplace directement le fichier source
- **Copie dans un sous-dossier** — comportement actuel,
  dossier `<dossier_source>_avec_entete/` au même niveau *(défaut)*
- **Copie dans le même dossier** — même dossier que la source,
  avec suffixe ou préfixe au nom du fichier
  - Sous-option : champ pour définir le suffixe/préfixe du nom de fichier
    (ex : `_modifie`, `copie_`, etc.)
- **Choisir l'emplacement** — ouvre la boîte de dialogue système à chaque fois

### Détails d'implémentation
- Nouvelle section "Sauvegarde" dans la sidebar
- Avertissement visuel si "Écraser" est sélectionné
- Sauvegarder le choix dans `pdf_header_config.json`

---

## Étape 6 — Appliquer à toute la liste
**Statut : À faire — dépend de l'Étape 3**
**Version cible : 0.6.0**

Ajouter un bouton pour appliquer les réglages actuels à tous les fichiers
non traités de la liste en une seule action.

### Comportement
- Bouton **"Appliquer à tous"** dans la bottombar
- Applique : tous les éléments actifs (textes + images), leurs positions,
  styles, et options pages
- Une barre de progression s'affiche pendant le traitement
- Les cartes de la liste se mettent à jour en temps réel au fur et à mesure
- Les fichiers déjà marqués "Traité" sont ignorés

### Détails d'implémentation
- Traitement dans un thread séparé pour ne pas bloquer l'interface
- Bouton désactivé pendant le traitement
- Possibilité d'annuler en cours de traitement

---

## Étape 7 — Rapport de session
**Statut : À faire — dépend de l'Étape 3**
**Version cible : 0.7.0**

Afficher un rapport à la fin d'une session et exporter un fichier CSV.

### Rapport dans l'interface
Quand tous les fichiers ont été traités (ou via un bouton "Voir le rapport"),
afficher une fenêtre modale récapitulative :
- Nombre de fichiers traités / ignorés / en erreur
- Liste des fichiers avec leur statut et le dossier de destination
- Bouton "Fermer et continuer" / "Quitter"

### Export CSV
- Bouton **"Exporter le rapport"** dans la fenêtre de rapport
- Colonnes : `nom_fichier`, `statut`, `dossier_source`, `dossier_destination`, `date_heure`
- Sauvegardé dans le dossier source ou à l'emplacement choisi par l'utilisateur

---

## Étape 8 — Améliorations UX
**Statut : À faire — dépend des Étapes 1 à 3**
**Version cible : 0.8.0**

- **Raccourcis clavier** :
  - `Entrée` → Appliquer
  - `Échap` → Passer
  - `Ctrl+Z` → Annuler le dernier Appliquer
  - `↑` / `↓` → Naviguer dans la liste des fichiers
- **Zoom prévisualisation** : `Ctrl+Molette` ou boutons `+` / `-`
- **Historique des dossiers récents** : liste déroulante sur l'écran d'accueil
  (5 derniers dossiers ouverts, sauvegardés dans la config)
- **Annuler le dernier Appliquer** : bouton `↩ Annuler` dans la bottombar,
  supprime le fichier généré et remet le fichier en statut "Non traité"

---

## Étape 9 — Glisser / déposer
**Statut : À faire — dépend de l'Étape 2**
**Version cible : 0.9.0**

- Ajouter `tkinterdnd2` aux dépendances dans `_bootstrap()`
- Remplacer `ctk.CTk()` par `TkinterDnD.Tk()` avec thème CustomTkinter appliqué manuellement
- Zone de drop : toute la fenêtre (écran d'accueil) ou le panneau liste (si déjà chargé)
- Accepter : fichiers `.pdf` individuels et dossiers
- Indicateur visuel pendant le survol (bordure colorée)

---

## Étape 10 — Éléments multiples : architecture
**Statut : À faire — dépend des Étapes 1, 2, 4**
**Version cible : 1.0.0**

Refonte de l'architecture interne pour supporter plusieurs éléments
(textes et images) positionnables indépendamment sur le PDF.
C'est une étape fondatrice dont dépendent les Étapes 11, 12 et 13.

### Nouveau modèle de données

Remplacer la position unique `last_x_ratio / last_y_ratio` par une liste
d'éléments dans la config :

```json
{
  "elements": [
    {
      "id": "elem_1",
      "type": "text",
      "content_mode": "filename",
      "prefixe": "CONFIDENTIEL – ",
      "suffixe": "",
      "custom_text": "",
      "color_hex": "#FF0000",
      "font_size": 8,
      "font_name": "cour",
      "x_ratio": 0.85,
      "y_ratio": 0.97
    },
    {
      "id": "elem_2",
      "type": "text",
      "content_mode": "custom",
      "custom_text": "Société XYZ",
      "color_hex": "#000000",
      "font_size": 6,
      "font_name": "cour",
      "x_ratio": 0.1,
      "y_ratio": 0.97
    }
  ],
  "all_pages": true,
  "save_mode": "subfolder"
}
```

### Refonte de la sidebar

La section "Texte de l'en-tête" et "Style" sont remplacées par un
**panneau d'éléments** :
- Liste des éléments actifs avec leur type (🔤 texte / 🖼 image) et un aperçu
- Boutons : **+ Texte** / **+ Image**
- Cliquer sur un élément dans la liste le sélectionne → ses options
  s'affichent dans un panneau de détail en dessous
- Boutons par élément : **↑ ↓** (réordonner) / **🗑 Supprimer**
- L'élément sélectionné est mis en surbrillance sur la prévisualisation

### Refonte du canvas

- Le clic positionne **l'élément actuellement sélectionné** dans la sidebar
- Chaque élément est représenté sur la prévisualisation par son aperçu
  avec une **poignée de sélection** (petit carré coloré)
- Cliquer sur une poignée sélectionne l'élément correspondant dans la sidebar

### Détails d'implémentation
- Nouvelle classe `Element` (dataclass) : `id`, `type`, `x_ratio`, `y_ratio`
  + attributs spécifiques texte ou image
- `PDFHeaderApp.elements` : liste d'`Element` remplace `pos_ratio_x/y`
- `_draw_overlay()` itère sur tous les éléments pour les afficher
- `_apply()` itère sur tous les éléments pour les écrire dans le PDF
- Rétrocompatibilité : si `pdf_header_config.json` ancien format détecté,
  migrer automatiquement vers le nouveau format

---

## Étape 11 — Éléments texte multiples
**Statut : À faire — dépend de l'Étape 10**
**Version cible : 1.1.0**

Implémenter complètement les éléments de type texte dans le nouveau modèle.

### Champ texte simple (une ligne)
- Options : préfixe (case à cocher), nom du fichier (sans .pdf),
  suffixe (case à cocher), ou texte custom
- Les champs de saisie préfixe/suffixe/custom sont placés **au-dessus**
  de leur label respectif
- Style par élément : couleur, taille, police (parmi les polices PDF standard
  de PyMuPDF : `cour`, `helv`, `tiro`, etc.)

### Bloc de texte (multiligne)
- Case à cocher **"Bloc multiligne"** pour basculer du champ simple au bloc
- Zone de saisie multiligne (`ctk.CTkTextbox`)
- Le texte peut contenir des sauts de ligne `\n`
- Option : largeur max du bloc en pts (retour à la ligne automatique)
- Utiliser `fitz.Page.insert_textbox()` à la place de `insert_text()`

### Aperçu temps réel
- L'aperçu dans la sidebar et sur le canvas se met à jour à chaque frappe

---

## Étape 12 — Éléments image
**Statut : À faire — dépend de l'Étape 10**
**Version cible : 1.2.0**

Implémenter les éléments de type image.

### Sources
- **Fichier image** : PNG, JPG, JPEG via boîte de dialogue
- **SVG** : converti en PNG via `cairosvg` avant insertion
  (dépendance optionnelle — avertir si non installé)
- **Logo enregistré dans la config** : chemin sauvegardé dans
  `pdf_header_config.json`, rechargé automatiquement à chaque session
  - Bouton "Définir comme logo par défaut" dans le panneau de détail

### Options
- **Largeur** en pts — hauteur calculée automatiquement (proportions conservées)
- **Hauteur** en pts — si modifiée manuellement, déverrouille les proportions
- **Opacité** : slider 0% → 100% (`ctk.CTkSlider`)
- Aperçu miniature de l'image dans le panneau de détail sidebar

### Positionnement
- Clic sur la prévisualisation comme pour le texte
- La position correspond au **coin supérieur gauche** de l'image

### Détails d'implémentation
- `fitz.Page.insert_image()` pour l'insertion
- Stocker le chemin de l'image dans l'`Element`, pas les données binaires
- Avertir si le fichier image n'existe plus au moment de l'Appliquer

---

## Étape 13 — Préférences globales
**Statut : À faire — dépend de l'Étape 1**
**Version cible : 1.3.0**

Fenêtre de préférences séparée accessible via un bouton engrenage ⚙ dans la
topbar. Les préférences définissent les valeurs par défaut appliquées à chaque
nouvel élément créé et à chaque nouvelle session.

### Interface
- Bouton **⚙** dans la topbar (côté droit) → ouvre une fenêtre `ctk.CTkToplevel`
- Titre : "Préférences"
- Sections :

#### Apparence des éléments par défaut
| Paramètre | Widget |
|-----------|--------|
| Couleur par défaut | Swatch + affichage hex (comme dans la sidebar) |
| Police par défaut | Menu déroulant (`ctk.CTkOptionMenu`) parmi les polices PDF standard PyMuPDF : Courier, Helvetica, Times |
| Taille par défaut | Champ numérique (`ctk.CTkEntry` avec validation 4–72) |
| Taille de l'interface | Champ numérique `ui_font_size` (plage 8–18, défaut 12) — applique la taille de base à tous les labels de la sidebar, topbar, bottombar et panneau fichiers |

#### Comportement par défaut
| Paramètre | Widget |
|-----------|--------|
| Option pages | Toggle : Toutes les pages / Première page uniquement |
| Mode de sauvegarde | Boutons radio : Sous-dossier / Même dossier / Écraser / Choisir |
| Activation des logs debug | Toggle (case à cocher) — active l'écriture dans `INSTALL_DIR/pdf_header_debug.log` (mode append). Utile pour diagnostiquer les problèmes remontés par les utilisateurs. |

#### Boutons
- **Enregistrer** → sauvegarde dans `pdf_header_config.json` sous clé `preferences`
  et ferme la fenêtre
- **Annuler** → ferme sans sauvegarder
- **Réinitialiser** → remet les valeurs d'usine (avec confirmation)

### Comportement
- À chaque création d'un nouvel élément texte, ses valeurs initiales sont
  celles des préférences globales
- Les préférences ne modifient PAS les éléments déjà créés
- Un bandeau discret dans la fenêtre le rappelle :
  *"Les préférences s'appliquent aux nouveaux éléments uniquement"*

### Stockage dans `pdf_header_config.json`
```json
{
  "preferences": {
    "default_color_hex": "#FF0000",
    "default_font_name": "cour",
    "default_font_size": 8,
    "default_all_pages": true,
    "default_save_mode": "subfolder",
    "ui_font_size": 12,
    "debug_enabled": false
  }
}
```

### Détails d'implémentation
- Nouvelle méthode `_open_preferences_window()` dans `PDFHeaderApp`
- Nouvelle méthode `_apply_preferences_to_new_element(element)` appelée dans
  `_add_text_element()` et `_add_image_element()`
- La fenêtre est modale (bloque l'interaction avec la fenêtre principale)

---

## Étape 14 — Templates enrichis
**Statut : À faire — dépend des Étapes 11, 12 et 13**
**Version cible : 1.4.0**

Sauvegarder et réutiliser des ensembles d'éléments complets incluant les
options de sauvegarde et l'option pages. Accessible depuis la sidebar ET
depuis un bouton dédié dans la topbar.

### Définition d'un template
Un template est un snapshot complet contenant :
- La liste `elements` (textes + images avec positions et styles)
- L'option pages (`all_pages` : toutes / première)
- Le mode de sauvegarde (`save_mode`)
- Le suffixe/préfixe de renommage si mode "même dossier"

### Interface — Sidebar
- Nouvelle section **"Templates"** en bas de la sidebar
- **Menu déroulant** listant les templates sauvegardés + option "Aucun"
- **Bouton "Appliquer"** → charge le template sur le PDF courant
- **Bouton "Appliquer à tous"** → applique le template à tous les PDFs
  non traités de la liste (avec barre de progression, en thread séparé)
- **Bouton "💾 Sauvegarder"** → sauvegarde l'état actuel comme nouveau template
  (demande un nom)
- **Bouton "🗑 Supprimer"** → supprime le template sélectionné (avec confirmation)

### Interface — Topbar
- Bouton **"Templates"** dans la topbar (à côté du bouton ⚙)
- Ouvre une fenêtre `ctk.CTkToplevel` de gestion complète des templates :
  - Liste scrollable de tous les templates avec nom + date de création
  + aperçu du nombre d'éléments
  - Boutons : **Charger** / **Renommer** / **Dupliquer** / **Supprimer**
  - Bouton **"Exporter (.json)"** → sauvegarde le template sélectionné
    comme fichier `.json` partageable
  - Bouton **"Importer (.json)"** → charge un template depuis un fichier `.json`

### Application à toute la liste
- **"Appliquer à tous"** depuis la sidebar ou la fenêtre topbar
- Confirmation : *"Appliquer le template 'X' aux Y fichiers non traités ?"*
- Traitement en thread séparé avec barre de progression
- Chaque fichier traité est marqué dans le panneau liste
- Les fichiers déjà marqués "Traité" sont ignorés sauf si l'option
  "Inclure les fichiers déjà traités" est cochée

### Stockage
Fichier `pdf_header_templates.json` dans `INSTALL_DIR` :
```json
{
  "templates": [
    {
      "name": "En-tête standard société",
      "created_at": "2025-01-01T12:00:00",
      "all_pages": true,
      "save_mode": "subfolder",
      "save_suffix": "",
      "elements": [
        {
          "id": "elem_1",
          "type": "text",
          "content_mode": "filename",
          "prefixe": "",
          "suffixe": "",
          "custom_text": "",
          "color_hex": "#FF0000",
          "font_size": 8,
          "font_name": "cour",
          "x_ratio": 0.85,
          "y_ratio": 0.97
        },
        {
          "id": "elem_2",
          "type": "image",
          "image_path": "C:/Users/.../logo.png",
          "width_pt": 60,
          "height_pt": 20,
          "opacity": 1.0,
          "x_ratio": 0.05,
          "y_ratio": 0.97
        }
      ]
    }
  ]
}
```

### Détails d'implémentation
- Les chemins d'images dans un template sont absolus — avertir si une image
  n'existe plus au chargement, proposer de la relocaliser
- Charger un template **ne déclenche pas immédiatement** le traitement —
  il charge les éléments dans la sidebar pour que l'utilisateur puisse
  vérifier / ajuster avant de cliquer Appliquer
- Exception : "Appliquer à tous" déclenche le traitement directement
  après confirmation


---

## Backlog — Points à traiter (sans étape fixée)

### Signature de code Windows (SmartScreen)
Depuis v0.4.6.1, Windows affiche une boîte de dialogue "Éditeur inconnu" au premier lancement
de `lancer.bat` ou de l'app. Ce comportement est dû à l'absence de signature de code (Code Signing).

**Causes :** L'exécutable et les scripts non signés → Windows SmartScreen les bloque par défaut.

**Solutions possibles (par ordre de complexité) :**
1. **Certificat OV/EV auto-signé ou payant** (Sectigo, DigiCert ~150-500 €/an) — supprime totalement
   la boîte de dialogue SmartScreen
2. **Signpathio.org** (certificat open source gratuit, pour projets open source) — à évaluer
3. **Compiler en `.exe` avec PyInstaller + signer l'exe** — plus complexe mais meilleure UX
4. **Information utilisateur dans le README** — solution court terme : documenter que le message
   est normal et expliquer comment le contourner ("Plus d'informations → Exécuter quand même")

**Priorité :** Basse pour l'instant. À traiter avant la v1.0.0 (ou si demande utilisateur forte).
**Impact :** Uniquement Windows. Linux non concerné.

---

### Launcher natif Windows (Go / Rust / C#)

Un launcher natif (.exe) remplacerait `lancer.bat` pour une meilleure UX : splash screen,
fenêtre d'erreur GUI, icône dans la barre des tâches.

**Analyse (2026-02-22) :**

| Critère | .bat actuel | Go (.exe) | Rust (.exe) | C# (.exe) |
|---------|-------------|-----------|-------------|-----------|
| SmartScreen | bloqué | bloqué sans cert | bloqué sans cert | bloqué sans cert |
| Cross-compile Linux→Win | natif | trivial | complexe | impossible |
| Splash screen | non | oui | oui | oui |
| Fenêtre d'erreur GUI | non | oui | oui | oui |
| Taille binaire | ~2 KB | ~2 MB | ~500 KB | ~60 MB (self-contained) |
| Dépendance toolchain | aucune | Go | Rust + mingw | .NET SDK |

**Conclusion :** SmartScreen n'est PAS résolu par un launcher natif — il nécessite un
certificat de signature de code (OV/EV) quelle que soit la technologie.
Si launcher natif : Go est le meilleur compromis (cross-compile trivial depuis Linux).

**Priorité :** Post-v1.0.0. Pas de valeur ajoutée avant la signature de code.

---

### Distribution installable (Inno Setup / NSIS)

En complément de la distribution portable (ZIP), une distribution installable permettrait :
shortcuts Bureau/Menu Démarrer, associations de fichiers `.pdf`, désinstalleur Windows propre.

**Outils envisagés (gratuits, utilisables depuis Linux) :**
- **Inno Setup** (via Wine) — script `.iss`, génère un `.exe` installeur signable
- **NSIS** (Nullsoft Scriptable Install System) — cross-platform, bien documenté

**Priorité :** Post-v0.5.0. La distribution portable est suffisante pour les premiers utilisateurs.

---

### Dettes techniques (avant v0.5.0)

#### Comparaison de version par chaîne
~~Dans `_check_update_thread()`, la comparaison `remote_version == _RUNNING_VERSION` était
correcte pour le cas "déjà à jour". Non urgent actuellement.~~
**Résolu (feat/multi-level-logging)** : remplacement par `_version_gt(remote, local)` (stdlib-only,
gère X.Y.Z, X.Y.Z.W, X.Y.Z-beta.N). Empêche les downgrades (ex: remote=0.4.6.9 vs local=0.4.6.10-beta.1).
À migrer dans `app/update.py` lors de l'Étape 4.7.

#### `requires_full_reinstall: true` sans notification GUI
Si une release nécessite une réinstallation complète, le thread abandonne silencieusement.
L'utilisateur ne voit aucun message. Prévu : notification GUI (Étape 4.7+).

#### `PATCH_FILES` n'inclut pas `app/`
Actuellement `PATCH_FILES = ["pdf_header.py", "version.txt"]`. À mettre à jour dès
que le package `app/` sera créé (Étape 4.7) pour inclure `app/**/*.py`.

---

## Conventions pour chaque étape

1. Avant v0.4.7 : modifier `pdf_header.py`. À partir de v0.4.7 : modifier le module concerné dans `app/`
2. Vérifier syntaxe :
   ```bash
   python3 -c "import ast; ast.parse(open('pdf_header.py').read())"
   ```
3. Tester sur Windows avant de merger
4. Mettre à jour `CLAUDE.md` si l'architecture change
5. Marquer l'étape comme **Statut : Terminé ✓** dans ce fichier
6. Workflow de release (depuis v0.4.6.1) :
   ```bash
   # 1. Créer une branche dédiée
   git checkout -b feat/step-X.Y
   # 2. Travailler, committer
   # 3. Merger dans main
   git checkout main && git merge feat/step-X.Y
   # 4. Lancer le script de release (bump version + build + tag + push + upload)
   ./release.sh X.Y.Z
   # Si site-packages/ ou python/ ont changé :
   ./release.sh X.Y.Z --full-reinstall
   ```
7. Pour ce cycle de reprise, démarrer à `v0.0.1` et viser `v1.0.0` à l'étape 10.
8. Format obligatoire du build global : `build-YYYY.MM.DD.NN` (ex: `build-2026.02.20.04`).
9. À chaque itération, incrémenter ce build global sur `pdf_header.py`, `README.md`, `CLAUDE.md`, `ROADMAP.md`.
10. Vérifier que ce build apparaît dans les logs runtime (`pdf_header.py`).
