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

Write-Output "Building OpenSSL..."
Invoke-Msys2 "cd /$OpenSSLVersion && PATH=`"/mingw64/bin:`$PATH`" make -j`$(nproc)"
if ($Fips) {
    Invoke-Msys2 "cd /$OpenSSLVersion && PATH=`"/mingw64/bin:`$PATH`" make install_fips"
} else {
    Invoke-Msys2 "cd /$OpenSSLVersion && PATH=`"/mingw64/bin:`$PATH`" make install_sw install_ssldirs"
}

