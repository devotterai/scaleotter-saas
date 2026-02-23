<#
.SYNOPSIS
ScaleOtter Ghost Laptop Provisioning Script

.DESCRIPTION
This script sets up a "Ghost Laptop" physical node. It installs necessary dependencies (Python, Git),
clones the GitHub repository (if accessible), sets up a virtual environment, generates a unique
DEVICE_ID, and configures the Ghost Worker to run in the background.

.NOTES
Requires Administrator privileges to install system packages and create Scheduled Tasks.
#>

# Ensure running as Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Please run this script as an Administrator."
    Exit
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " ScaleOtter Ghost Laptop Auto-Provisioner" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Install Dependencies Wait for winget
Write-Host "[1/5] Installing Dependencies..." -ForegroundColor Yellow
$packages = @("Python.Python.3.11", "Git.Git", "Google.Chrome")
foreach ($pkg in $packages) {
    Write-Host "  Checking/Installing $pkg..."
    winget install --id $pkg --accept-package-agreements --accept-source-agreements --silent --disable-interactivity
}

# 2. Setup Directory & Repo
Write-Host "`n[2/5] Setting up Execution Environment..." -ForegroundColor Yellow
$GhostDir = "C:\ScaleOtterGhost"

if (-not (Test-Path $GhostDir)) {
    New-Item -ItemType Directory -Force -Path $GhostDir | Out-Null
    Write-Host "  Created directory: $GhostDir"
}

Set-Location $GhostDir

# Assuming the repo exists or we're just copying it manually in dev
# For production: git clone https://github.com/YourOrg/ScaleOtter.git .
Write-Host "  Note: Ensure the ScaleOtter codebase is cloned into $GhostDir"

# 3. Generating Identity
Write-Host "`n[3/5] Generating Ghost Identity..." -ForegroundColor Yellow
$EnvFile = Join-Path $GhostDir "ghost-engine\.env"

$DeviceId = "GHOST-" + $([guid]::NewGuid().ToString().Substring(0,8).ToUpper())

Write-Host "  Generated Device ID: " -NoNewline; Write-Host $DeviceId -ForegroundColor Green

if (-not (Test-Path $EnvFile)) {
    Write-Host "  Creating new .env file in ghost-engine\"
    
    $SupabaseUrl = Read-Host "  Enter Supabase URL"
    $SupabaseKey = Read-Host "  Enter Supabase Service Key"

    $envContent = @"
DEVICE_ID=$DeviceId
SUPABASE_URL=$SupabaseUrl
SUPABASE_SERVICE_KEY=$SupabaseKey
"@
    
    # Ensure ghost-engine folder exists
    if (-not (Test-Path (Join-Path $GhostDir "ghost-engine"))) {
        New-Item -ItemType Directory -Path (Join-Path $GhostDir "ghost-engine") | Out-Null
    }

    Set-Content -Path $EnvFile -Value $envContent
    Write-Host "  Environment configured."
} else {
    Write-Host "  .env file already exists. Skipping..."
}

# 4. Python Environment setup
Write-Host "`n[4/5] Setting up Python Virtual Environment..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $GhostDir "ghost-engine\venv"))) {
    Set-Location (Join-Path $GhostDir "ghost-engine")
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
    } else {
        pip install supabase playwright python-dotenv
        playwright install chromium
    }
}

# 5. Background Task
Write-Host "`n[5/5] Configuring Background Service..." -ForegroundColor Yellow
$TaskName = "ScaleOtterGhostWorker"

# Check if task already exists
$Exists = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $Exists) {
    $Action = New-ScheduledTaskAction -Execute "C:\ScaleOtterGhost\ghost-engine\venv\Scripts\python.exe" -Argument "C:\ScaleOtterGhost\ghost-engine\ghost_worker.py" -WorkingDirectory "C:\ScaleOtterGhost\ghost-engine"
    $Trigger = New-ScheduledTaskTrigger -AtStartup
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
    
    Register-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -TaskName $TaskName -Description "Runs the ScaleOtter Ghost Worker queue listener" -User "SYSTEM" | Out-Null
    Write-Host "  Scheduled task created successfully."
} else {
    Write-Host "  Scheduled task already exists."
}

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host " Provisioning Complete!" -ForegroundColor Green
Write-Host " Ghost Device ID: $DeviceId"
Write-Host " Please register this ID in the Parant Dashboard via the Web UI."
Write-Host "=========================================" -ForegroundColor Cyan
