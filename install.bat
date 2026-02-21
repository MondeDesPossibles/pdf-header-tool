@echo off
:: ==============================================================================
:: PDF Header Tool - install.bat
:: Version : 0.4.0
:: Build   : build-2026.02.21.01
:: Repo    : MondeDesPossibles/pdf-header-tool
:: ==============================================================================
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PDF Header Tool - Installation
color 0A
cls

set "SCRIPT_DIR=%~dp0"
set "LOG_FILE=%SCRIPT_DIR%pdf_header_install.log"
set "BUILD_ID=build-2026.02.21.01"
set "PYTHON_CMD=python"
set "PY_EXE="

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
call :log "Build install.bat: %BUILD_ID%"

:checkpython
call :log "Etape: verification Python via 'python --version'"
python --version >nul 2>&1
if errorlevel 1 goto :nopython

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
call :log_ok "Python detecte: !PY_VER!"
for /f "tokens=*" %%p in ('python -c "import sys; print(sys.executable)" 2^>^&1') do set "PY_EXE=%%p"
call :log "Python executable: !PY_EXE!"
echo(!PY_EXE! | find /I "WindowsApps" >nul
if not errorlevel 1 goto :storepython
echo(!PY_EXE! | find /I "PythonSoftwareFoundation.Python." >nul
if not errorlevel 1 goto :storepython
goto :runinstaller

:nopython
call :log "Python non detecte, ouverture python.org/downloads"
echo.
echo   Python n'est pas detecte.
echo   Installez Python manuellement depuis python.org puis relancez install.bat.
echo.
start "" "https://www.python.org/downloads/"
pause
endlocal
exit /b 1

:storepython
call :log_error "Python Microsoft Store detecte (non supporte pour installation stable)"
echo   Python Microsoft Store detecte.
echo   Pour une installation stable, installez Python officiel depuis python.org.
echo   URL : https://www.python.org/downloads/
start "" "https://www.python.org/downloads/"
pause
endlocal
exit /b 1

:runinstaller
if not exist "%SCRIPT_DIR%install.py" (
    call :fail "install.py introuvable"
)

call :log "Etape: lancement install.py"
echo.
echo   Installation de PDF Header Tool en cours...
echo.

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
endlocal
exit /b 0
