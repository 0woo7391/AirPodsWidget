param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDir,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$source = (Resolve-Path -LiteralPath $SourceDir).Path
$output = [System.IO.Path]::GetFullPath($OutputPath)
$staging = Join-Path (Get-Location) "build\msix-staging"
$manifest = Join-Path (Get-Location) "packaging\AppxManifest.xml"
$iconPath = Join-Path $source "_internal\assets\app.ico"

if (-not (Test-Path -LiteralPath $manifest)) {
    throw "MSIX manifest not found: $manifest"
}
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Application icon not found: $iconPath"
}

$makeAppx = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter "makeappx.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "\\x64\\makeappx\.exe$" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $makeAppx) {
    throw "Windows SDK makeappx.exe (x64) was not found."
}

Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $staging -Force | Out-Null
Copy-Item -Path (Join-Path $source "*") -Destination $staging -Recurse -Force

$assetDir = Join-Path $staging "Assets"
New-Item -ItemType Directory -Path $assetDir -Force | Out-Null
$logoPath = Join-Path $assetDir "logo.png"

Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::new($iconPath)
$bitmap = [System.Drawing.Bitmap]::new(256, 256, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.DrawIcon($icon, 0, 0)
    $bitmap.Save($logoPath, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $icon.Dispose()
}

Copy-Item -LiteralPath $manifest -Destination (Join-Path $staging "AppxManifest.xml") -Force
Remove-Item -LiteralPath $output -Force -ErrorAction SilentlyContinue
$makeAppxOutput = & $makeAppx.FullName pack /d $staging /p $output /o 2>&1
if ($LASTEXITCODE -ne 0) {
    $makeAppxOutput | Write-Host
    throw "makeappx.exe failed with exit code $LASTEXITCODE"
}
Write-Host "완료: $output (unsigned MSIX; package identity + globalMediaControl 포함)"
