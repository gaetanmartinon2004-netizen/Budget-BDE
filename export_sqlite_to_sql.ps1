#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Exporte les bases SQLite en SQL PostgreSQL
.DESCRIPTION
    Convertit les dumps SQLite en format importable PostgreSQL
#>

function Test-SQLiteAvailable {
    $sqlite = Get-Command sqlite3 -ErrorAction SilentlyContinue
    if ($null -eq $sqlite) {
        Write-Host "❌ sqlite3 CLI not found"
        Write-Host "   Install from: https://www.sqlite.org/download.html"
        return $false
    }
    return $true
}

function Export-SQLiteToSQL {
    param(
        [string]$DBPath,
        [string]$OutputPath
    )
    
    if (-not (Test-Path $DBPath)) {
        Write-Host "⚠️  Not found: $DBPath"
        return
    }
    
    Write-Host "Processing: $DBPath"
    
    # Exporte le dump SQLite
    $tempDump = [System.IO.Path]::GetTempFileName()
    sqlite3 $DBPath ".dump" | Out-File -Encoding UTF8 $tempDump
    
    # Lit le dump et le convertit
    $content = Get-Content $tempDump -Raw -Encoding UTF8
    
    # Conversions SQLite → PostgreSQL
    $content = $content -replace 'AUTOINCREMENT', 'SERIAL'
    $content = $content -replace 'INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY'
    $content = $content -replace "(?i)BEGIN TRANSACTION", 'BEGIN TRANSACTION'
    
    # Ajoute le header
    $header = @"
-- PostgreSQL Migration Dump
-- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
-- Source: $DBPath
-- Note: Review and test before importing to production

BEGIN TRANSACTION;

"@
    
    $footer = @"

COMMIT;
"@
    
    # Écrit le fichier de sortie
    $outputContent = $header + $content + $footer
    $outputContent | Out-File -Encoding UTF8 $OutputPath
    
    Remove-Item $tempDump -Force
    Write-Host "✓ Exported: $OutputPath"
}

function Main {
    Write-Host "🔄 SQLite to PostgreSQL Migration`n"
    
    # Vérifie que sqlite3 est dispo
    if (-not (Test-SQLiteAvailable)) {
        Write-Host "`nℹ️  You can install sqlite3 via:"
        Write-Host "    choco install sqlite (if Chocolatey installed)"
        Write-Host "    Or download from https://www.sqlite.org/download.html"
        return
    }
    
    # Crée le dossier de sortie
    $outputDir = "data\db PostgreSQL"
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    
    # Bases à exporter
    $databases = @(
        @{
            Source = "data/budget.db"
            Dest   = "data/db PostgreSQL/budget.sql"
        },
        @{
            Source = "data/mandats.db"
            Dest   = "data/db PostgreSQL/mandats.sql"
        },
        @{
            Source = "data/mandats/budget_riptide_2025_26.db"
            Dest   = "data/db PostgreSQL/budget_riptide_2025_26.sql"
        },
        @{
            Source = "data/mandats/budget_test.db"
            Dest   = "data/db PostgreSQL/budget_test.sql"
        }
    )
    
    # Exporte chaque base
    foreach ($db in $databases) {
        Export-SQLiteToSQL -DBPath $db.Source -OutputPath $db.Dest
    }
    
    # Crée le script d'import unifié
    $importScript = "data/db PostgreSQL/IMPORT_ALL.sql"
    $importContent = @"
-- Import all databases to PostgreSQL
-- Usage: psql -U user -d database -f IMPORT_ALL.sql

"@
    
    foreach ($db in $databases) {
        $sqlFile = (Resolve-Path $db.Dest).Path
        $importContent += "\i '$sqlFile'`n"
    }
    
    $importContent | Out-File -Encoding UTF8 $importScript
    Write-Host "✓ Created: $importScript"
    
    Write-Host "`n✅ Export complete!`n"
    Write-Host "📁 Output: data/db PostgreSQL/"
    Write-Host "`n📋 Next steps:"
    Write-Host "  1. Review the SQL files in data/db PostgreSQL/"
    Write-Host "  2. Import to PostgreSQL:"
    Write-Host "     Option A: Copy-paste into Supabase SQL Editor"
    Write-Host "     Option B: psql -U user -d dbname -f data/db\ PostgreSQL/IMPORT_ALL.sql"
    Write-Host "  3. Verify tables were created: SELECT * FROM mandats LIMIT 1;"
}

Main
