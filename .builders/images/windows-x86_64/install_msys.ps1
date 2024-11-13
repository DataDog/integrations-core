param (
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$Sha256
)
$InstallPath = "c:\tools"
<#
.SYNOPSIS
 Invoke-Msys2Shell  Runs the shell once to do first-time startup.  

.NOTES
Taken from chocolatey installer.
#>
function Invoke-Msys2Shell($Arguments) {
    if (![string]::IsNullOrWhiteSpace($Arguments)) { $Arguments += "; " }
    $Arguments += "ps -ef | grep '[?]' | awk '{print `$2}' | xargs -r kill"
    $basepath = Join-Path $InstallPath msys64

    $params = @{
        FilePath     = Join-Path $basepath msys2_shell.cmd
        NoNewWindow  = $true
        Wait         = $true
#        PassThru     = $true
        ArgumentList = "-defterm", "-no-start", "-c", "`"$Arguments`""
    }
    Write-Host "Invoking msys2 shell command:" $params.ArgumentList
    $p = Start-Process @params
    return $lastExitCode
}

# First mirror in the list is tried first
$mirrors = @(
    "https://mirror.umd.edu/msys2";
    "https://repo.msys2.org"
)

Write-Host  -ForegroundColor Green starting with MSYS
$out = "$($PSScriptRoot)\msys.tar.xz"
$msyszip = "distrib/x86_64/msys2-base-x86_64-$($Version).tar.xz"
$downloadSuccessful = $False
foreach($mirror in $mirrors) {
    Write-Host "Trying $mirror"
    try {
        Get-RemoteFile -RemoteFile $mirror/$msyszip -LocalFile $out -VerifyHash $Sha256
        $downloadSuccessful = $True
        break;
    } catch {
    }
}
if (!$downloadSuccessful) {
    throw "Failed to download MSYS2 from all mirrors"
}

# uncompress the tar-xz into a tar
$msystar = "msys.tar"
& 7z x $out
start-process 7z -ArgumentList "x -o$($InstallPath) $msystar" -Wait

Remove-Item $out
Remove-Item $msystar

## invoke the first-run shell
$mshell = Invoke-Msys2Shell
Write-Host -ForegroundColor Yellow "Invoke-Msys2Shell return code $mshell"
if ( $mshell -ne "0") {
    throw "Invoke MSYS returned $mshell"
}

# fails with autoconf errors
# ridk install 3
ridk enable
pacman -S --noconfirm autoconf autogen automake diffutils file gawk grep libtool m4 make patch pkg-config sed texinfo texinfo-tex wget mingw-w64-x86_64-gcc mingw-w64-x86_64-tools-git
If ($lastExitCode -ne "0") { 
    throw "ridk install 3 returned $lastExitCode" 
}

Remove-Item c:\*.zst
Set-InstalledVersionKey -Component "msys" -Keyname "version" -TargetValue $Version
Write-Host -ForegroundColor Green Done with MSYS