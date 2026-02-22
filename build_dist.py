#!/usr/bin/env python3
# ==============================================================================
# PDF Header Tool — build_dist.py
# Version : 0.4.6
# Build   : build-2026.02.21.07
# Repo    : MondeDesPossibles/pdf-header-tool
# Usage   : python3 build_dist.py [--python-version 3.11.9]
# Dev-only : ne pas inclure dans la distribution finale.
# ==============================================================================
"""
Script de build pour la distribution Windows portable (bundle complet).

etapes :
  1. Telecharger Python Embeddable Package (amd64) depuis python.org
  2. Source Tcl/Tk (deux modes, par priorite) :
     a. Dossier local tcltk/  — si present, utilise en priorite (recommande)
     b. Python NuGet package  — telecharge automatiquement si tcltk/ absent
  3. Extraire Python Embedded dans dist/PDFHeaderTool-vX.Y.Z/python/
  4. Copier les DLLs Tcl/Tk + scripts → python/
  5. Patcher python3XX._pth : decommenter "import site" + ajouter "../site-packages"
  6. Installer les dependances (pymupdf, pillow, customtkinter) dans site-packages/
     via pip cross-compilation Windows (fonctionne depuis Linux)
  7. Copier les fichiers du projet (pdf_header.py, version.txt, lancer.bat)
  8. Creer dist/PDFHeaderTool-vX.Y.Z.zip

Prerequis :
  - pip installe sur la machine de build (pip3)
  - Connexion internet si tcltk/ absent (telecharge Python Embedded, NuGet, wheels)
  - OU dossier tcltk/ present (pour Tcl/Tk sans internet)

Dossier tcltk/ (source locale recommandee) :
  Copier depuis une installation Python 3.11.x Windows (64-bit) :
    tcltk/tcl86t.dll      ← Python311/tcl86t.dll
    tcltk/tk86t.dll       ← Python311/tk86t.dll
    tcltk/tcl/            ← Python311/tcl/  (contient tcl8.6/ et tk8.6/)
  Ajouter tcltk/ au .gitignore (binaires lourds, non versionnes).

Resultat :
  - Zip entièrement auto-contenu : aucun internet requis sur la machine utilisateur
  - Deziper + double-clic lancer.bat = l'app se lance directement
"""

import argparse
import hashlib
import json
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
BUILD_ID = "build-2026.02.22.01"

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

SCRIPT_DIR     = Path(__file__).parent
DIST_BASE      = SCRIPT_DIR / "dist"
TCLTK_LOCAL    = SCRIPT_DIR / "tcltk"   # dossier local (non versionne, voir .gitignore)

# Fichiers du projet à copier dans la distribution
PROJECT_FILES = [
    "pdf_header.py",
    "version.txt",
    "lancer.bat",
]

# Fichiers sources inclus dans app-patch.zip (mise à jour légère)
# À partir de v0.4.7 : ajouter les fichiers app/*.py ici
PATCH_FILES = [
    "pdf_header.py",
    "version.txt",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _log(msg: str) -> None:
    print(f"  {msg}")


def _find_pip() -> list:
    """Retourne la commande pip utilisable sur cette machine.

    Essaie dans l'ordre :
      1. python3 -m pip  (pip dans le module Python courant)
      2. pip3            (commande système)
      3. pip             (commande système generique)
    """
    for candidate in [
        [sys.executable, "-m", "pip"],
        ["pip3"],
        ["pip"],
    ]:
        try:
            result = subprocess.run(
                candidate + ["--version"],
                capture_output=True,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, OSError):
            continue
    print("  ERREUR : pip introuvable. Installez-le avec : sudo pacman -S python-pip", file=sys.stderr)
    sys.exit(1)


def _download(url: str, dest: Path) -> None:
    """Telecharge url vers dest avec barre de progression."""
    print(f"  Telechargement : {url}")

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
        print("  AVERTISSEMENT : aucun fichier ._pth trouve dans python/", file=sys.stderr)
        return

    pth_file = pth_files[0]
    content  = pth_file.read_text(encoding="utf-8")

    if "#import site" in content:
        content = content.replace("#import site", "import site")
        _log(f"Patche : '#import site' → 'import site' dans {pth_file.name}")
    elif "import site" not in content:
        content += "\nimport site\n"
        _log(f"Ajoute : 'import site' dans {pth_file.name}")

    if "../site-packages" not in content:
        content += "../site-packages\n"
        _log(f"Ajoute : '../site-packages' dans {pth_file.name}")

    pth_file.write_text(content, encoding="utf-8")


def _copy_tcltk_local(tcltk_dir: Path, python_dir: Path) -> None:
    """Copie les DLLs, le module Python tkinter et les scripts Tcl/Tk.

    Structure attendue dans tcltk/ (issue d'une install Windows Python 3.11.x) :
      tcltk/_tkinter.pyd    ← DLLs/_tkinter.pyd      → python/_tkinter.pyd
      tcltk/tcl86t.dll      ← tcl86t.dll             → python/tcl86t.dll
      tcltk/tk86t.dll       ← tk86t.dll              → python/tk86t.dll
      tcltk/tkinter/        ← Lib/tkinter/           → python/tkinter/
      tcltk/tcl/            ← tcl/                   → python/tcl/  (tcl8.6/ ET tk8.6/ côte à côte)

    Notes :
      - _tkinter.pyd et tkinter/ sont ABSENTS du Python Embedded officiel
      - Les deux doivent être copies depuis une installation Windows standard
      - tkinter/ va dans python/ car '.' est dans sys.path (via ._pth)
      - tcl/ doit être copie EN ENTIER : _tkinter.pyd cherche TK_LIBRARY dans
        python/tcl/tk8.6/ (structure du full install Windows, pas du NuGet)
    """
    _log(f"Copie Tcl/Tk depuis le dossier local : {tcltk_dir.name}/")

    for dll in ["_tkinter.pyd", "tcl86t.dll", "tk86t.dll"]:
        src = tcltk_dir / dll
        if not src.exists():
            print(f"  AVERTISSEMENT : {dll} introuvable dans {tcltk_dir}", file=sys.stderr)
            if dll == "_tkinter.pyd":
                print(
                    "    → Copiez DLLs\\_tkinter.pyd depuis votre install Python Windows",
                    file=sys.stderr,
                )
            continue
        shutil.copy2(src, python_dir / dll)
        _log(f"  Copie : {dll} ({src.stat().st_size // 1024} Ko)")

    # module Python tkinter : tcltk/tkinter/ → python/tkinter/
    # (absent de python311.zip dans l'Embedded — doit être fourni separement)
    tkinter_src = tcltk_dir / "tkinter"
    tkinter_dst = python_dir / "tkinter"
    if tkinter_src.exists():
        shutil.copytree(tkinter_src, tkinter_dst)
        count = sum(1 for f in tkinter_dst.rglob("*") if f.is_file())
        _log(f"  Copie : tkinter/ ({count} fichiers)")
    else:
        print(f"  AVERTISSEMENT : tkinter/ introuvable dans {tcltk_dir}", file=sys.stderr)
        print("    → Copiez Lib\\tkinter\\ depuis votre install Python Windows", file=sys.stderr)

    # Scripts Tcl/Tk : copie du dossier tcl/ complet → python/tcl/
    # _tkinter.pyd (issu d'une install Windows) cherche TK_LIBRARY dans python/tcl/tk8.6/
    # → tcl8.6/ et tk8.6/ doivent être côte à côte sous python/tcl/ (structure Windows)
    tcl_src = tcltk_dir / "tcl"
    tcl_dst = python_dir / "tcl"
    if tcl_src.exists():
        shutil.copytree(tcl_src, tcl_dst)
        count = sum(1 for f in tcl_dst.rglob("*") if f.is_file())
        _log(f"  Copie : tcl/ complet ({count} fichiers) → python/tcl/")
    else:
        print(f"  AVERTISSEMENT : tcl/ introuvable dans {tcltk_dir}", file=sys.stderr)


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
                _log(f"  Copie : {Path(tcl_path).name} ({len(data) // 1024} Ko)")
            else:
                print(f"  AVERTISSEMENT : {tcl_path} non trouve dans le NuGet", file=sys.stderr)

        # Copier les dossiers tcl/ et tk/
        for tcl_dir in TCLK_DIRS:
            dir_name = tcl_dir.split("/")[-1]  # "tcl" ou "tk"
            prefix_candidates = [p for p in names if p.startswith(tcl_dir + "/")
                                  or p.lower().startswith("tools/" + dir_name + "/")]
            if not prefix_candidates:
                print(f"  AVERTISSEMENT : dossier {tcl_dir}/ non trouve dans le NuGet", file=sys.stderr)
                continue

            # Determiner le prefixe reel dans le zip
            prefix = prefix_candidates[0].split(dir_name + "/")[0] + dir_name + "/"
            count = 0
            for member in names:
                if member.startswith(prefix) and not member.endswith("/"):
                    rel = member[len(prefix):]
                    dest = python_dir / dir_name / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(member))
                    count += 1
            _log(f"  Copie : {dir_name}/ ({count} fichiers)")


# ---------------------------------------------------------------------------
# Build principal
# ---------------------------------------------------------------------------
def build(python_version: str, full_reinstall: bool = False) -> None:
    # Lire la version du projet depuis version.txt
    version_file = SCRIPT_DIR / "version.txt"
    if version_file.exists():
        project_version = version_file.read_text(encoding="utf-8").strip()
    else:
        project_version = "0.4.6"

    dist_name = f"PDFHeaderTool-v{project_version}-{BUILD_ID}"
    dist_dir  = DIST_BASE / dist_name
    zip_path  = DIST_BASE / f"{dist_name}.zip"

    print(f"\n{'=' * 60}")
    print(f"  Build distribution : {dist_name}")
    print(f"  Python Embedded    : {python_version}")
    print(f"  Mode               : bundle complet (offline)")
    print(f"  Sortie             : {zip_path}")
    print(f"{'=' * 60}\n")

    DIST_BASE.mkdir(parents=True, exist_ok=True)

    # 1. Nettoyage / creation du dossier de distribution
    if dist_dir.exists():
        _log(f"Suppression dossier existant : {dist_dir.name}/")
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 2. Telechargement Python Embedded (cache local dans dist/)
    embed_url      = PYTHON_EMBED_URL_TEMPLATE.format(ver=python_version)
    embed_zip_name = f"python-{python_version}-embed-amd64.zip"
    embed_zip_path = DIST_BASE / embed_zip_name

    if embed_zip_path.exists():
        _log(f"Python Embedded dejà en cache : {embed_zip_name}")
    else:
        _download(embed_url, embed_zip_path)
        _log(f"Termine : {embed_zip_name} ({embed_zip_path.stat().st_size // 1024} Ko)")

    # 3. Source Tcl/Tk : dossier local tcltk/ en priorite, NuGet en fallback
    use_local_tcltk = TCLTK_LOCAL.exists() and (TCLTK_LOCAL / "tcl86t.dll").exists()

    nuget_zip_path = None
    if not use_local_tcltk:
        nuget_url      = PYTHON_NUGET_URL_TEMPLATE.format(ver=python_version)
        nuget_zip_name = f"python-{python_version}-nuget.nupkg"
        nuget_zip_path = DIST_BASE / nuget_zip_name

        if nuget_zip_path.exists():
            _log(f"Python NuGet dejà en cache : {nuget_zip_name}")
        else:
            _log("Dossier tcltk/ absent — telechargement NuGet (fallback)...")
            _download(nuget_url, nuget_zip_path)
            _log(f"Termine : {nuget_zip_name} ({nuget_zip_path.stat().st_size // 1024} Ko)")
    else:
        _log(f"Dossier tcltk/ detecte — NuGet ignore")

    # 4. Extraction Python Embedded → python/
    python_dir = dist_dir / "python"
    _log("Extraction Python Embedded dans python/...")
    with zipfile.ZipFile(embed_zip_path, "r") as zf:
        zf.extractall(python_dir)
    _log(f"Extraction terminee ({len(list(python_dir.iterdir()))} fichiers)")

    # 5. Copie DLLs + scripts Tcl/Tk → python/
    if use_local_tcltk:
        _copy_tcltk_local(TCLTK_LOCAL, python_dir)
    else:
        _extract_tcltk(nuget_zip_path, python_dir)

    # 6. Patch python3XX._pth
    _patch_pth(python_dir)

    # 7. Creation du dossier site-packages
    site_pkg_dir = dist_dir / "site-packages"
    site_pkg_dir.mkdir()
    _log("Dossier site-packages/ cree")

    # 8. Installation des dependances Windows dans site-packages/ (cross-compilation)
    _log("Installation des dependances Windows (cross-compilation depuis Linux)...")
    pip_cmd = _find_pip() + [
        "install",
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
    _log(f"Dependances installees dans site-packages/ ({sum(1 for _ in site_pkg_dir.rglob('*') if _.is_file())} fichiers)")

    # 9. Copie des fichiers du projet
    missing = []
    for fname in PROJECT_FILES:
        src = SCRIPT_DIR / fname
        if src.exists():
            shutil.copy2(src, dist_dir / fname)
            _log(f"Copie : {fname}")
        else:
            missing.append(fname)
            print(f"  AVERTISSEMENT : {fname} introuvable — ignore", file=sys.stderr)

    if missing:
        print(f"\n  Fichiers manquants : {', '.join(missing)}", file=sys.stderr)
        print("  La distribution peut être incomplète.\n", file=sys.stderr)

    # 10. Creation du zip final
    _log(f"Creation du zip : {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in sorted(dist_dir.rglob("*")):
            if file.is_file():
                arcname = Path(dist_name) / file.relative_to(dist_dir)
                zf.write(file, arcname)

    zip_size_mb = zip_path.stat().st_size / 1024 / 1024
    _log(f"Zip cree : {zip_path.name} ({zip_size_mb:.1f} Mo)")

    # 11. Création du patch zip (sources Python uniquement — mise à jour légère)
    patch_zip_name = f"app-patch-v{project_version}.zip"
    patch_zip_path = DIST_BASE / patch_zip_name
    _log(f"Creation du patch zip : {patch_zip_name}...")
    with zipfile.ZipFile(patch_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for fname in PATCH_FILES:
            src = SCRIPT_DIR / fname
            if src.exists():
                zf.write(src, fname)
                _log(f"  + {fname}")
    patch_size_kb = patch_zip_path.stat().st_size / 1024
    patch_sha256 = hashlib.sha256(patch_zip_path.read_bytes()).hexdigest()
    _log(f"Patch zip cree : {patch_zip_name} ({patch_size_kb:.1f} Ko) sha256={patch_sha256[:16]}...")

    # 12. Génération de metadata.json
    metadata = {
        "manifest_version": 1,
        "version": project_version,
        "requires_full_reinstall": full_reinstall,
        "patch_zip": {
            "name": patch_zip_name,
            "sha256": patch_sha256,
            "size": patch_zip_path.stat().st_size,
        },
        "delete": [],
    }
    metadata_path = DIST_BASE / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    _log(f"metadata.json cree : requires_full_reinstall={full_reinstall}")

    print(f"\n{'=' * 60}")
    print(f"  Distribution prête  : {zip_path}")
    print(f"  Taille              : {zip_size_mb:.1f} Mo")
    print(f"  Patch zip           : {patch_zip_path}")
    print(f"  Taille patch        : {patch_size_kb:.1f} Ko")
    print(f"  metadata.json       : {metadata_path}")
    print(f"  Contenu             : Python {python_version} + Tcl/Tk + pymupdf + Pillow + customtkinter")
    print(f"  Utilisation         : deziper + double-clic lancer.bat")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build distribution Windows portable PDF Header Tool (bundle complet)"
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help=f"Version Python Embedded à utiliser (defaut : {DEFAULT_PYTHON_VERSION})",
    )
    parser.add_argument(
        "--full-reinstall",
        action="store_true",
        default=False,
        help="Marquer requires_full_reinstall=true dans metadata.json (si site-packages/ ou python/ changent)",
    )
    args = parser.parse_args()
    build(args.python_version, full_reinstall=args.full_reinstall)
