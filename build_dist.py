#!/usr/bin/env python3
# ==============================================================================
# PDF Header Tool — build_dist.py
# Version : 0.4.6
# Build   : build-2026.02.21.03
# Repo    : MondeDesPossibles/pdf-header-tool
# Usage   : python3 build_dist.py [--python-version 3.11.9]
# Dev-only : ne pas inclure dans la distribution finale.
# ==============================================================================
"""
Script de build pour la distribution Windows portable.

Étapes :
  1. Télécharger Python Embeddable Package (amd64) depuis python.org
  2. Extraire dans dist/PDFHeaderTool-vX.Y.Z/python/
  3. Patcher python3XX._pth  : décommenter "import site" + ajouter "../site-packages"
  4. Créer dist/PDFHeaderTool-vX.Y.Z/site-packages/ (vide)
  5. Copier les fichiers du projet (pdf_header.py, version.txt, lancer.bat,
     setup.bat, get-pip.py)
  6. Créer dist/PDFHeaderTool-vX.Y.Z.zip

Prérequis :
  - get-pip.py doit être présent à la racine du repo
    (télécharger depuis https://bootstrap.pypa.io/get-pip.py)
  - Connexion internet pour télécharger Python Embedded
"""

import argparse
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL_TEMPLATE = (
    "https://www.python.org/ftp/python/{ver}/python-{ver}-embed-amd64.zip"
)

SCRIPT_DIR = Path(__file__).parent
DIST_BASE  = SCRIPT_DIR / "dist"

# Fichiers du projet à copier dans la distribution
PROJECT_FILES = [
    "pdf_header.py",
    "version.txt",
    "lancer.bat",
    "setup.bat",
    "get-pip.py",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _log(msg: str) -> None:
    print(f"  {msg}")


def _download(url: str, dest: Path) -> None:
    """Télécharge url vers dest avec barre de progression."""
    print(f"  Téléchargement : {url}")

    def _reporthook(count, block_size, total_size):
        if total_size > 0:
            pct = min(100, int(count * block_size * 100 / total_size))
            bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
            print(f"\r    [{bar}] {pct}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
    print()  # newline après la barre


def _patch_pth(python_dir: Path) -> None:
    """Patche python3XX._pth pour activer site et ../site-packages."""
    pth_files = sorted(python_dir.glob("python3*._pth"))
    if not pth_files:
        print("  AVERTISSEMENT : aucun fichier ._pth trouvé dans python/", file=sys.stderr)
        return

    pth_file = pth_files[0]
    content  = pth_file.read_text(encoding="utf-8")

    # Décommenter "import site"
    if "#import site" in content:
        content = content.replace("#import site", "import site")
        _log(f"Patché : '#import site' → 'import site' dans {pth_file.name}")
    elif "import site" not in content:
        content += "\nimport site\n"
        _log(f"Ajouté : 'import site' dans {pth_file.name}")

    # Ajouter ../site-packages si absent
    if "../site-packages" not in content:
        content += "../site-packages\n"
        _log(f"Ajouté : '../site-packages' dans {pth_file.name}")

    pth_file.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Build principal
# ---------------------------------------------------------------------------
def build(python_version: str) -> None:
    # Lire la version du projet depuis version.txt
    version_file = SCRIPT_DIR / "version.txt"
    if version_file.exists():
        project_version = version_file.read_text(encoding="utf-8").strip()
    else:
        project_version = "0.4.6"

    dist_name = f"PDFHeaderTool-v{project_version}"
    dist_dir  = DIST_BASE / dist_name
    zip_path  = DIST_BASE / f"{dist_name}.zip"

    print(f"\n{'=' * 60}")
    print(f"  Build distribution : {dist_name}")
    print(f"  Python Embedded    : {python_version}")
    print(f"  Sortie             : {zip_path}")
    print(f"{'=' * 60}\n")

    # 1. Nettoyage / création du dossier de distribution
    if dist_dir.exists():
        _log(f"Suppression dossier existant : {dist_dir.name}/")
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)
    _log(f"Dossier créé : {dist_dir}")

    # 2. Téléchargement Python Embedded (cache local dans dist/)
    embed_url      = PYTHON_EMBED_URL_TEMPLATE.format(ver=python_version)
    embed_zip_name = f"python-{python_version}-embed-amd64.zip"
    embed_zip_path = DIST_BASE / embed_zip_name

    DIST_BASE.mkdir(parents=True, exist_ok=True)

    if embed_zip_path.exists():
        _log(f"Python Embedded déjà en cache : {embed_zip_name}")
    else:
        _download(embed_url, embed_zip_path)
        _log(f"Téléchargement terminé : {embed_zip_name} ({embed_zip_path.stat().st_size // 1024} Ko)")

    # 3. Extraction dans dist/PDFHeaderTool-vX.Y.Z/python/
    python_dir = dist_dir / "python"
    _log(f"Extraction dans python/...")
    with zipfile.ZipFile(embed_zip_path, "r") as zf:
        zf.extractall(python_dir)
    _log(f"Extraction terminée ({len(list(python_dir.iterdir()))} fichiers)")

    # 4. Patch python3XX._pth
    _patch_pth(python_dir)

    # 5. Création du dossier site-packages (vide)
    site_pkg_dir = dist_dir / "site-packages"
    site_pkg_dir.mkdir()
    _log("Dossier site-packages/ créé")

    # 6. Copie des fichiers du projet
    missing = []
    for fname in PROJECT_FILES:
        src = SCRIPT_DIR / fname
        if src.exists():
            shutil.copy2(src, dist_dir / fname)
            _log(f"Copié : {fname}")
        else:
            missing.append(fname)
            print(f"  AVERTISSEMENT : {fname} introuvable — ignoré", file=sys.stderr)

    if missing:
        print(f"\n  Fichiers manquants : {', '.join(missing)}", file=sys.stderr)
        print("  La distribution peut être incomplète.\n", file=sys.stderr)

    # 7. Création du zip final
    _log(f"Création du zip : {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in sorted(dist_dir.rglob("*")):
            if file.is_file():
                arcname = Path(dist_name) / file.relative_to(dist_dir)
                zf.write(file, arcname)

    zip_size_mb = zip_path.stat().st_size / 1024 / 1024
    _log(f"Zip créé : {zip_path.name} ({zip_size_mb:.1f} Mo)")

    print(f"\n{'=' * 60}")
    print(f"  Distribution prête : {zip_path}")
    print(f"  Taille             : {zip_size_mb:.1f} Mo")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build distribution Windows portable PDF Header Tool"
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help=f"Version Python Embedded à utiliser (défaut : {DEFAULT_PYTHON_VERSION})",
    )
    args = parser.parse_args()
    build(args.python_version)
