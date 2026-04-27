@echo off
REM Batch script to run the BDE Treasury Management App
setlocal

echo Starting BDE Treasury Management Application...

REM Check if virtual environment exists
if not exist ".venv\" (
    echo Virtual environment not found. Running build...
    call build.bat
    if errorlevel 1 (
        echo ERROR: Build failed.
        exit /b 1
    )
)

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
    if errorlevel 1 (
        echo Incompatible Python version in .venv. Rebuilding...
        call build.bat
        if errorlevel 1 (
            echo ERROR: Build failed.
            exit /b 1
        )
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python executable not found in .venv\Scripts
    exit /b 1
)

REM Run the application
echo Launching application...
.venv\Scripts\python.exe main.py

pause
