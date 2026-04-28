@echo off
REM Build script for BDE Treasury Management App
setlocal

echo Building BDE Treasury Management Application...

set "APP_NAME=BDE Tresorerie"
set "REQUIRED_PYTHON=3.12.10"
set "DIST_DIR=Build EXE"
set "EXE_PATH=%DIST_DIR%\%APP_NAME%.exe"
set "ROOT_DIR=%CD%"
set "PYINSTALLER_WORK_DIR=%TEMP%\%APP_NAME%-pyinstaller"

set "RECREATE_VENV=0"

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:3] == (3, 12, 10) else 1)"
    if errorlevel 1 (
        echo Existing .venv is not Python %REQUIRED_PYTHON%. Recreating environment...
        set "RECREATE_VENV=1"
    )
)

if "%RECREATE_VENV%"=="1" (
    rmdir /s /q ".venv"
)

REM Create virtual environment if it doesn't exist
if not exist ".venv\" (
    echo Creating virtual environment...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python %REQUIRED_PYTHON% est requis pour le build.
        echo Installez-le puis relancez build.bat
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Impossible de creer l'environnement virtuel dans .venv
    exit /b 1
)

.venv\Scripts\python.exe -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info[:3] == (3, 12, 10) else 1)"
if errorlevel 1 (
    echo ERROR: La version Python dans .venv n'est pas %REQUIRED_PYTHON%.
    echo Installez Python %REQUIRED_PYTHON% puis relancez build.bat
    exit /b 1
)

REM Install/update dependencies
echo Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Echec de la mise a jour de pip
    exit /b 1
)

.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Echec de l'installation des dependances
    exit /b 1
)

echo Installing PyInstaller...
.venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Echec de l'installation de PyInstaller
    exit /b 1
)

echo Building executable...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%"
)
if exist "%PYINSTALLER_WORK_DIR%" (
    rmdir /s /q "%PYINSTALLER_WORK_DIR%"
)

.venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "%APP_NAME%" ^
    --distpath "%DIST_DIR%" ^
    --workpath "%PYINSTALLER_WORK_DIR%" ^
    --specpath "%PYINSTALLER_WORK_DIR%" ^
    --add-data "%ROOT_DIR%\app\frontend\static;app\frontend\static" ^
    --add-data "%ROOT_DIR%\app\frontend\templates;app\frontend\templates" ^
    main.py
if errorlevel 1 (
    echo ERROR: Echec de la generation de l'executable
    exit /b 1
)

echo Preparing distribution folder...
if not exist "%DIST_DIR%\justificatifs" (
    mkdir "%DIST_DIR%\justificatifs"
)
if not exist "%DIST_DIR%\mandats" (
    mkdir "%DIST_DIR%\mandats"
)

if not exist "%EXE_PATH%" (
    echo ERROR: Executable introuvable: %EXE_PATH%
    exit /b 1
)

for %%F in ("data\budget.db" "data\mandats.db") do (
    if exist "%%~fF" (
        copy /Y "%%~fF" "%DIST_DIR%\%%~nxF" >nul
        if exist "%%~fF-wal" copy /Y "%%~fF-wal" "%DIST_DIR%\%%~nxF-wal" >nul
        if exist "%%~fF-shm" copy /Y "%%~fF-shm" "%DIST_DIR%\%%~nxF-shm" >nul
    )
)

if exist "data\mandats" (
    robocopy "data\mandats" "%DIST_DIR%\mandats" /E /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 (
        echo ERROR: Echec de la copie du dossier des bases de mandats
        exit /b 1
    )
)

if exist "justificatifs" (
    robocopy "justificatifs" "%DIST_DIR%\justificatifs" /E /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 (
        echo ERROR: Echec de la copie du dossier justificatifs
        exit /b 1
    )
)

REM Success message
echo.
echo ============================================
echo   BUILD SUCCESSFULLY COMPLETED!
echo ============================================
echo.
echo Executable: %EXE_PATH%
echo Distribution folder: %DIST_DIR%
echo.
pause
