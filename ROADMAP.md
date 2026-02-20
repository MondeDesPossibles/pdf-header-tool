# ==============================================================================
# PDF Header Tool — ROADMAP.md
# Version : 0.0.1
# Build   : build-2026.02.20.06
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
- Si Python absent : exécute `python` pour déclencher Microsoft Store, puis recheck en boucle (timeout 60s)
- Si Python détecté : lance `install.py`
- Log complet dans `pdf_header_install.log` (dossier de `install.bat`)

---

## Étape 1 — Migration CustomTkinter
**Statut : À faire**
**Version cible : 0.1.0**

Remplacer tkinter par CustomTkinter pour un rendu moderne.

- Remplacer `import tkinter as tk` par `import customtkinter as ctk`
- Remplacer `tk.Tk()` par `ctk.CTk()`
- Remplacer tous les widgets tk par leurs équivalents ctk
  (`ctk.CTkFrame`, `ctk.CTkLabel`, `ctk.CTkButton`, `ctk.CTkRadioButton`, etc.)
- Remplacer `tk.Spinbox` → `ctk.CTkEntry` avec validation numérique
  (CustomTkinter n'a pas de Spinbox natif)
- Garder `tk.Canvas` pour la prévisualisation PDF
  (CustomTkinter n'a pas de canvas, on mixe les deux)
- Définir un thème global : `ctk.set_appearance_mode("dark")`
  et `ctk.set_default_color_theme("blue")`
- Ajouter `customtkinter` à la liste des dépendances dans `_bootstrap()`

---

## Étape 2 — Écran d'accueil avec choix fichier / dossier
**Statut : À faire — dépend de l'Étape 1**
**Version cible : 0.2.0**

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
**Statut : À faire — dépend de l'Étape 2**
**Version cible : 0.3.0**

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
**Statut : À faire — dépend de l'Étape 1**
**Version cible : 0.4.0**

Corrections et améliorations de la section "Texte de l'en-tête" dans la sidebar.

### Changements
- **Supprimer l'extension `.pdf`** du texte injecté par défaut
  (ex : `rapport_2024` au lieu de `rapport_2024.pdf`)
- **Remplacer les 4 radio boutons** par :
  - Case à cocher **Préfixe** (activable indépendamment)
  - Champ de saisie préfixe — placé **au-dessus** du label "Préfixe"
  - Nom du fichier (toujours présent, non modifiable, affiché en lecture seule)
  - Case à cocher **Suffixe** (activable indépendamment)
  - Champ de saisie suffixe — placé **au-dessus** du label "Suffixe"
  - Case à cocher **Texte personnalisé** — remplace le nom du fichier si coché
  - Champ de saisie texte custom — placé **au-dessus** du label "Texte custom"
- Préfixe et suffixe peuvent être actifs simultanément
- L'aperçu temps réel reste en bas de la section

### Exemple de résultat
Préfixe "CONFIDENTIEL –" + nom "rapport_2024" + suffixe "– V2" →
`CONFIDENTIEL – rapport_2024 – V2`

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

#### Comportement par défaut
| Paramètre | Widget |
|-----------|--------|
| Option pages | Toggle : Toutes les pages / Première page uniquement |
| Mode de sauvegarde | Boutons radio : Sous-dossier / Même dossier / Écraser / Choisir |

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
    "default_save_mode": "subfolder"
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

## Conventions pour chaque étape

1. Modifier `pdf_header.py` uniquement (sauf si la dépendance touche `install.py`)
2. Incrémenter `VERSION` dans le script et `version.txt`
3. Vérifier syntaxe :
   ```bash
   python3 -c "import ast; ast.parse(open('pdf_header.py').read())"
   ```
4. Tester sur Windows avant de merger
5. Mettre à jour `CLAUDE.md` si l'architecture change
6. Marquer l'étape comme **Statut : Terminé ✓** dans ce fichier
7. Commiter avec un message clair :
   ```bash
   git add .
   git commit -m "feat: étape X — description"
   git tag vX.Y.Z
   git push && git push origin vX.Y.Z
   ```
8. Pour ce cycle de reprise, démarrer à `v0.0.1` et viser `v1.0.0` à l'étape 10.
9. Format obligatoire du build global : `build-YYYY.MM.DD.NN` (ex: `build-2026.02.20.04`).
10. À chaque itération, incrémenter ce build global sur `pdf_header.py`, `install.py`, `install.bat`,
    `README.md`, `CLAUDE.md`, `ROADMAP.md`.
11. Vérifier que ce build apparaît dans les logs runtime (`install.bat`, `install.py`, `pdf_header.py`).
