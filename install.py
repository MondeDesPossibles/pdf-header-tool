# ==============================================================================
# PDF Header Tool — install.py
# Version : 0.0.1
# Build   : build-2026.02.20.07
# Repo    : MondeDesPossibles/pdf-header-tool
# Installation Windows : AppData/Local, venv, raccourcis bureau + menu démarrer
# ==============================================================================

import sys
import os
import shutil
import subprocess
from pathlib import Path

# Nécessite Python 3.8+
if sys.version_info < (3, 8):
    print("Python 3.8 ou supérieur requis.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
INSTALL_DIR  = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PDFHeaderTool"
VENV_DIR     = INSTALL_DIR / ".venv"
VENV_PYTHON  = VENV_DIR / "Scripts" / "python.exe"
SCRIPT_DIR   = Path(__file__).parent.resolve()
APP_NAME     = "PDF Header Tool"
ICON_NAME    = "pdf_header.ico"
INSTALLER_VERSION = "build-2026.02.20.07"

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def step(msg):
    print(f"\n  >  {msg}")

def ok(msg=""):
    print(f"      [OK] {msg}" if msg else "      [OK] OK")

def fail(msg):
    print(f"      [ERROR] {msg}")
    input("\nAppuyez sur Entree pour quitter...")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 1. Copier les fichiers dans AppData\Local\PDFHeaderTool
# ---------------------------------------------------------------------------
def install_files():
    step(f"Copie des fichiers vers {INSTALL_DIR}")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    files_to_copy = ["pdf_header.py", "version.txt"]
    for fname in files_to_copy:
        src = SCRIPT_DIR / fname
        dst = INSTALL_DIR / fname
        if src.exists():
            shutil.copy2(src, dst)
            ok(fname)
        else:
            print(f"      [WARN] {fname} introuvable, ignore")

    # Icône (optionnelle)
    icon_src = SCRIPT_DIR / ICON_NAME
    icon_dst = INSTALL_DIR / ICON_NAME
    if icon_src.exists():
        shutil.copy2(icon_src, icon_dst)
        ok(ICON_NAME)

# ---------------------------------------------------------------------------
# 2. Créer le venv et installer les dépendances
# ---------------------------------------------------------------------------
def setup_venv():
    step("Création de l'environnement virtuel")
    if not VENV_PYTHON.exists():
        import venv
        venv.create(str(VENV_DIR), with_pip=True)
        ok("Venv créé")
    else:
        ok("Venv déjà existant, réutilisation")

    step("Installation des dependances (pymupdf, Pillow, customtkinter)")
    # Mettre pip a jour augmente fortement la fiabilite sur VM fraiches.
    try:
        subprocess.check_call(
            [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "--disable-pip-version-check"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        pass

    pkgs = ["pymupdf", "Pillow", "customtkinter"]
    for pkg in pkgs:
        print(f"      -> {pkg}...", end="", flush=True)
        cmd = [
            str(VENV_PYTHON), "-m", "pip", "install", pkg,
            "--disable-pip-version-check", "--prefer-binary"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(" [OK]")
        else:
            print(f"\n      [ERROR] Impossible d'installer {pkg}")
            if result.stderr:
                print("      pip stderr:")
                for line in result.stderr.strip().splitlines()[-8:]:
                    print(f"        {line}")
            fail("Verifiez la connexion Internet et relancez install.bat")

# ---------------------------------------------------------------------------
# 3. Créer le lancer.bat dans le dossier d'installation
# ---------------------------------------------------------------------------
def create_launcher():
    step("Création du lanceur")
    launcher = INSTALL_DIR / "lancer.bat"
    content = f"""@echo off
"{VENV_PYTHON}" "{INSTALL_DIR / 'pdf_header.py'}" %*
"""
    launcher.write_text(content, encoding="utf-8")
    ok(str(launcher))
    return launcher

# ---------------------------------------------------------------------------
# 4. Créer les raccourcis Windows (.lnk) via PowerShell
# ---------------------------------------------------------------------------
def _create_shortcut(target_bat, shortcut_path, description):
    """Crée un raccourci .lnk via PowerShell (pas de dépendance externe)."""
    icon_path = INSTALL_DIR / ICON_NAME
    icon_line = f'$s.IconLocation = "{icon_path}"' if icon_path.exists() else ""

    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath       = "{target_bat}"
$s.WorkingDirectory = "{INSTALL_DIR}"
$s.Description      = "{description}"
{icon_line}
$s.Save()
"""
    try:
        subprocess.check_call(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", ps_script],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False

def create_shortcuts(launcher_bat):
    step("Création des raccourcis")

    # Bureau
    desktop = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    if not desktop.exists():
        # Chemin localisé via PowerShell
        try:
            result = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetFolderPath('Desktop')"],
                text=True
            ).strip()
            if result:
                desktop = Path(result)
        except Exception:
            pass

    lnk_desktop = desktop / f"{APP_NAME}.lnk"
    if _create_shortcut(str(launcher_bat), str(lnk_desktop), APP_NAME):
        ok(f"Raccourci bureau : {lnk_desktop}")
    else:
        print("      [WARN] Raccourci bureau non cree (PowerShell indisponible ?)")

    # Menu Démarrer
    start_menu = Path(os.environ.get("APPDATA", "")) / \
                 "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu.mkdir(parents=True, exist_ok=True)
    lnk_start = start_menu / f"{APP_NAME}.lnk"
    if _create_shortcut(str(launcher_bat), str(lnk_start), APP_NAME):
        ok(f"Menu Démarrer : {lnk_start}")
    else:
        print("      [WARN] Raccourci menu Demarrer non cree")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print(f"  Installation de {APP_NAME}")
    print(f"  install.py version: {INSTALLER_VERSION}")
    print("=" * 60)

    install_files()
    setup_venv()
    launcher = create_launcher()
    create_shortcuts(launcher)

    print("\n" + "=" * 60)
    print(f"  [OK] Installation terminee !")
    print(f"     Dossier : {INSTALL_DIR}")
    print(f"     Lancez l'application depuis le raccourci sur le bureau")
    print("=" * 60)
    input("\nAppuyez sur Entree pour fermer...")

if __name__ == "__main__":
    main()
