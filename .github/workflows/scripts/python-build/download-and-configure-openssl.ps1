[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string] $Msys2Path = "C:\msys64",

    [Parameter(Mandatory=$true)]
    [string] $OpenSSLVersion = "openssl-3.0.15",

    [switch] $Fips = $false
)

Set-StrictMode -Version 3
$ErrorActionPreference = "Stop"

$Msys2Bin = "$Msys2Path\usr\bin\bash.exe"

if (!(Test-Path $Msys2Bin)) {
    throw "MSYS2 not found at path: $Msys2Path"
}

function Invoke-Msys2 {
    param (
        [string] $Command
    )
    & $Msys2Bin -e -l -c $Command
    if (!$?) { throw "Command failed: $Command" }
}

$OutDir = "/ssl_out"
if ($Fips) {
    $OutDir = "/ssl_out_fips"
}

if (Test-Path $Msys2Bin/$OpenSSLVersion) {
    Remove-Item -Recurse -Force $Msys2Bin/$OpenSSLVersion
}

"Cloning OpenSSL repository..."
git clone --branch $OpenSSLVersion --depth 1 https://github.com/openssl/openssl.git "$Msys2Path/$OpenSSLVersion"
if (!$?) { throw "Failed to clone OpenSSL repository" }

Invoke-Msys2 'echo "pwd: `$(pwd) "'
Write-Output "Configuring OpenSSL..."
$configure_command = "cd $OpenSSLVersion && PATH=`"/mingw64/bin:`$PATH`" perl ./Configure --prefix=$OutDir/ mingw64"
if ($Fips) {
    $configure_command += " enable-fips"
}
Invoke-Msys2 $configure_command
