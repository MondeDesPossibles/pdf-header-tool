@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PDF Header Tool - Installation
color 0A
cls

:: ── Fichier log ────────────────────────────────────────────────
set LOG_FILE=%TEMP%\pdf_header_install.log
echo [%date% %time%] Debut de l'installation > "%LOG_FILE%"
echo [%date% %time%] OS : %OS% >> "%LOG_FILE%"
echo [%date% %time%] Utilisateur : %USERNAME% >> "%LOG_FILE%"
echo [%date% %time%] Repertoire : %~dp0 >> "%LOG_FILE%"

:: ── Macro de logging ───────────────────────────────────────────
:: Usage : call :log "message"
goto :main

:log
echo [%date% %time%] %~1 >> "%LOG_FILE%"
echo   %~1
goto :eof

:log_error
echo [%date% %time%] [ERREUR] %~1 >> "%LOG_FILE%"
echo.
echo   [ERREUR] %~1
echo.
goto :eof

:log_ok
echo [%date% %time%] [OK] %~1 >> "%LOG_FILE%"
echo   [OK] %~1
goto :eof

:: ── Programme principal ────────────────────────────────────────
:main
echo ============================================================
echo   PDF Header Tool - Installation
echo   Log : %LOG_FILE%
echo ============================================================
echo.
call :log "Demarrage install.bat"

:: ── Verification Python ────────────────────────────────────────
call :log "Recherche de Python..."

set PYTHON_CMD=
set PY_VER=

python --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    set PYTHON_CMD=python
    call :log_ok "!PY_VER! detecte via 'python'"
    goto :check_version
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%v in ('py --version 2^>^&1') do set PY_VER=%%v
    set PYTHON_CMD=py
    call :log_ok "!PY_VER! detecte via 'py launcher'"
    goto :check_version
)

:: Chercher Python dans les emplacements courants
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
) do (
    if exist "%%~P" (
        for /f "tokens=*" %%v in ('"%%~P" --version 2^>^&1') do set PY_VER=%%v
        set PYTHON_CMD=%%~P
        call :log_ok "!PY_VER! detecte dans %%~P"
        goto :check_version
    )
)

call :log "Python introuvable sur le systeme"
goto :install_python

:: ── Verification version minimale (3.8+) ──────────────────────
:check_version
call :log "Verification version Python (3.8+ requis)..."
for /f "tokens=2 delims= " %%v in ("!PY_VER!") do set PY_NUM=%%v
for /f "tokens=1,2 delims=." %%a in ("!PY_NUM!") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if !PY_MAJOR! LSS 3 (
    call :log "Version trop ancienne : !PY_VER!"
    goto :install_python
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 8 (
    call :log "Version trop ancienne : !PY_VER!"
    goto :install_python
)
call :log_ok "Version compatible : !PY_VER!"
goto :run_installer

:: ── Python absent ou trop ancien ──────────────────────────────
:install_python
echo.
echo   Python 3.8 ou superieur est requis et n'a pas ete detecte.
echo.
echo   Options :
echo     1. Telecharger et installer Python automatiquement
echo     2. Ouvrir python.org pour telecharger manuellement
echo     3. Annuler
echo.
set /p CHOICE="   Votre choix (1, 2 ou 3) : "
echo [%date% %time%] Choix utilisateur : %CHOICE% >> "%LOG_FILE%"

if "%CHOICE%"=="3" goto :cancelled
if "%CHOICE%"=="2" (
    call :log "Ouverture python.org"
    start https://www.python.org/downloads/
    echo.
    echo   Apres l'installation de Python, relancez install.bat
    echo   Log disponible : %LOG_FILE%
    pause
    exit /b 0
)
if "%CHOICE%"=="1" goto :download_python

echo   Choix invalide.
goto :install_python

:: ── Telechargement Python ──────────────────────────────────────
:download_python
call :log "Debut du telechargement de Python..."

:: Detecter l'architecture
set PY_ARCH=amd64
if "%PROCESSOR_ARCHITECTURE%"=="x86" set PY_ARCH=win32
if "%PROCESSOR_ARCHITEW6432%"=="AMD64" set PY_ARCH=amd64
call :log "Architecture detectee : %PY_ARCH%"

:: URL de la derniere version stable
set PY_VERSION=3.13.1
set PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-%PY_ARCH%.exe
set PY_INSTALLER=%TEMP%\python_%PY_VERSION%_installer.exe

call :log "URL : %PY_URL%"
call :log "Destination : %PY_INSTALLER%"

echo.
echo   Telechargement de Python %PY_VERSION% (%PY_ARCH%)...
echo   (Cette operation peut prendre 1 a 2 minutes selon votre connexion)
echo.

:: Essai 1 : curl.exe (natif Windows 11, plus fiable)
call :log "Tentative 1 : curl.exe"
curl.exe --version >nul 2>&1
if %errorlevel% == 0 (
    curl.exe -L --retry 3 --retry-delay 5 --connect-timeout 30 ^
        --max-time 180 --progress-bar ^
        -o "%PY_INSTALLER%" "%PY_URL%" >> "%LOG_FILE%" 2>&1
    if !errorlevel! == 0 (
        call :log_ok "Telechargement reussi via curl.exe"
        goto :verify_download
    )
    call :log "curl.exe a echoue (code !errorlevel!), tentative suivante..."
)

:: Essai 2 : PowerShell avec WebClient (plus stable que Invoke-WebRequest)
call :log "Tentative 2 : PowerShell WebClient"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$wc = New-Object System.Net.WebClient; $wc.DownloadFile('%PY_URL%', '%PY_INSTALLER%')" ^
  >> "%LOG_FILE%" 2>&1
if %errorlevel% == 0 (
    call :log_ok "Telechargement reussi via PowerShell WebClient"
    goto :verify_download
)
call :log "PowerShell WebClient a echoue (code %errorlevel%), tentative suivante..."

:: Essai 3 : PowerShell Invoke-WebRequest (dernier recours)
call :log "Tentative 3 : PowerShell Invoke-WebRequest"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing" ^
  >> "%LOG_FILE%" 2>&1
if %errorlevel% == 0 (
    call :log_ok "Telechargement reussi via Invoke-WebRequest"
    goto :verify_download
)
call :log "Toutes les methodes de telechargement ont echoue"

:: Echec total du telechargement
call :log_error "Telechargement impossible. Verifiez votre connexion Internet."
echo   Ouvrez manuellement : https://www.python.org/downloads/python-%PY_VERSION%/
echo.
echo   Log complet : %LOG_FILE%
pause
exit /b 1

:: ── Verification du fichier telecharge ────────────────────────
:verify_download
if not exist "%PY_INSTALLER%" (
    call :log_error "Fichier telecharge introuvable : %PY_INSTALLER%"
    goto :download_failed
)

:: Verifier taille minimale (> 1 Mo = 1048576 octets)
for %%F in ("%PY_INSTALLER%") do set FILE_SIZE=%%~zF
call :log "Taille du fichier telecharge : %FILE_SIZE% octets"
if %FILE_SIZE% LSS 1048576 (
    call :log_error "Fichier telecharge trop petit (%FILE_SIZE% octets) - probablement corrompu"
    del "%PY_INSTALLER%" >nul 2>&1
    goto :download_failed
)
call :log_ok "Fichier telecharge valide (%FILE_SIZE% octets)"
goto :run_python_installer

:download_failed
echo.
echo   Le telechargement a echoue.
echo   Installez Python manuellement depuis : https://www.python.org/downloads/
echo   Puis relancez install.bat
echo.
echo   Log complet : %LOG_FILE%
pause
exit /b 1

:: ── Installation de Python ─────────────────────────────────────
:run_python_installer
echo.
call :log "Lancement de l'installateur Python..."
echo   Installation de Python en cours...
echo   (Des fenetres UAC peuvent apparaitre - cliquez Oui)
echo.

"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 ^
    Include_test=0 Include_launcher=1 >> "%LOG_FILE%" 2>&1
set INSTALL_RESULT=%errorlevel%

call :log "Code retour installateur Python : %INSTALL_RESULT%"

if %INSTALL_RESULT% neq 0 (
    call :log_error "L'installateur Python a retourne une erreur (code %INSTALL_RESULT%)"
    echo   Essayez d'installer Python manuellement.
    echo   Log : %LOG_FILE%
    pause
    exit /b 1
)

:: Nettoyer l'installateur
del "%PY_INSTALLER%" >nul 2>&1

:: Rafraichir le PATH pour cette session
call :log "Rafraichissement du PATH..."
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts"
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"

:: Verifier que Python est bien accessible
python --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    call :log_ok "Python installe avec succes : !PY_VER!"
    goto :run_installer
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=py
    call :log_ok "Python accessible via py launcher"
    goto :run_installer
)

call :log_error "Python installe mais non accessible. Redemarrez et relancez install.bat"
echo   Log : %LOG_FILE%
pause
exit /b 1

:: ── Lancer install.py ─────────────────────────────────────────
:run_installer
echo.
call :log "Lancement de install.py avec !PYTHON_CMD!..."
echo   Installation de PDF Header Tool en cours...
echo.

set SCRIPT_DIR=%~dp0

"!PYTHON_CMD!" "%SCRIPT_DIR%install.py"
set INSTALL_PY_RESULT=%errorlevel%

call :log "Code retour install.py : %INSTALL_PY_RESULT%"

if %INSTALL_PY_RESULT% neq 0 (
    call :log_error "install.py a retourne une erreur (code %INSTALL_PY_RESULT%)"
    echo   Consultez le log pour les details : %LOG_FILE%
    pause
    exit /b 1
)

call :log "Installation terminee avec succes"
endlocal
exit /b 0

:: ── Annulation ────────────────────────────────────────────────
:cancelled
call :log "Installation annulee par l'utilisateur"
echo.
echo   Installation annulee.
pause
exit /b 0
