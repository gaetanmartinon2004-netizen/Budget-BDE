@echo off
REM Script pour pousser le code sur GitHub - Double cliquable

REM Ajouter Git au PATH
set PATH=%PATH%;C:\Program Files\Git\bin

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
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas disponible!
    pause
    exit /b 1
)

echo [OK] Git disponible
echo.

REM Afficher le statut
echo --- Statut actuel ---
git status
echo.

REM Ajouter les fichiers
echo [*] Ajout de tous les fichiers...
git add .
echo [OK] Fichiers ajoutés

REM Créer le commit
echo.
echo [*] Création du commit...
set /p commitMsg=Entrez le message de commit (ou appuyez sur Entrée): 
if "%commitMsg%"=="" set commitMsg=Update: Modifications du code
git commit -m "%commitMsg%" --allow-empty
echo [OK] Commit créé

REM Pousser vers GitHub
echo.
echo [*] Poussée vers GitHub (main)...
git push origin main
if errorlevel 1 (
    echo [ERREUR] Echec du push!
    pause
    exit /b 1
)
echo [OK] Code poussé sur GitHub

REM Afficher le statut final
echo.
echo --- Statut final ---
git status
echo.
git log --oneline -3
echo.
echo ========================================
echo   PUSH TERMINÉ AVEC SUCCÈS!
echo ========================================
echo.
pause
