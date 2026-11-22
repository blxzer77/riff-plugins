# Installs a released `riff` binary on Windows x86_64.
#
#   install.ps1 [-Version 0.1.0] [-InstallDir <dir>]
#
# RIFF_VERSION and RIFF_REPO (default blxzer77/riff-plugins) override the
# defaults. The archive is checked against the release's SHA256SUMS before
# anything is installed.
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Version,
    [string]$InstallDir = (Join-Path $HOME '.local\bin')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 may not offer TLS 1.2 by default; GitHub requires it.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$repo = if ($env:RIFF_REPO) { $env:RIFF_REPO } else { 'blxzer77/riff-plugins' }
if (-not $Version -and $env:RIFF_VERSION) {
    $Version = $env:RIFF_VERSION
}

if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne [System.Runtime.InteropServices.Architecture]::X64) {
    throw 'install.ps1 currently supports Windows x86_64 only.'
}

if (-not $Version) {
    # The repository also tags its skills (plain vX.Y.Z), so the newest release
    # overall is not necessarily a riff release: take the newest riff-v one
    # that is not a pre-release.
    $releases = Invoke-RestMethod -Headers @{ Accept = 'application/vnd.github+json' } `
        -Uri "https://api.github.com/repos/$repo/releases?per_page=100"
    $latest = @($releases) |
        Where-Object { $_.tag_name -match '^riff-v[0-9]+\.[0-9]+\.[0-9]+$' } |
        Select-Object -First 1
    if (-not $latest) {
        throw "No riff release found in $repo; pass a version, for example: install.ps1 0.1.0"
    }
    $tag = $latest.tag_name
} elseif ($Version.StartsWith('riff-v')) {
    $tag = $Version
} else {
    $tag = "riff-v$Version"
}

if ($tag -notmatch '^riff-v[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$') {
    throw "Invalid riff release tag: $tag"
}

$asset = "$tag-windows-x86_64.zip"
$baseUrl = "https://github.com/$repo/releases/download/$tag"
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("riff-install-" + [guid]::NewGuid())
$archive = Join-Path $tempDir $asset
$sums = Join-Path $tempDir 'SHA256SUMS'
$unpacked = Join-Path $tempDir 'unpacked'

try {
    New-Item -ItemType Directory -Force $tempDir | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/$asset" -OutFile $archive
    Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/SHA256SUMS" -OutFile $sums

    $escapedAsset = [regex]::Escape($asset)
    $sumLine = Get-Content $sums | Where-Object { $_ -match "\s+$escapedAsset$" } | Select-Object -First 1
    if (-not $sumLine) {
        throw "SHA256SUMS has no entry for $asset"
    }
    $expected = ($sumLine -split '\s+')[0].ToLowerInvariant()
    if ($expected -notmatch '^[0-9a-f]{64}$') {
        throw "SHA256SUMS has an invalid digest for $asset"
    }
    $actual = (Get-FileHash -Algorithm SHA256 -Path $archive).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        throw "SHA256 mismatch for $asset"
    }

    Expand-Archive -Path $archive -DestinationPath $unpacked
    $unpackedExe = Join-Path $unpacked 'riff.exe'
    if (-not (Test-Path $unpackedExe -PathType Leaf)) {
        throw "Archive has no riff.exe"
    }
    New-Item -ItemType Directory -Force $InstallDir | Out-Null
    Copy-Item $unpackedExe (Join-Path $InstallDir 'riff.exe') -Force
    Write-Host "Installed riff $($tag.Substring('riff-v'.Length)) to $(Join-Path $InstallDir 'riff.exe')"

    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $pathEntries = if ($userPath) { $userPath -split ';' } else { @() }
    if ($pathEntries -notcontains $InstallDir) {
        Write-Host "Add the install directory to your user PATH with:"
        Write-Host "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';$InstallDir', 'User')"
        Write-Host 'Open a new PowerShell session after changing PATH.'
    }
    Write-Host 'Next: riff init, then riff web doctor.'
    Write-Host 'Global instructions for every agent: riff prompt install, then fill in the file it names.'
} finally {
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}
