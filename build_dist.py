#!/usr/bin/env python3
# ==============================================================================
# PDF Header Tool — build_dist.py
# Version : 0.4.6
# Build   : build-2026.02.21.04
# Repo    : MondeDesPossibles/pdf-header-tool
# Usage   : python3 build_dist.py [--python-version 3.11.9]
# Dev-only : ne pas inclure dans la distribution finale.
# ==============================================================================
"""
Script de build pour la distribution Windows portable (bundle complet).

Étapes :
  1. Télécharger Python Embeddable Package (amd64) depuis python.org
  2. Télécharger Python NuGet package (pour les DLLs Tcl/Tk)
  3. Extraire Python Embedded dans dist/PDFHeaderTool-vX.Y.Z/python/
  4. Copier les DLLs Tcl/Tk depuis le NuGet → python/
  5. Patcher python3XX._pth : décommenter "import site" + ajouter "../site-packages"
  6. Installer les dépendances (pymupdf, pillow, customtkinter) dans site-packages/
     via pip cross-compilation Windows (fonctionne depuis Linux)
  7. Copier les fichiers du projet (pdf_header.py, version.txt, lancer.bat)
  8. Créer dist/PDFHeaderTool-vX.Y.Z.zip

Prérequis :
  - pip installé sur la machine de build (pip3)
  - Connexion internet (pour télécharger Python Embedded, NuGet et les wheels)

Résultat :
  - Zip entièrement auto-contenu : aucun internet requis sur la machine utilisateur
  - Déziper + double-clic lancer.bat = l'app se lance directement
"""

import argparse
import shutil
import subprocess
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
# NuGet package Python — contient les DLLs Tcl/Tk (tcl86t.dll, tk86t.dll, tcl/, tk/)
PYTHON_NUGET_URL_TEMPLATE = (
    "https://www.nuget.org/api/v2/package/python/{ver}"
)

# Fichiers Tcl/Tk à extraire du NuGet (chemin interne du nupkg)
TCLK_FILES = [
    "tools/tcl86t.dll",
    "tools/tk86t.dll",
]
TCLK_DIRS = [
    "tools/tcl",
    "tools/tk",
]

SCRIPT_DIR = Path(__file__).parent
DIST_BASE  = SCRIPT_DIR / "dist"

# Fichiers du projet à copier dans la distribution
PROJECT_FILES = [
    "pdf_header.py",
    "version.txt",
    "lancer.bat",
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

    if "#import site" in content:
        content = content.replace("#import site", "import site")
        _log(f"Patché : '#import site' → 'import site' dans {pth_file.name}")
    elif "import site" not in content:
        content += "\nimport site\n"
        _log(f"Ajouté : 'import site' dans {pth_file.name}")

    if "../site-packages" not in content:
        content += "../site-packages\n"
        _log(f"Ajouté : '../site-packages' dans {pth_file.name}")

    pth_file.write_text(content, encoding="utf-8")


def _extract_tcltk(nuget_zip_path: Path, python_dir: Path) -> None:
    """Extrait les DLLs et dossiers Tcl/Tk depuis le NuGet vers python/."""
    _log("Extraction Tcl/Tk depuis NuGet...")
    with zipfile.ZipFile(nuget_zip_path, "r") as zf:
        names = zf.namelist()

        # Copier les DLLs individuelles
        for tcl_path in TCLK_FILES:
            matches = [n for n in names if n.lower() == tcl_path.lower()
                       or n.lower().endswith("/" + tcl_path.split("/")[-1].lower())]
            if matches:
                member = matches[0]
                data = zf.read(member)
                dest = python_dir / Path(tcl_path).name
                dest.write_bytes(data)
                _log(f"  Copié : {Path(tcl_path).name} ({len(data) // 1024} Ko)")
            else:
                print(f"  AVERTISSEMENT : {tcl_path} non trouvé dans le NuGet", file=sys.stderr)

        # Copier les dossiers tcl/ et tk/
        for tcl_dir in TCLK_DIRS:
            dir_name = tcl_dir.split("/")[-1]  # "tcl" ou "tk"
            prefix_candidates = [p for p in names if p.startswith(tcl_dir + "/")
                                  or p.lower().startswith("tools/" + dir_name + "/")]
            if not prefix_candidates:
                print(f"  AVERTISSEMENT : dossier {tcl_dir}/ non trouvé dans le NuGet", file=sys.stderr)
                continue

            # Déterminer le préfixe réel dans le zip
            prefix = prefix_candidates[0].split(dir_name + "/")[0] + dir_name + "/"
            count = 0
            for member in names:
                if member.startswith(prefix) and not member.endswith("/"):
                    rel = member[len(prefix):]
                    dest = python_dir / dir_name / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(member))
                    count += 1
            _log(f"  Copié : {dir_name}/ ({count} fichiers)")


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
    print(f"  Mode               : bundle complet (offline)")
    print(f"  Sortie             : {zip_path}")
    print(f"{'=' * 60}\n")

    DIST_BASE.mkdir(parents=True, exist_ok=True)

    # 1. Nettoyage / création du dossier de distribution
    if dist_dir.exists():
        _log(f"Suppression dossier existant : {dist_dir.name}/")
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 2. Téléchargement Python Embedded (cache local dans dist/)
    embed_url      = PYTHON_EMBED_URL_TEMPLATE.format(ver=python_version)
    embed_zip_name = f"python-{python_version}-embed-amd64.zip"
    embed_zip_path = DIST_BASE / embed_zip_name

    if embed_zip_path.exists():
        _log(f"Python Embedded déjà en cache : {embed_zip_name}")
    else:
        _download(embed_url, embed_zip_path)
        _log(f"Terminé : {embed_zip_name} ({embed_zip_path.stat().st_size // 1024} Ko)")

    # 3. Téléchargement Python NuGet (cache local dans dist/) — pour Tcl/Tk DLLs
    nuget_url      = PYTHON_NUGET_URL_TEMPLATE.format(ver=python_version)
    nuget_zip_name = f"python-{python_version}-nuget.nupkg"
    nuget_zip_path = DIST_BASE / nuget_zip_name

    if nuget_zip_path.exists():
        _log(f"Python NuGet déjà en cache : {nuget_zip_name}")
    else:
        _download(nuget_url, nuget_zip_path)
        _log(f"Terminé : {nuget_zip_name} ({nuget_zip_path.stat().st_size // 1024} Ko)")

    # 4. Extraction Python Embedded → python/
    python_dir = dist_dir / "python"
    _log("Extraction Python Embedded dans python/...")
    with zipfile.ZipFile(embed_zip_path, "r") as zf:
        zf.extractall(python_dir)
    _log(f"Extraction terminée ({len(list(python_dir.iterdir()))} fichiers)")

    # 5. Extraction DLLs Tcl/Tk depuis NuGet → python/
    _extract_tcltk(nuget_zip_path, python_dir)

    # 6. Patch python3XX._pth
    _patch_pth(python_dir)

    # 7. Création du dossier site-packages
    site_pkg_dir = dist_dir / "site-packages"
    site_pkg_dir.mkdir()
    _log("Dossier site-packages/ créé")

    # 8. Installation des dépendances Windows dans site-packages/ (cross-compilation)
    _log("Installation des dépendances Windows (cross-compilation depuis Linux)...")
    pip_cmd = [
        sys.executable, "-m", "pip", "install",
        "--platform", "win_amd64",
        "--python-version", "311",
        "--implementation", "cp",
        "--abi", "cp311",
        "--only-binary=:all:",
        "--target", str(site_pkg_dir),
        "pymupdf", "pillow", "customtkinter",
    ]
    result = subprocess.run(pip_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  ERREUR pip install :\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    _log(f"Dépendances installées dans site-packages/ ({sum(1 for _ in site_pkg_dir.rglob('*') if _.is_file())} fichiers)")

    # 9. Copie des fichiers du projet
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

    # 10. Création du zip final
    _log(f"Création du zip : {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in sorted(dist_dir.rglob("*")):
            if file.is_file():
                arcname = Path(dist_name) / file.relative_to(dist_dir)
                zf.write(file, arcname)

    zip_size_mb = zip_path.stat().st_size / 1024 / 1024
    _log(f"Zip créé : {zip_path.name} ({zip_size_mb:.1f} Mo)")

    print(f"\n{'=' * 60}")
    print(f"  Distribution prête  : {zip_path}")
    print(f"  Taille              : {zip_size_mb:.1f} Mo")
    print(f"  Contenu             : Python {python_version} + Tcl/Tk + pymupdf + Pillow + customtkinter")
    print(f"  Utilisation         : déziper + double-clic lancer.bat")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build distribution Windows portable PDF Header Tool (bundle complet)"
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help=f"Version Python Embedded à utiliser (défaut : {DEFAULT_PYTHON_VERSION})",
    )
    args = parser.parse_args()
    build(args.python_version)
