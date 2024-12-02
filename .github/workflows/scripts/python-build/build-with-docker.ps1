[CmdletBinding()]
param (
    [switch] $HasDockerStarted = $false
)

Set-StrictMode -Version 3
$ErrorActionPreference = "Stop"

if (!($HasDockerStarted)) {
    docker build -t nubtron/openssh-builder -f Dockerfile .
    if (!$?) { throw "Docker build failed" }

    docker run --rm --volume ${PSScriptRoot}:C:/mnt/ nubtron/openssh-builder pwsh "C:\mnt\Build-All.ps1" -HasDockerStarted
    if (!$?) { throw "Docker run failed" }
    exit
}

Copy-Item -Force -Path "C:\repos\cpython\python.zip" -Destination "C:\mnt\python.zip"

Write-Output "Done."