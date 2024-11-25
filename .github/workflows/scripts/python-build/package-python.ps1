[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string] $PythonRepoPath = "C:\path\to\cpython",

    [Parameter(Mandatory=$true)]
    [string] $Msys2Path = "C:\msys64"
)

Set-StrictMode -Version 3
$ErrorActionPreference = "Stop"

Push-Location
try {
    Set-Location $PythonRepoPath
    Write-Output "Setting up Python intall layout..."
    & .\python.bat -m PC.layout --preset-default --copy installed -v
    if (!$?) { throw "Python layout failed" }

    Write-Output "Copying fips.dll..."
    # C:\tools\msys64\ssl_out_fips\lib64\oss-modules\fips.dll
    Copy-Item -Force -Path "$Msys2Path\ssl_out_fips\lib64\ossl-modules\fips.dll" -Destination .\installed
    Write-Output "Copying fipsmodule.cnf..."
    Copy-Item -Force -Path "$Msys2Path\ssl_out_fips\ssl\fipsmodule.cnf" -Destination .\installed

    # Delete .pdb files from installed
    Get-ChildItem .\installed -Filter *.pdb | Remove-Item -Force

    # Compress installed into python.zip
    Write-Output "Compressing Python..."
    Compress-Archive -Path .\installed\* -DestinationPath .\python.zip -Force
    Write-Output "Python zip created at: $PythonRepoPath\python.zip"
} finally {
    Pop-Location
}