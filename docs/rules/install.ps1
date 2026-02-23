# Get the directory where the script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptDir)) { $scriptDir = "." }

# Target directory for Claude Desktop rules
$targetDir = Join-Path $HOME ".claude\rules"

# Ensure target directory exists
if (!(Test-Path $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
}

# Always install common rules
$commonSrc = Join-Path $scriptDir "common"
if (Test-Path $commonSrc -PathType Container) {
    Write-Host "Installing common rules to $targetDir..."
    Copy-Item -Path $commonSrc -Destination $targetDir -Recurse -Force
}
else {
    Write-Error "Error: 'common' directory not found in $scriptDir"
    exit 1
}

# Install requested language rules
foreach ($lang in $args) {
    $langSrc = Join-Path $scriptDir $lang
    if (Test-Path $langSrc -PathType Container) {
        Write-Host "Installing $lang rules..."
        Copy-Item -Path $langSrc -Destination $targetDir -Recurse -Force
    }
    else {
        Write-Warning "Language directory '$lang' not found. Skipping."
    }
}

Write-Host "Installation complete. Rules are located in: $targetDir"
