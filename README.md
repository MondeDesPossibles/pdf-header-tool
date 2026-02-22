# ==============================================================================
# PDF Header Tool — README.md
# Version : 0.4.6
# Build   : build-2026.02.21.07
# Repo    : MondeDesPossibles/pdf-header-tool
# ==============================================================================

# PDF Header Tool

Outil GUI Python pour insérer automatiquement un en-tête sur les pages de vos fichiers PDF.

---

## Fonctionnalités

- **Prévisualisation interactive** — la première page de chaque PDF s'affiche, un aperçu de l'en-tête suit la souris en temps réel
- **Positionnement au clic** — cliquez pour placer l'en-tête, ou choisissez parmi 9 presets (coin, centre, milieu...)
- **Texte flexible** — nom du fichier seul, avec préfixe, avec suffixe, texte entièrement libre, ou combinaison avec la date
- **Typographie complète** — polices PDF intégrées (Courier, Helvetica, Times) et polices système, taille, gras, italique, souligné, espacement
- **Rotation** — texte inclinable librement
- **Cadre** — bordure autour du texte, style, couleur, épaisseur, opacité
- **Fond** — rectangle de fond derrière le texte, couleur, opacité
- **Application sélective** — toutes les pages ou première page uniquement
- **Position mémorisée** — la position et les réglages sont automatiquement réutilisés pour le fichier suivant
- **Fichiers originaux préservés** — les PDFs modifiés sont enregistrés dans un nouveau dossier `<dossier_source>_avec_entete/`
- **Mise à jour automatique** — le script se met à jour silencieusement depuis GitHub au lancement
- **Multi-OS** — Windows 11 et Linux

---

## Installation Windows

1. Télécharge le fichier `PDFHeaderTool-vX.Y.Z.zip` depuis les [Releases GitHub](../../releases)
2. Dézippe le dossier où tu veux
3. Double-clique sur `lancer.bat`

Aucun Python requis — tout est inclus dans le zip.

---

## Installation Linux

**Prérequis système** (exemple sur Arch / EndeavourOS) :
```bash
sudo pacman -S tk
```

Sur Ubuntu/Debian :
```bash
sudo apt install python3-tk
```

Ensuite, au choix :

**Option A — Installation directe :**
```bash
pip install pymupdf customtkinter pillow
python3 pdf_header.py
```

**Option B — venv (recommandé) :**
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install pymupdf customtkinter pillow
python3 pdf_header.py
```

**Option C — uv :**
```bash
uv run --with pymupdf,customtkinter,pillow pdf_header.py
```

---

## Utilisation

1. Lance l'outil (`lancer.bat` sous Windows, `python3 pdf_header.py` sous Linux)
2. Sélectionne un dossier ou des fichiers PDF via les boutons en haut
3. Pour chaque PDF :
   - Configure le texte, la police et le style dans le panneau gauche
   - Clique sur la prévisualisation pour positionner l'en-tête, ou utilise les presets de position
   - Clique **Appliquer** pour valider, ou **Passer** pour ignorer ce fichier
4. Les PDFs modifiés sont enregistrés dans `<dossier>_avec_entete/`

---

## Options de texte

| Mode | Exemple de résultat |
|------|-------------------|
| Nom du fichier | `rapport_2024` |
| Préfixe + nom | `CONFIDENTIEL – rapport_2024` |
| Nom + suffixe | `rapport_2024 – DRAFT` |
| Texte personnalisé | `Société XYZ` |
| Avec date | `rapport_2024 – 21/02/2026` |

---

## Structure du projet

```
pdf-header-tool/
├── pdf_header.py     # Script principal
├── build_dist.py     # Script de build distribution Windows (dev uniquement)
├── lancer.bat        # Point d'entrée Windows portable (double-clic)
├── setup.bat         # Réinstallation manuelle des dépendances (secours)
├── version.txt       # Numéro de version courant
├── CLAUDE.md         # Contexte technique pour Claude Code (développement)
└── README.md         # Ce fichier
```

---

## Build de la distribution Windows

Requiert Python 3 et une connexion internet (télécharge Python Embeddable depuis python.org) :

```bash
python3 build_dist.py
```

Le zip généré dans `dist/` est autonome et prêt à distribuer.

---

## Publier une nouvelle version

```bash
# 1. Mettre à jour VERSION dans pdf_header.py et version.txt
# 2. Commit + tag
git add pdf_header.py version.txt
git commit -m "feat: description"
git tag vX.Y.Z
git push origin main && git push origin vX.Y.Z
```

---

## Dépendances

- [PyMuPDF](https://pymupdf.readthedocs.io/) — rendu et édition PDF
- [Pillow](https://pillow.readthedocs.io/) — traitement d'image pour la prévisualisation
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — interface graphique moderne
- tkinter — canvas de prévisualisation (inclus avec Python, paquet système sous Linux)

---

## Licence

MIT
