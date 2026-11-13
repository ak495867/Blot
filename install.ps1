
$ErrorActionPreference = "Stop"

$RepoZip = "https://github.com/ak495867/Blot/archive/refs/heads/master.zip"
$InstallDir = Join-Path $env:LOCALAPPDATA "Blot"
$VenvPython = Join-Path $InstallDir "Scripts\python.exe"
$ScriptsDir = Join-Path $InstallDir "Scripts"

$PythonCommand = Get-Command py -ErrorAction SilentlyContinue

if ($PythonCommand) {
    & $PythonCommand.Source -3 --version
    if ($LASTEXITCODE -eq 0) {
        $PythonArgs = @("-3")
    } else {
        $PythonCommand = $null
    }
}

if (-not $PythonCommand) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        throw "Python 3.9+ is required. Install it from https://www.python.org/downloads/"
    }

    $PythonArgs = @()
    & $PythonCommand.Source --version

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to run Python."
    }
}

$VersionOutput = & $PythonCommand.Source @PythonArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

if ($LASTEXITCODE -ne 0) {
    throw "Unable to determine Python version."
}

$Version = [version]$VersionOutput

if ($Version -lt [version]"3.9") {
    throw "Blot requires Python 3.9 or newer."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

if (-not (Test-Path $VenvPython)) {
    & $PythonCommand.Source @PythonArgs -m venv $InstallDir

    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Blot environment."
    }
}

& $VenvPython -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    throw "Could not upgrade pip."
}

& $VenvPython -m pip install --upgrade $RepoZip

if ($LASTEXITCODE -ne 0) {
    throw "Blot installation failed."
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathEntries = @($UserPath -split ";" | Where-Object { $_ })

if ($PathEntries -notcontains $ScriptsDir) {
    $NewUserPath = (@($PathEntries) + $ScriptsDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
}

if (($env:Path -split ";") -notcontains $ScriptsDir) {
    $env:Path = "$ScriptsDir;$env:Path"
}

& $VenvPython -m pip show blot

if ($LASTEXITCODE -ne 0) {
    throw "Blot installation verification failed."
}

Write-Host ""
Write-Host "Blot installed successfully."
Write-Host "Run: blot --help"
