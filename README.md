# PDF Header Tool

Outil GUI Python pour insérer automatiquement le nom d'un fichier en en-tête de ses pages PDF.

---

## Fonctionnalités

- **Prévisualisation interactive** — la première page de chaque PDF s'affiche, des croix de guidage suivent la souris, un clic positionne l'en-tête
- **Position mémorisée** — la position choisie est automatiquement réutilisée pour le fichier suivant
- **Texte personnalisable** — nom du fichier seul, avec préfixe, avec suffixe, ou texte entièrement libre
- **Style configurable** — couleur (sélecteur graphique) et taille en points
- **Application sélective** — toutes les pages ou première page uniquement
- **Fichiers originaux préservés** — les PDFs modifiés sont enregistrés dans un nouveau dossier `<dossier_source>_avec_entete/`
- **Mise à jour automatique** — le script se met à jour silencieusement depuis GitHub au lancement
- **Multi-OS** — Windows 11 et Linux

---

## Installation (Windows)

1. Télécharge les fichiers `install.bat`, `install.py` et `pdf_header.py`
2. Place-les dans le même dossier
3. Double-clique sur `install.bat`

Le script vérifie si Python est installé (et le télécharge si nécessaire), installe les dépendances, puis crée un raccourci sur le bureau et dans le menu Démarrer.

> **Python requis** : 3.8 ou supérieur. Téléchargement sur [python.org](https://www.python.org/downloads/).

---

## Utilisation (Linux)

```bash
# Premier lancement (crée le venv et installe les dépendances automatiquement)
python3 pdf_header.py

# Avec un dossier en argument
python3 pdf_header.py /chemin/vers/mes/pdfs/
```

---

## Utilisation

1. Lance l'outil via le raccourci bureau (Windows) ou en ligne de commande (Linux)
2. Sélectionne un dossier contenant des PDFs
3. Pour chaque fichier :
   - Configure le texte, la couleur et la taille dans le panneau gauche
   - Clique sur la prévisualisation pour positionner l'en-tête
   - Clique **Appliquer** pour valider, ou **Passer** pour ignorer ce fichier
4. Les PDFs modifiés sont enregistrés dans `<dossier>_avec_entete/`

---

## Options de texte

| Mode | Exemple de résultat |
|------|-------------------|
| Nom du fichier | `rapport_2024.pdf` |
| Préfixe + nom | `CONFIDENTIEL – rapport_2024.pdf` |
| Nom + suffixe | `rapport_2024.pdf – DRAFT` |
| Texte personnalisé | `Société XYZ` |

---

## Structure du projet

```
pdf-header-tool/
├── pdf_header.py   # Script principal
├── install.py      # Installateur Windows
├── install.bat     # Vérification Python + lancement installateur
├── version.txt     # Version courante
├── CLAUDE.md       # Contexte pour Claude Code (développement)
└── README.md       # Ce fichier
```

---

## Développement

Voir `CLAUDE.md` pour le contexte technique complet destiné à Claude Code.

Pour publier une nouvelle version :
```bash
# 1. Mettre à jour VERSION dans pdf_header.py et version.txt
# 2. Commit + tag
git add .
git commit -m "feat: description de la modification"
git tag v1.0.1
git push && git push origin v1.0.1
```

---

## Dépendances

- [PyMuPDF](https://pymupdf.readthedocs.io/) — rendu et édition PDF
- [Pillow](https://pillow.readthedocs.io/) — traitement d'image pour la prévisualisation
- tkinter — interface graphique (inclus dans Python)

---

## Licence

MIT
