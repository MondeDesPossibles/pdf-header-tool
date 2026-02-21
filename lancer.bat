@echo off
:: ==============================================================================
:: PDF Header Tool - lancer.bat
:: Version : 0.4.6
:: Build   : build-2026.02.21.03
:: Repo    : MondeDesPossibles/pdf-header-tool
:: Point d'entree Windows pour le modele portable (Python Embarque)
:: ==============================================================================
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PDF Header Tool

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%python\python.exe"
set "FITZ_CHECK=%SCRIPT_DIR%site-packages\fitz\__init__.py"
set "LOG_FILE=%SCRIPT_DIR%pdf_header_launch.log"
set "BUILD_ID=build-2026.02.21.03"

echo [%date% %time%] Lancement PDF Header Tool > "%LOG_FILE%"
echo [%date% %time%] Build: %BUILD_ID% >> "%LOG_FILE%"
echo [%date% %time%] SCRIPT_DIR: %SCRIPT_DIR% >> "%LOG_FILE%"

:: --- Verification Python embarque ---
if not exist "%PYTHON_EXE%" (
    echo [%date% %time%] [ERROR] python\python.exe introuvable >> "%LOG_FILE%"
    echo.
    echo   Erreur : python\python.exe introuvable.
    echo   Verifiez que le dossier python\ est present dans le dossier de l'application.
    echo.
    pause
    endlocal
    exit /b 1
)
echo [%date% %time%] [OK] Python embarque detecte >> "%LOG_FILE%"

:: --- Installation des dependances si absentes ---
if not exist "%FITZ_CHECK%" (
    echo [%date% %time%] Dependances absentes, lancement setup.bat >> "%LOG_FILE%"
    echo.
    echo   Premiere installation des dependances en cours...
    echo   (connexion internet requise - quelques minutes)
    echo.
    call "%SCRIPT_DIR%setup.bat"
    if errorlevel 1 (
        echo [%date% %time%] [ERROR] setup.bat a echoue >> "%LOG_FILE%"
        echo.
        echo   Erreur lors de l'installation des dependances.
        echo   Consultez pdf_header_install.log pour les details.
        echo.
        pause
        endlocal
        exit /b 1
    )
    echo [%date% %time%] [OK] setup.bat termine avec succes >> "%LOG_FILE%"
)

:: --- Lancement de l'application ---
echo [%date% %time%] Lancement pdf_header.py >> "%LOG_FILE%"
"%PYTHON_EXE%" "%SCRIPT_DIR%pdf_header.py"
set "APP_RESULT=%errorlevel%"
echo [%date% %time%] Code retour application: %APP_RESULT% >> "%LOG_FILE%"

endlocal
exit /b %APP_RESULT%
