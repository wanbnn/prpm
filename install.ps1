#!/usr/bin/env pwsh
#Requires -Version 5.1
<#
.SYNOPSIS
    Install PRPM, the package manager for the PyReact ecosystem.

.DESCRIPTION
    Installs the published prpm package from PyPI, or the development version
    directly from the GitHub repository.

.PARAMETER Dev
    Install the development version from GitHub instead of the published PyPI
    release.

.PARAMETER Ref
    Install a specific git ref (branch, tag, or commit). Implies -Dev.

.PARAMETER User
    Install into the user site instead of the active environment.

.PARAMETER Upgrade
    Upgrade an existing installation to the requested version.

.PARAMETER NoVerify
    Skip the post-install verification step.

.PARAMETER Python
    Override the Python interpreter to use. Defaults to the first one found on
    PATH that satisfies the minimum version requirement.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Dev
    .\install.ps1 -Ref v0.3.0
    .\install.ps1 -User -Upgrade

.NOTES
    Requires PowerShell 5.1+ and Python 3.9+.
#>

[CmdletBinding()]
param(
    [switch]$Dev,
    [string]$Ref,
    [switch]$User,
    [switch]$Upgrade,
    [switch]$NoVerify,
    [string]$Python
)

$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/wanbnn/prpm'
$DefaultRef = 'main'
$Package = 'prpm'
$MinMajor = 3
$MinMinor = 9

function Write-Info  { param([string]$Message) Write-Host ":: $Message" -ForegroundColor Blue }
function Write-Ok    { param([string]$Message) Write-Host "OK $Message" -ForegroundColor Green }
function Write-Fail  { param([string]$Message) Write-Host "!! $Message" -ForegroundColor Red }
function Write-Title { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }

function Get-PythonCandidates {
    if ($Python) {
        return ,$Python
    }
    $candidates = @('python', 'python3', 'py')
    $found = @()
    foreach ($name in $candidates) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            $found += $cmd.Source
        }
    }
    return $found
}

function Test-PythonVersion {
    param([string]$Path)
    try {
        $versionOutput = & $Path '-c' 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if (-not $versionOutput) { return $false }
        $parts = $versionOutput.Trim().Split('.')
        if ($parts.Count -lt 2) { return $false }
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        return ($major -gt $MinMajor) -or ($major -eq $MinMajor -and $minor -ge $MinMinor)
    } catch {
        return $false
    }
}

function Resolve-Python {
    foreach ($candidate in Get-PythonCandidates) {
        if (Test-PythonVersion -Path $candidate) {
            return $candidate
        }
    }
    return $null
}

function Show-Usage {
    @"
Usage: .\install.ps1 [options]

Options:
  -Dev              Install the development version from GitHub ($DefaultRef)
  -Ref <ref>        Install a specific git ref (branch, tag, or commit). Implies -Dev.
  -User             Install into the user site instead of the active environment
  -Upgrade          Upgrade an existing installation to the requested version
  -NoVerify         Skip the post-install verification step
  -Python <path>    Override the Python interpreter to use
  -Help             Show this help and exit

Examples:
  .\install.ps1
  .\install.ps1 -Dev
  .\install.ps1 -Ref v0.3.0
  .\install.ps1 -User -Upgrade
"@
}

if ($MyArgs -contains '-h' -or $MyArgs -contains '--help') {
    Write-Output (Show-Usage)
    exit 0
}

Write-Title "PRPM installer"

if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Fail "pip was not found on PATH. Install Python 3.9+ and ensure that pip is available."
    exit 1
}

$pythonBin = Resolve-Python
if (-not $pythonBin) {
    Write-Fail "Python $MinMajor.$MinMinor or newer is required but was not found."
    exit 1
}

$pythonVersion = & $pythonBin '-c' 'import sys; print(sys.version.split()[0])'
Write-Info "Using Python: $pythonVersion ($pythonBin)"

$pipArgs = @('install')
if ($User) { $pipArgs += '--user' }
if ($Upgrade) { $pipArgs += '--upgrade' }

if ($Dev) {
    $target = if ($Ref) { $Ref } else { $DefaultRef }
    $target = $target -replace '^refs/heads/', ''
    Write-Info "Installing development version from $Repo @ $target"
    $pipArgs += "$Repo@$target"
} elseif ($Ref) {
    Write-Info "Installing $Package from PyPI with constraint $Ref"
    $pipArgs += "$Package==$Ref"
} else {
    Write-Info "Installing $Package from PyPI"
    $pipArgs += $Package
}

try {
    & $pythonBin @pipArgs
    if ($LASTEXITCODE -ne 0) {
        throw "pip exited with code $LASTEXITCODE"
    }
} catch {
    Write-Fail "pip install failed: $_"
    exit 1
}

Write-Ok "$Package installed."

if (-not $NoVerify) {
    $prpm = Get-Command prpm -ErrorAction SilentlyContinue
    if (-not $prpm) {
        if ($User) {
            Write-Fail "prpm not found on PATH. Add the user Scripts directory to your PATH and re-run."
        } else {
            Write-Fail "prpm not found on PATH. Check the install location reported by pip."
        }
        exit 1
    }

    Write-Info "Verifying installation..."
    try {
        & prpm --version
        Write-Ok "PRPM is ready. Run 'prpm --help' to get started."
    } catch {
        Write-Fail "prpm was installed but failed to run: $_"
        exit 1
    }
} else {
    Write-Info "Skipping verification (-NoVerify)."
}
