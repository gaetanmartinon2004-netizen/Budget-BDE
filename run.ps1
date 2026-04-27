# PowerShell script to run the BDE Treasury Management App

Write-Host "Starting BDE Treasury Management Application..."

# Check if virtual environment exists
if (-not (Test-Path ".\.venv")) {
    Write-Host "Virtual environment not found. Running build..."
    & .\build.bat
}

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Run the application
Write-Host "Launching application..."
python main.py
