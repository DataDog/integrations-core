[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string] $Msys2Path = "C:\msys64"
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

Write-Output "Installing dependencies..."
Invoke-Msys2 "pacman -S --noconfirm make mingw-w64-i686-gcc mingw-w64-x86_64-gcc"
