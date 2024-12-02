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
    Copy-Item -Force -Path "$Msys2Path\ssl_out_fips\lib64\ossl-modules\fips.dll" -Destination .\installed
    Write-Output "Copying fipsmodule.cnf..."
    Copy-Item -Force -Path "$Msys2Path\ssl_out_fips\ssl\fipsmodule.cnf" -Destination .\installed
    Write-Output "Copying openssl.cnf..."
    Copy-Item -Force -Path "$Msys2Path\ssl_out\ssl\openssl.cnf" -Destination .\installed
    Write-Output "Copying openssl.exe"
    Copy-Item -Force -Path "$Msys2Path\ssl_out\bin\openssl.exe" -Destination .\installed

    # Delete .pdb files from installed
    Get-ChildItem .\installed -Filter *.pdb -Recurse | Remove-Item -Force

    Write-Output "Compressing Python..."
    Compress-Archive -Path .\installed\* -DestinationPath .\python.zip -Force
    Write-Output "Python zip created at: $PythonRepoPath\python.zip"

    Write-Output "Creating SHA-256 checksum file..."
    $sha256 = Get-FileHash -Path .\python.zip -Algorithm SHA256
    $sha256.Hash | Out-File -FilePath .\python.zip.sha256
    Write-Output "SHA-256 checksum file created at: .\python.zip.sha256"
} finally {
    Pop-Location
}