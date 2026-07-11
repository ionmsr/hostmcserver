@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        goto :run
    )
)

py -3 --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    goto :run_with_py
)

echo Python 3 is not installed. Attempting to install...

where winget >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Installing Python via winget...
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    goto :check_after_install
)

where choco >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Installing Python via Chocolatey...
    choco install python -y
    goto :check_after_install
)

where pip >nul 2>&1
if %ERRORLEVEL% equ 0 (
    goto :run
)

echo Could not install Python automatically.
echo Please download and install Python 3.8+ from:
echo https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:check_after_install
python --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Python installed successfully.
    goto :run
)

py -3 --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Python installed successfully.
    goto :run_with_py
)

echo Python installation may require a terminal restart.
echo Please close and reopen this window, then run run.bat again.
echo Or install Python manually from: https://www.python.org/downloads/
pause
exit /b 1

:run
python mcserverhost.py
pause
exit /b 0

:run_with_py
py -3 mcserverhost.py
pause
exit /b 0
