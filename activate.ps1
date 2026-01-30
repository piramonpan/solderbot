# Activate the virtual environment located in `.venv` (PowerShell)
# Usage (important): dot-source this script to activate the venv in your current shell:
#   . .\activate_venv.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$venvPath = Join-Path $scriptDir '.venv'
$activateScript = Join-Path $venvPath 'Scripts\Activate.ps1'

if (-not (Test-Path $activateScript)) {
    Write-Error "Activate script not found: $activateScript`nMake sure the virtual environment exists at: $venvPath"
    return 1
}

Write-Host "Activating virtual environment at: $venvPath"

# Dot-source the venv activation script so it affects the current session.
. $activateScript

if ($?) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        Write-Host "Activated. Python executable: $($py.Source)"
    } else {
        Write-Host "Activated virtualenv (python not found in PATH)."
    }
} else {
    Write-Error "Failed to run Activate.ps1"
}