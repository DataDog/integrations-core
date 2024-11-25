[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string] $PythonRepoPath = "C:\path\to\cpython",
    [switch] $Pgo = $false
)

Set-StrictMode -Version 3
$ErrorActionPreference = "Stop"

if ($Pgo) {
    Write-Output "Building Python with PGO..."
    & "$PythonRepoPath\PCBuild\build.bat" --pgo
} else {
    Write-Output "Building Python..."
    & "$PythonRepoPath\PCBuild\build.bat"
}
if (!$?) { throw "Python build failed" }