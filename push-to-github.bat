@echo off
REM Script pour pousser le code sur GitHub - Double cliquable

REM Ajouter Git au PATH
set PATH=%PATH%;C:\Program Files\Git\bin
set GIT_EXE=C:\Program Files\Git\bin\git.exe

REM Obtenir le répertoire du script
cd /d "%~dp0"

REM Couleurs et messages
cls
echo.
echo ========================================
echo   PUSH CODE TO GITHUB (Budget BDE)
echo ========================================
echo.

REM Vérifier que git existe
"%GIT_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas disponible!
    pause
    exit /b 1
)

echo [OK] Git disponible
echo.

REM Afficher le statut
echo --- Statut actuel ---
"%GIT_EXE%" status
echo.

REM Ajouter les fichiers
echo [*] Ajout de tous les fichiers...
"%GIT_EXE%" add .
echo [OK] Fichiers ajoutés

REM Créer le commit
echo.
echo [*] Création du commit...
set /p commitMsg=Entrez le message de commit (ou appuyez sur Entrée): 
if "%commitMsg%"=="" set commitMsg=Update: Modifications du code
"%GIT_EXE%" commit -m "%commitMsg%"
if errorlevel 1 (
    echo [ERREUR] Echec du commit! Verifiez user.name/user.email et les changements.
    pause
    exit /b 1
)
echo [OK] Commit créé

REM Synchroniser avec le remote avant le push
echo.
echo [*] Synchronisation avec origin/main...
"%GIT_EXE%" pull --rebase origin main
if errorlevel 1 (
    echo [ERREUR] Echec du pull --rebase! Resolution manuelle requise.
    pause
    exit /b 1
)
echo [OK] Synchronisation terminée

REM Pousser vers GitHub
echo.
echo [*] Poussée vers GitHub (main)...
"%GIT_EXE%" push origin main
if errorlevel 1 (
    echo [ERREUR] Echec du push!
    pause
    exit /b 1
)
echo [OK] Code poussé sur GitHub

REM Afficher le statut final
echo.
echo --- Statut final ---
"%GIT_EXE%" status
echo.
"%GIT_EXE%" log --oneline -3
echo.
echo ========================================
echo   PUSH TERMINÉ AVEC SUCCÈS!
echo ========================================
echo.
pause
