@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Installing Dependencies for generate-plateflaws
echo ============================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in system PATH.
    echo Please install Python 3 or add python.exe to your PATH.
    pause
    exit /b 1
)

echo [1/2] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [2/2] Installing required packages from requirements.txt...
python -m pip install -r "%~dp0requirements.txt"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   Installation completed successfully!
    echo ============================================
) else (
    echo.
    echo [ERROR] Failed to install dependencies.
)

pause
