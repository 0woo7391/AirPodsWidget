$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Administrator permission is required. Requesting UAC elevation..."
    $elevatedArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ('"' + $PSCommandPath + '"')
    )
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $elevatedArgs -WorkingDirectory $PSScriptRoot -Wait
    exit 0
}

$msixPath = Join-Path $PSScriptRoot "AirPodsWidget.msix"
if (-not (Test-Path -LiteralPath $msixPath)) {
    throw "AirPodsWidget.msix not found. Run .\build_windows.ps1 first."
}

$signTool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $signTool) {
    throw "Windows SDK signtool.exe (x64) was not found."
}

# This is intentionally performed only by this explicit installer. It creates
# a local development certificate, not a public code-signing identity.
$subject = "CN=AirPodsWidget Dev"
$cert = New-SelfSignedCertificate `
    -Type Custom `
    -Subject $subject `
    -KeyUsage DigitalSignature `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}") `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -FriendlyName "AirPodsWidget local package certificate"

$passwordText = [guid]::NewGuid().ToString("N")
$password = ConvertTo-SecureString -String $passwordText -Force -AsPlainText
$tempRoot = Join-Path $env:TEMP ("AirPodsWidget-install-" + [guid]::NewGuid().ToString("N"))
$pfxPath = Join-Path $tempRoot "AirPodsWidget.pfx"
$cerPath = Join-Path $tempRoot "AirPodsWidget.cer"
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password | Out-Null
    Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null
    # AppX validation checks the complete chain. Because this local
    # development certificate is self-signed, Windows must trust it in the
    # machine-level stores used by AppX deployment. Only the public .cer is
    # imported; the private signing key remains temporary and is deleted below.
    Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
    Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null

    & $signTool.FullName sign /fd SHA256 /a /f $pfxPath /p $passwordText $msixPath
    if ($LASTEXITCODE -ne 0) {
        throw "signtool.exe failed with exit code $LASTEXITCODE"
    }
    Add-AppxPackage -Path $msixPath -ForceUpdateFromAnyVersion
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath ("Cert:\CurrentUser\My\" + $cert.Thumbprint) -Force -ErrorAction SilentlyContinue
}

$package = Get-AppxPackage -Name "AirPodsWidget" | Select-Object -First 1
if ($package) {
    Write-Host "Installation complete. Launch AirPodsWidget from the Start menu."
    Start-Process explorer.exe ("shell:AppsFolder\" + $package.PackageFamilyName + "!AirPodsWidget")
}
