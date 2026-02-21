@echo off
:: ==============================================================================
:: PDF Header Tool - setup.bat
:: Version : 0.4.6
:: Build   : build-2026.02.21.03
:: Repo    : MondeDesPossibles/pdf-header-tool
:: Installation des dependances au premier lancement (Python Embarque)
:: Appele automatiquement par lancer.bat si site-packages\fitz\ est absent.
:: ==============================================================================
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PDF Header Tool - Installation dependances

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%python\python.exe"
set "GET_PIP=%SCRIPT_DIR%get-pip.py"
set "SITE_PACKAGES=%SCRIPT_DIR%site-packages"
set "LOG_FILE=%SCRIPT_DIR%pdf_header_install.log"
set "BUILD_ID=build-2026.02.21.03"

echo [%date% %time%] Debut installation dependances > "%LOG_FILE%"
echo [%date% %time%] Build: %BUILD_ID% >> "%LOG_FILE%"
echo [%date% %time%] SCRIPT_DIR: %SCRIPT_DIR% >> "%LOG_FILE%"

echo.
echo   Installation des dependances PDF Header Tool...
echo   (connexion internet requise)
echo.

:: --- Verification Python embarque ---
if not exist "%PYTHON_EXE%" (
    echo [%date% %time%] [ERROR] python\python.exe introuvable >> "%LOG_FILE%"
    echo   Erreur : python\python.exe introuvable.
    pause
    endlocal
    exit /b 1
)
echo [%date% %time%] [OK] Python embarque: %PYTHON_EXE% >> "%LOG_FILE%"

:: --- Verification get-pip.py ---
if not exist "%GET_PIP%" (
    echo [%date% %time%] [ERROR] get-pip.py introuvable >> "%LOG_FILE%"
    echo.
    echo   Erreur : get-pip.py introuvable.
    echo   Ce fichier doit etre present dans le dossier de l'application.
    echo.
    pause
    endlocal
    exit /b 1
)
echo [%date% %time%] [OK] get-pip.py detecte >> "%LOG_FILE%"

:: --- Creation dossier site-packages ---
if not exist "%SITE_PACKAGES%" (
    mkdir "%SITE_PACKAGES%"
    echo [%date% %time%] Dossier site-packages cree >> "%LOG_FILE%"
)

:: --- Etape 1 : installation pip via get-pip.py ---
echo [%date% %time%] Etape 1: installation pip >> "%LOG_FILE%"
echo   Etape 1/2 : installation de pip...
"%PYTHON_EXE%" "%GET_PIP%" --no-warn-script-location >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] [ERROR] Installation pip echouee >> "%LOG_FILE%"
    echo.
    echo   Erreur lors de l'installation de pip.
    echo   Consultez %LOG_FILE% pour les details.
    echo.
    pause
    endlocal
    exit /b 1
)
echo [%date% %time%] [OK] pip installe >> "%LOG_FILE%"

:: --- Etape 2 : installation dependances dans site-packages ---
echo [%date% %time%] Etape 2: installation pymupdf pillow customtkinter >> "%LOG_FILE%"
echo   Etape 2/2 : installation pymupdf, Pillow, customtkinter...
"%PYTHON_EXE%" -m pip install --target="%SITE_PACKAGES%" pymupdf pillow customtkinter >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] [ERROR] Installation paquets echouee >> "%LOG_FILE%"
    echo.
    echo   Erreur lors de l'installation des paquets.
    echo   Consultez %LOG_FILE% pour les details.
    echo.
    pause
    endlocal
    exit /b 1
)
echo [%date% %time%] [OK] pymupdf, Pillow, customtkinter installes >> "%LOG_FILE%"

echo [%date% %time%] Installation terminee avec succes >> "%LOG_FILE%"
echo.
echo   Installation terminee avec succes.
echo.

endlocal
exit /b 0
