@echo off
setlocal

set APP_NAME=MCServerHost
set REPO=https://github.com/ionmsr/hostmcserver.git
set INSTALL_DIR=%USERPROFILE%\MCServerHost-app

echo ==================================
echo   MCServerHost Installer
echo ==================================
echo.

REM ── Check / Install Python ─────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   Python not found. Attempting to install...
    where winget >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    ) else (
        where choco >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            choco install python -y
        ) else (
            echo   Cannot auto-install Python.
            echo   Download from https://www.python.org/downloads/
            echo   Make sure to check "Add Python to PATH".
            pause
            exit /b 1
        )
    )
)
python --version
echo.

REM ── Check / Install Java ───────────────────────────
echo [2/5] Checking Java...
java -version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   Java not found. Attempting to install...
    where winget >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        winget install EclipseAdoptium.Temurin.21.JRE --accept-source-agreements --accept-package-agreements
    ) else (
        where choco >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            choco install temurin21 -y
        ) else (
            echo   Cannot auto-install Java.
            echo   Download from https://adoptium.net
        )
    )
)
java -version 2>&1 | findstr /i "version"
echo.

REM ── Check Git ──────────────────────────────────────
echo [3/5] Checking Git...
git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   Git not found.
    where winget >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        winget install Git.Git --accept-source-agreements --accept-package-agreements
    ) else (
        echo   Download from https://git-scm.com
        pause
        exit /b 1
    )
)
git --version
echo.

REM ── Clone / Update ─────────────────────────────────
echo [4/5] Downloading MCServerHost...
if exist "%INSTALL_DIR%\.git" (
    echo   Repository exists. Updating...
    cd /d "%INSTALL_DIR%"
    git pull --ff-only 2>nul
) else (
    if exist "%INSTALL_DIR%" (
        rmdir /s /q "%INSTALL_DIR%"
    )
    git clone "%REPO%" "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)
echo.

REM ── Create Desktop Shortcut ────────────────────────
echo [5/5] Creating desktop shortcut...
set SHORTCUT=%USERPROFILE%\Desktop\MCServerHost.bat
echo @echo off > "%SHORTCUT%"
echo cd /d "%INSTALL_DIR%" >> "%SHORTCUT%"
echo call run.bat >> "%SHORTCUT%"
echo   Shortcut created on Desktop.
echo.

echo ==================================
echo   Installation Complete!
echo ==================================
echo.
echo   Location: %INSTALL_DIR%
echo   Run:      Double-click MCServerHost.bat on Desktop
echo             or run "%INSTALL_DIR%\run.bat"
echo.

pause
