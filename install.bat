@echo off
setlocal EnableDelayedExpansion
title PDF Header Tool — Installation
color 0A
cls

echo ============================================================
echo   PDF Header Tool — Installation
echo ============================================================
echo.

:: ── Verifier si Python est installe ──────────────────────────
echo   Verification de Python...
python --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    echo   [OK] !PY_VER! detecte
    goto :run_installer
)

:: Python introuvable — tentative via py launcher
py --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%v in ('py --version 2^>^&1') do set PY_VER=%%v
    echo   [OK] !PY_VER! detecte via py launcher
    set PYTHON_CMD=py
    goto :run_installer
)

:: ── Python absent : telechargement + installation ─────────────
echo.
echo   Python n'est pas installe sur ce systeme.
echo.
echo   Deux options :
echo     1. Installation automatique (telechargement ~25 Mo)
echo     2. Ouvrir python.org pour telecharger manuellement
echo.
set /p CHOICE="   Votre choix (1 ou 2) : "

if "%CHOICE%"=="2" (
    echo.
    echo   Ouverture de https://www.python.org/downloads/
    start https://www.python.org/downloads/
    echo.
    echo   Apres installation, relancez install.bat
    pause
    exit /b 0
)

:: Telechargement silencieux de Python 3.12
echo.
echo   Telechargement de Python 3.12...
set PY_INSTALLER=%TEMP%\python_installer.exe
set PY_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe

powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing"

if not exist "%PY_INSTALLER%" (
    echo   [ERREUR] Telechargement echoue. Verifiez votre connexion.
    echo   Ouvrez manuellement : https://www.python.org/downloads/
    pause
    exit /b 1
)

echo   Installation de Python (fenetres UAC possibles)...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

:: Rafraichir PATH
call refreshenv >nul 2>&1
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERREUR] Installation Python echouee.
    echo   Redemarrez et relancez install.bat, ou installez Python manuellement.
    pause
    exit /b 1
)
echo   [OK] Python installe avec succes

:: ── Lancer install.py ─────────────────────────────────────────
:run_installer
echo.
echo   Lancement du script d'installation...
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_CMD=python

:: Utiliser py si python n'est pas directement accessible
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=py
)

"%PYTHON_CMD%" "%SCRIPT_DIR%install.py"

if %errorlevel% neq 0 (
    echo.
    echo   [ERREUR] L'installation a echoue.
    pause
    exit /b 1
)

endlocal
exit /b 0
