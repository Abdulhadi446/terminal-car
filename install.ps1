param(
    [switch]$Silent = $false
)

$ErrorActionPreference = "Stop"

function Info($m) { if (-not $Silent) { Write-Host ("install: $m") } }
function Fail($m) { Write-Host ("install: error: $m") -ForegroundColor Red; exit 1 }

# Resolve where this script lives
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$SourceDir = $ScriptDir

# Check if play.py and terminal_car exist locally
$HasLocal = (Test-Path (Join-Path $SourceDir "play.py")) -and (Test-Path (Join-Path $SourceDir "terminal_car"))

if (-not $HasLocal) {
    Info "Local files not found, cloning repository..."
    $tmp = Join-Path $env:TEMP "terminal-car-clone"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    try {
        git clone --depth 1 "https://github.com/Abdulhadi446/terminal-car.git" $tmp
        $SourceDir = $tmp
    } catch {
        Fail "Git is required to download terminal-car. Please clone the repository manually."
    }
}

# Locate Python
$PythonExe = $null
foreach ($candidate in @("python", "py", "python3")) {
    try {
        $p = Get-Command $candidate -ErrorAction Stop
        $PythonExe = $p.Source
        break
    } catch { }
}
if (-not $PythonExe) {
    Fail "Python 3 is not installed or not in PATH. Install from python.org and reopen PowerShell."
}

# Verify curses (Windows standard Python needs windows-curses)
$cursesOk = & $PythonExe -c "import sys,curses; sys.exit(0)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Info "Standard Windows Python does not include curses."
    Info "To run natively in PowerShell, run:  $PythonExe -m pip install windows-curses"
    Info "Alternatively, run inside WSL (Windows Subsystem for Linux) for native curses support."
}

$InstallDir = Join-Path $env:LOCALAPPDATA "terminal-car"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Info "Copying files to $InstallDir..."
Copy-Item -Force (Join-Path $SourceDir "play.py") (Join-Path $InstallDir "play.py")
if (Test-Path (Join-Path $InstallDir "terminal_car")) {
    Remove-Item -Recurse -Force (Join-Path $InstallDir "terminal_car")
}
Copy-Item -Recurse -Force (Join-Path $SourceDir "terminal_car") (Join-Path $InstallDir "terminal_car")

# Shims for `car` and `terminal-car`
$ShimContent = "@echo off`r`n`"$PythonExe`" `"%~dp0play.py`" %*`r`n"
Set-Content -Path (Join-Path $InstallDir "car.cmd") -Value $ShimContent -Encoding ascii
Set-Content -Path (Join-Path $InstallDir "terminal-car.cmd") -Value $ShimContent -Encoding ascii

# Add to user PATH if missing
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$has = $false
foreach ($p in ($userPath -split ';')) {
    if ($p -ieq $InstallDir) { $has = $true; break }
}
if (-not $has) {
    $newPath = "$InstallDir;$userPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Info "Added $InstallDir to user PATH (open a new terminal)"
}

# Start Menu shortcut
try {
    $shell = New-Object -ComObject WScript.Shell
    $programs = [Environment]::GetFolderPath('StartMenu') + "\Programs"
    if (-not (Test-Path $programs)) { New-Item -ItemType Directory -Force -Path $programs | Out-Null }
    $lnk = $shell.CreateShortcut("$programs\Terminal Rush.lnk")
    $lnk.TargetPath = $PythonExe
    $lnk.Arguments = "`"$InstallDir\play.py`""
    $lnk.WorkingDirectory = $InstallDir
    $lnk.WindowStyle = 1
    $lnk.Description = "Endless retro highway survival in your terminal"
    $lnk.Save()
    Info "Created Start Menu shortcut 'Terminal Rush'"
} catch {
    Info "Could not create Start Menu shortcut: $($_.Exception.Message)"
}

Write-Host @"

🏎️  Terminal Rush is installed!

Run the game from any new PowerShell or CMD prompt with:
    car

(Or 'terminal-car')

Note for Windows users:
If 'curses' is missing, install it with:
    pip install windows-curses
Or play seamlessly via WSL!

"@
