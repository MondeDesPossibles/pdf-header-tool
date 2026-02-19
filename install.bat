@echo off
setlocal EnableDelayedExpansion
title PDF Header Tool — Installation
color 0A
cls

echo ============================================================
echo   PDF Header Tool — Installation
echo ============================================================
echo.

:: ── 1. Chercher Python (3 passes) ─────────────────────────────
echo   Verification de Python...
set "PYTHON_CMD="
set "PY_VER=inconnu"

:: Passe 1 : commande 'python'
python --version >nul 2>&1
if %errorlevel% EQU 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python"
    echo   [OK] Python !PY_VER! detecte
    goto :check_version
)

:: Passe 2 : py launcher (Windows Python Launcher)
py --version >nul 2>&1
if %errorlevel% EQU 0 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=py"
    echo   [OK] Python !PY_VER! detecte via py launcher
    goto :check_version
)

:: Passe 3 : emplacements standards (PATH pas encore mis a jour)
for %%d in (
    "%LOCALAPPDATA%\Programs\Python\Python314"
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%LOCALAPPDATA%\Programs\Python\Python310"
    "%LOCALAPPDATA%\Programs\Python\Python39"
    "%LOCALAPPDATA%\Programs\Python\Python38"
    "%ProgramFiles%\Python314"
    "%ProgramFiles%\Python313"
    "%ProgramFiles%\Python312"
) do (
    if exist "%%~d\python.exe" (
        for /f "tokens=2" %%v in ('"%%~d\python.exe" --version 2^>^&1') do set "PY_VER=%%v"
        set "PYTHON_CMD=%%~d\python.exe"
        echo   [OK] Python !PY_VER! trouve dans %%~d
        goto :check_version
    )
)

goto :install_python

:: ── 2. Verifier la version minimale (3.8+) ───────────────────
:check_version
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! LSS 3 goto :version_too_old
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 8 goto :version_too_old
goto :run_installer

:version_too_old
echo.
echo   [ATTENTION] Python !PY_VER! est trop ancien (3.8 minimum requis).
echo.
set /p "UPGRADE=   Mettre a jour Python automatiquement ? (O/N) : "
if /i "!UPGRADE!"=="O" goto :install_python
echo   Attention : des erreurs sont possibles avec cette version.
goto :run_installer

:: ── 3. Installer Python automatiquement ──────────────────────
:install_python
echo.
echo   Python n'est pas detecte sur ce systeme.
echo.
echo     1. Installation automatique (telechargement ~27 Mo)
echo     2. Ouvrir python.org pour telecharger manuellement
echo.
set /p "CHOICE=   Votre choix (1 ou 2) : "

if "!CHOICE!"=="2" goto :manual_install
if not "!CHOICE!"=="1" goto :manual_install
goto :auto_install

:manual_install
echo.
start https://www.python.org/downloads/
echo   Apres installation de Python, relancez install.bat
pause
exit /b 0

:auto_install
:: Detecter l'architecture processeur
set "PY_ARCH=amd64"
if /i "!PROCESSOR_ARCHITECTURE!"=="ARM64" set "PY_ARCH=arm64"
:: x86 pur (rare) : installateur sans suffixe
if /i "!PROCESSOR_ARCHITECTURE!"=="x86" if "!PROCESSOR_ARCHITEW6432!"=="" set "PY_ARCH="

:: Recuperer la derniere version stable depuis python.org
echo.
echo   Recherche de la derniere version stable de Python sur python.org...
set "PY_VERSION=3.13.1"
set "PY_VER_TMP=%TEMP%\pdf_header_py_version.txt"
if exist "%PY_VER_TMP%" del "%PY_VER_TMP%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; try { $r=Invoke-WebRequest -Uri 'https://www.python.org/downloads/' -UseBasicParsing -TimeoutSec 15; $m=[regex]::Match($r.Content,'Download Python (\d+\.\d+\.\d+)'); if($m.Success){ $m.Groups[1].Value | Out-File '%PY_VER_TMP%' -Encoding ascii -NoNewline } } catch {}"

if exist "%PY_VER_TMP%" (
    set /p PY_VERSION_RAW=<"%PY_VER_TMP%"
    del "%PY_VER_TMP%" >nul 2>&1
    if not "!PY_VERSION_RAW!"=="" set "PY_VERSION=!PY_VERSION_RAW!"
)
echo   Version : Python !PY_VERSION!
echo   Architecture : !PY_ARCH!

:: Construire l'URL de l'installateur
set "PY_INSTALLER=%TEMP%\python-!PY_VERSION!-installer.exe"
if "!PY_ARCH!"=="" (
    set "PY_URL=https://www.python.org/ftp/python/!PY_VERSION!/python-!PY_VERSION!.exe"
) else (
    set "PY_URL=https://www.python.org/ftp/python/!PY_VERSION!/python-!PY_VERSION!-!PY_ARCH!.exe"
)

echo.
echo   Telechargement en cours (patientez)...

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '!PY_URL!' -OutFile '!PY_INSTALLER!' -UseBasicParsing; exit 0 } catch { Write-Host '  Erreur reseau : '$_.Exception.Message; exit 1 }"

if not exist "!PY_INSTALLER!" (
    echo.
    echo   [ERREUR] Telechargement echoue. Verifiez votre connexion internet.
    echo   Installez Python manuellement : https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Verifier que le fichier est complet (> 5 Mo)
for %%f in ("!PY_INSTALLER!") do set "INSTALLER_SIZE=%%~zf"
if !INSTALLER_SIZE! LSS 5000000 (
    echo.
    echo   [ERREUR] Fichier telecharge invalide (!INSTALLER_SIZE! octets, attendu ^>5 Mo).
    echo   Verifiez votre connexion et relancez install.bat
    del "!PY_INSTALLER!" >nul 2>&1
    pause
    exit /b 1
)
echo   [OK] Fichier telecharge (!INSTALLER_SIZE! octets)

echo.
echo   Installation de Python !PY_VERSION! en cours...
echo   (Une fenetre de controle du compte peut apparaitre - cliquez Oui)

"!PY_INSTALLER!" /passive InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
set "PY_INSTALL_CODE=!errorlevel!"

del "!PY_INSTALLER!" >nul 2>&1

if !PY_INSTALL_CODE! EQU 1602 (
    echo.
    echo   [ERREUR] Installation annulee par l'utilisateur.
    pause
    exit /b 1
)
if !PY_INSTALL_CODE! NEQ 0 (
    echo.
    echo   [ERREUR] Installation de Python echouee (code !PY_INSTALL_CODE!).
    echo   Essayez d'installer Python manuellement : https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   [OK] Python !PY_VERSION! installe avec succes

:: Mettre a jour le PATH de la session via PowerShell
:: (remplace 'refreshenv' de Chocolatey qui n'est pas disponible par defaut)
echo   Mise a jour du PATH...
set "PY_PATHS_TMP=%TEMP%\pdf_header_py_paths.txt"
if exist "%PY_PATHS_TMP%" del "%PY_PATHS_TMP%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $p=@(); if(Test-Path '%LOCALAPPDATA%\Programs\Python'){ Get-ChildItem '%LOCALAPPDATA%\Programs\Python' | ForEach-Object { $p+=$_.FullName; $p+=($_.FullName+'\Scripts') } }; ($p -join ';') | Out-File '%PY_PATHS_TMP%' -Encoding ascii -NoNewline"

if exist "%PY_PATHS_TMP%" (
    set /p "PY_NEW_PATHS="<"%PY_PATHS_TMP%"
    del "%PY_PATHS_TMP%" >nul 2>&1
    if defined PY_NEW_PATHS set "PATH=!PATH!;!PY_NEW_PATHS!"
)

:: Re-verifier Python apres installation (3 passes)
set "PYTHON_CMD="
python --version >nul 2>&1
if %errorlevel% EQU 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=python"
    echo   [OK] Python !PY_VER! accessible
    goto :run_installer
)

py --version >nul 2>&1
if %errorlevel% EQU 0 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do set "PY_VER=%%v"
    set "PYTHON_CMD=py"
    echo   [OK] Python !PY_VER! accessible via py launcher
    goto :run_installer
)

for %%d in (
    "%LOCALAPPDATA%\Programs\Python\Python314"
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%LOCALAPPDATA%\Programs\Python\Python310"
) do (
    if exist "%%~d\python.exe" (
        set "PYTHON_CMD=%%~d\python.exe"
        echo   [OK] Python trouve dans %%~d
        goto :run_installer
    )
)

echo.
echo   [INFO] Python est installe mais pas encore accessible dans cette session.
echo   Cela arrive parfois apres une premiere installation sous Windows 11.
echo.
echo   Fermez cette fenetre et relancez install.bat
echo.
pause
exit /b 0

:: ── 4. Lancer install.py ──────────────────────────────────────
:run_installer
echo.
echo   Lancement du script d'installation...
echo.

if not defined PYTHON_CMD (
    echo   [ERREUR] Aucun interpreteur Python trouve.
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
"!PYTHON_CMD!" "!SCRIPT_DIR!install.py"

if !errorlevel! NEQ 0 (
    echo.
    echo   [ERREUR] L'installation a echoue (code !errorlevel!).
    echo   Consultez les messages ci-dessus pour plus de details.
    pause
    exit /b 1
)

endlocal
exit /b 0
