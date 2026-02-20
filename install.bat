@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PDF Header Tool - Installation
color 0A
cls

set "SCRIPT_DIR=%~dp0"
set "LOG_FILE=%SCRIPT_DIR%pdf_header_install.log"
set "PYTHON_CMD=python"
set "PY_VERSION=3.13.1"
set "PY_ARCH=amd64"
set "PY_INSTALLER="

if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if "%PROCESSOR_ARCHITEW6432%"=="" set "PY_ARCH=win32"
for /f "tokens=1,2 delims=." %%a in ("%PY_VERSION%") do set "PY_FOLDER=Python%%a%%b"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-%PY_ARCH%.exe"
set "PY_INSTALLER=%TEMP%\python_%PY_VERSION%_%PY_ARCH%.exe"

echo [%date% %time%] Debut installation > "%LOG_FILE%"
echo [%date% %time%] OS=%OS% >> "%LOG_FILE%"
echo [%date% %time%] USER=%USERNAME% >> "%LOG_FILE%"
echo [%date% %time%] DIR=%SCRIPT_DIR% >> "%LOG_FILE%"

goto :main

:log
echo [%date% %time%] %~1>> "%LOG_FILE%"
echo   %~1
goto :eof

:log_ok
echo [%date% %time%] [OK] %~1>> "%LOG_FILE%"
echo   [OK] %~1
goto :eof

:log_error
echo [%date% %time%] [ERROR] %~1>> "%LOG_FILE%"
echo.
echo   [ERROR] %~1
echo.
goto :eof

:fail
call :log_error "%~1"
echo   Log: %LOG_FILE%
pause
endlocal
exit /b 1

:main
echo ============================================================
echo   PDF Header Tool - Installation
echo   Log : %LOG_FILE%
echo ============================================================
echo.
call :log "Demarrage install.bat"

call :log "Etape: verification Python via 'python --version'"
python --version >nul 2>&1
if errorlevel 1 (
    call :log "Python non detecte dans PATH"
    goto :python_missing_menu
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
call :log_ok "Python detecte: !PY_VER!"
goto :python_present

:python_missing_menu
echo.
echo   Python n'est pas detecte.
echo.
echo   1. Ouvrir python.org (manuel)
echo   2. Installation auto (winget puis curl)
echo   3. Annuler
echo.
set /p CHOICE="   Votre choix (1, 2 ou 3): "
call :log "Choix utilisateur saisi"

if "%CHOICE%"=="1" goto :open_python_org
if "%CHOICE%"=="2" goto :download_python
if "%CHOICE%"=="3" goto :cancelled
echo   Choix invalide.
goto :python_missing_menu

:python_present
call :log "Etape: tentative winget upgrade Python.Python.3"
call :check_winget
if errorlevel 1 (
    call :log "winget introuvable, upgrade ignore"
    goto :post_python_install
)

echo   Mise a jour Python via winget en cours...
winget upgrade --id Python.Python.3 -e --accept-package-agreements --accept-source-agreements --disable-interactivity >> "%LOG_FILE%" 2>&1
set "WINGET_UPGRADE_EXIT=%errorlevel%"
call :log "Code retour winget upgrade: %WINGET_UPGRADE_EXIT%"
if not "%WINGET_UPGRADE_EXIT%"=="0" (
    call :log "winget upgrade non applique (non bloquant)"
) else (
    call :log_ok "winget upgrade Python applique"
)
goto :post_python_install

:open_python_org
call :log "Ouverture python.org/downloads"
start "" "https://www.python.org/downloads/"
echo.
echo   Installez Python puis relancez install.bat.
echo   Log: %LOG_FILE%
pause
endlocal
exit /b 0

:download_python
call :log "Etape: tentative winget install Python.Python.3.13"
call :check_winget
if errorlevel 1 (
    call :log "winget introuvable, fallback curl"
    goto :download_python_curl
)

echo   Installation Python via winget en cours...
winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements --disable-interactivity >> "%LOG_FILE%" 2>&1
set "WINGET_INSTALL_EXIT=%errorlevel%"
call :log "Code retour winget install: %WINGET_INSTALL_EXIT%"
if "%WINGET_INSTALL_EXIT%"=="0" (
    call :log_ok "winget install Python reussi"
    goto :post_python_install
)

call :log "winget install a echoue, fallback curl"
goto :download_python_curl

:download_python_curl
call :log "Etape: verification curl.exe"
curl.exe --version >nul 2>&1
if errorlevel 1 (
    call :log "curl.exe introuvable, fallback python.org"
    goto :open_python_org
)

call :log "Etape: telechargement Python via curl"
call :log "URL: %PY_URL%"
call :log "Destination: %PY_INSTALLER%"
echo.
echo   Telechargement de Python %PY_VERSION% (%PY_ARCH%)...
echo.

call :log "Trace: lancement commande curl"
curl.exe -L --retry 3 --retry-delay 5 --connect-timeout 30 --max-time 300 -o "%PY_INSTALLER%" "%PY_URL%" >> "%LOG_FILE%" 2>&1
set "CURL_EXIT=%errorlevel%"
call :log "Code retour curl: %CURL_EXIT%"
if not "%CURL_EXIT%"=="0" (
    call :log "Echec telechargement curl, fallback python.org"
    goto :open_python_org
)

if not exist "%PY_INSTALLER%" (
    call :fail "Fichier telecharge introuvable"
)

for %%F in ("%PY_INSTALLER%") do set "FILE_SIZE=%%~zF"
call :log "Taille fichier telecharge: %FILE_SIZE% octets"
if %FILE_SIZE% LSS 1048576 (
    del "%PY_INSTALLER%" >nul 2>&1
    call :fail "Fichier telecharge invalide (trop petit)"
)
call :log_ok "Telechargement Python valide"
goto :run_python_installer

:run_python_installer
call :log "Etape: lancement installateur Python"
echo.
echo   Installation de Python en cours...
echo.

"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1 >> "%LOG_FILE%" 2>&1
set "PY_INSTALL_EXIT=%errorlevel%"
call :log "Code retour installateur Python: %PY_INSTALL_EXIT%"
if not "%PY_INSTALL_EXIT%"=="0" (
    call :fail "Installateur Python en erreur"
)

del "%PY_INSTALLER%" >nul 2>&1
call :log "Installateur temporaire supprime"

:post_python_install
call :log "Etape: rafraichissement PATH session"
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts"
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"

call :resolve_python_cmd
if errorlevel 1 (
    call :fail "Python installe mais non detecte. Relancez le script."
)

call :log "Etape: nouvelle verification Python"
"%PYTHON_CMD%" --version >nul 2>&1
if errorlevel 1 (
    call :fail "Python installe mais non detecte. Relancez le script."
)

for /f "tokens=*" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do set "PY_VER=%%v"
call :log_ok "Python pret: !PY_VER!"
goto :run_installer

:check_winget
winget --version >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

:resolve_python_cmd
set "PYTHON_CMD="

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py"
)

if defined PYTHON_CMD (
    call :log "Commande Python resolue: %PYTHON_CMD%"
    exit /b 0
)
exit /b 1

:run_installer
if not exist "%SCRIPT_DIR%install.py" (
    call :fail "install.py introuvable"
)

call :log "Etape: lancement install.py"
echo.
echo   Installation de PDF Header Tool en cours...
echo.

call :log "Commande Python utilisee: %PYTHON_CMD%"
"%PYTHON_CMD%" "%SCRIPT_DIR%install.py" >> "%LOG_FILE%" 2>&1
set "INSTALL_PY_RESULT=%errorlevel%"
call :log "Code retour install.py: %INSTALL_PY_RESULT%"
if not "%INSTALL_PY_RESULT%"=="0" (
    call :fail "install.py a retourne une erreur"
)

call :log_ok "Installation terminee avec succes"
echo.
echo   Installation terminee avec succes.
echo   Log: %LOG_FILE%
pause
endlocal
exit /b 0

:cancelled
call :log "Installation annulee par utilisateur"
echo.
echo   Installation annulee.
echo   Log: %LOG_FILE%
pause
endlocal
exit /b 0
