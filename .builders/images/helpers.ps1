# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Approve-File() {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Hash
    )
    $dlhash = (Get-FileHash -Algorithm sha256 $Path).Hash.ToLower()
    if ($dlhash -ne $Hash) {
        Write-Host
        Write-Host '/!\ Hash mismatch'
        Write-Host got $dlhash`,` expected $Hash
        Write-Host
        exit 1
    }
}

function Get-RemoteFile() {
    param(
        [Parameter(Mandatory = $true)][string] $Uri,
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $false)][string] $Hash
    )
    Invoke-WebRequest -Uri $Uri -OutFile $Path
    if ($PSBoundParameters.ContainsKey("Hash")){
        Approve-File -Path $Path -Hash $Hash
    }
}

function Add-ToPath() {
    param(
        [Parameter(Mandatory = $true)][string] $Append
    )
    $Env:Path="$Env:Path;$Append"
    $oldPath=[Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
    $target="$oldPath;$Append"
    [Environment]::SetEnvironmentVariable("Path", $target, [System.EnvironmentVariableTarget]::User)
}
