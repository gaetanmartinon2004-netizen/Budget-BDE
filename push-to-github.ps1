# Script pour pousser le code sur GitHub branche main

# Ajouter Git au PATH
$env:Path += ";C:\Program Files\Git\bin"

# Obtenir le répertoire courant
$projectDir = "C:\Users\gaeta\OneDrive - Builders Ecole d'Ingénieurs\1 - Scolaire\BDE 2025\Budget\Budget BDE"

# Changer de répertoire
Set-Location $projectDir

Write-Host "📁 Répertoire: $projectDir" -ForegroundColor Cyan
Write-Host ""

# Vérifier que git est disponible
try {
    $gitVersion = git --version
    Write-Host "✅ Git disponible: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git n'est pas disponible!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔄 Vérification du statut actuel..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "📝 Ajout de tous les fichiers..." -ForegroundColor Yellow
git add .

Write-Host ""
Write-Host "💾 Création du commit..." -ForegroundColor Yellow
$commitMessage = "Update: Push all code to GitHub main branch"
git commit -m "$commitMessage" --allow-empty

Write-Host ""
Write-Host "🚀 Poussée vers GitHub (main)..." -ForegroundColor Yellow
git push origin main

Write-Host ""
Write-Host "✅ Terminé!" -ForegroundColor Green
Write-Host "📊 Statut final:" -ForegroundColor Cyan
git status
git log --oneline -3
