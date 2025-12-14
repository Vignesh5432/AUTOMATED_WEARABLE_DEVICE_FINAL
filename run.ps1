param(
  [string]$Env = "development"
)

# Ensure we run from the script's directory
Set-Location -Path $PSScriptRoot

Write-Host "Starting Flask (FLASK_APP=backend, FLASK_ENV=$Env)"
$Env:FLASK_APP = 'backend'
$Env:FLASK_ENV = $Env
flask run
