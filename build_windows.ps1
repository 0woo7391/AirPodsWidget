$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$runningApp = Get-Process -Name "AirPodsWidget" -ErrorAction SilentlyContinue
if ($runningApp) {
    throw "AirPodsWidget.exe가 실행 중입니다. 앱을 종료한 뒤 다시 빌드하세요. 기존 실행 파일은 변경하지 않았습니다."
}

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    & py -3.11 -c "import sys" *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonCommand = "py"
        $pythonArguments = @("-3.11")
    } else {
        $pythonLauncher = $null
    }
}

if (-not $pythonLauncher -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c "import sys; assert sys.version_info[:2] == (3, 11)" *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonCommand = "python"
        $pythonArguments = @()
    }
}

if (-not $pythonCommand) {
    throw "Python 3.11 x64 또는 python.exe를 찾을 수 없습니다."
}

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3, 11)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -Recurse -Force ".venv"
    }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $pythonCommand @pythonArguments -m venv .venv
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install -r requirements.txt

$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
& $venvPython -m pytest -q
& $venvPython tools\validate_project.py
& $venvPython tools\ui_spec_check.py
& $venvPython tools\qml_runtime_check.py

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
& $venvPython -m PyInstaller --clean --noconfirm AirPodsWidget.spec
Copy-Item README.md, BUILD_REPORT.md, UI_REDESIGN_SPEC.md, LICENSE, THIRD_PARTY_NOTICES.md -Destination "dist\AirPodsWidget"

$packageDir = Join-Path $PSScriptRoot "dist\AirPodsWidget"
$rootRuntimeDir = Join-Path $PSScriptRoot "_internal"
$msixPath = Join-Path $PSScriptRoot "AirPodsWidget.msix"

& (Join-Path $PSScriptRoot "tools\package_msix.ps1") -SourceDir $packageDir -OutputPath $msixPath
if ($LASTEXITCODE -ne 0) {
    throw "MSIX package creation failed."
}

# Keep one user-facing folder: the project root is also the portable app folder.
# dist\AirPodsWidget remains the PyInstaller staging output for this build.
Remove-Item -LiteralPath $rootRuntimeDir -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath (Join-Path $packageDir "_internal") -Destination $rootRuntimeDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $packageDir "AirPodsWidget.exe") -Destination $PSScriptRoot -Force
Write-Host "완료: $(Join-Path $PSScriptRoot 'AirPodsWidget.exe')"
