# Modified from https://github.com/DataDog/datadog-agent/blob/main/tasks/winbuildscripts/Generate-Pyzip.ps1 to support using local installers instead of downloading them from FTP.


param (
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$false)][string]$md5sum,
    [Parameter(Mandatory=$false)][string]$OutDir,
    [Parameter(Mandatory=$false)][string] $InputFile
)
# https://www.python.org/ftp/python/2.7.17/python-2.7.17.amd64.msi
# https://www.python.org/ftp/python/2.7.17/python-2.7.17.msi

# https://www.python.org/ftp/python/3.8.0/python-3.8.0-amd64.exe
# https://www.python.org/ftp/python/3.8.0/python-3.8.0.exe

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$maj, $min, $patch = $Version.Split(".")
Write-Host -ForegroundColor Green "Installing Python version $maj $min $patch"

function Get-Installer-Url {
    param (
        [string]$version
    )

    $maj, $min, $patch = $Version.Split(".")
    if ($maj -eq "2") {
        $url = "https://www.python.org/ftp/python/$Version/python-$Version.amd64.msi"
    } elseif ($maj -eq "3"){
        $url = "https://www.python.org/ftp/python/$Version/python-$Version-amd64.exe"
    } else {
        Write-Host -ForegroundColor Red "Unknown major version $Maj.  I don't know how to do this"
        exit 1
    }

    return $url
}

$outzip = "python-windows-$Version-amd64.zip"
$url = Get-Installer-Url -version $version
$dlfilename = ($url -split '/')[-1]
$dlfullpath = "$Env:TEMP\$dlfilename"

function Get-Installer {
    param  (
        [string]$url,
        [string]$dlfullpath,
        [string]$md5sum
    )

    Write-Host -ForegroundColor Green "Downloading file from $url..."
    (New-Object System.Net.WebClient).DownloadFile($url, $dlfullpath)
    Write-Host -ForegroundColor Green "... Done."

    ## do md5 check if we have it
    if ($md5sum){
        $downloadedhash = (Get-FileHash -Algorithm md5 $dlfullpath).Hash.ToLower()
        if($downloadedhash -ne $md5sum.ToLower()){
            Write-Host -ForegroundColor Red "MD5Sums Don't Match"
            exit -1
        }
        Write-Host -ForegroundColor Green "Matched MD5 Sums"
    } else {
        Write-Host -ForegroundColor Yellow "MD5 Hash not supplied, not comparing"
    }
}

function Uninstall-Python {
    param  (
        [string]$installedPythonVersion,
        [string]$dlfullpath,
        [string]$md5sum
    )
    if ($InputFile) {
        $dlfullpath = Resolve-Path -Path $InputFile
    } else {
        Get-Installer -url (Get-Installer-Url -version $installedPythonVersion) -dlfullpath $dlfullpath -md5sum $md5sum
    }    
    Write-Host -ForegroundColor Yellow "Uninstalling Python $installedPythonVersion"
    $p = Start-Process $dlfullpath -ArgumentList "/quiet /uninstall" -Wait -Passthru
    if ($p.ExitCode -ne 0) {
        Write-Host -ForegroundColor Red ("Failed to uninstall Python, exit code 0x{0:X}" -f $p.ExitCode)
        exit 1
    }
    Remove-Item $dlfullpath
}

# Where to install the target python
$pythonRoot = "c:\pythonroot"

if($maj -eq "2") {
    if ($InputFile) {
        throw "The Infile Parameter is not supported for Python 2"
    }
    Get-Installer -url $url -dlfullpath $dlfullpath -md5sum $md5sum
    Write-Host -ForegroundColor Green "Installing package in container..."
    $p = Start-Process msiexec -ArgumentList "/q /i $dlfullpath TARGETDIR=""$pythonRoot"" ADDLOCAL=DefaultFeature,Tools,TclTk,Testsuite" -Wait -Passthru

    if ($p.ExitCode -ne 0) {
        Write-Host -ForegroundColor Red ("Failed to install Python, exit code 0x{0:X}" -f $p.ExitCode)
        exit 1
    }
}
elseif ($maj -eq "3") {
    $Env:PATH="$Env:PATH;c:\tools\msys64\mingw64\bin"

    try {
        $installedPythonVersion = python --version
        $installedPythonVersion = [regex]::match($installedPythonVersion,'Python (\d.\d.\d)').Groups[1].Value
        $installedMaj, $installedMin, $installedPatch = $installedPythonVersion.Split(".")

        Write-Host -ForegroundColor Green "Detected installed Python $installedMaj $installedMin $installedPatch"

        if ($installedMaj -ne "3") {
            Write-Host -ForegroundColor Red "Invalid Python $installedPythonVersion installation detected"
            exit 1
        }
        # Python is already installed in the buildimage, but is the wrong version uninstall it
        Uninstall-Python -installedPythonVersion $installedPythonVersion -dlfullpath $dlfullpath -md5sum $null
    }
    catch {
        # Python command not found
    }

    if ($InputFile) {
        $dlfullpath = Resolve-Path -Path $InputFile
    } else {
        Get-Installer -url $url -dlfullpath $dlfullpath -md5sum $md5sum
    }    
    Write-Host -ForegroundColor Green "Installing Python $Version"
    $p = Start-Process $dlfullpath -ArgumentList "/quiet /log C:\mnt\install.log DefaultJustForMeTargetDir=""$pythonRoot"" DefaultAllUsersTargetDir=""$pythonRoot"" AssociateFiles=0 Include_doc=0 Include_launcher=0 Include_pip=0 Include_tcltk=0" -Wait -Passthru
    if ($p.ExitCode -ne 0) {
        Write-Host -ForegroundColor Red ("Failed to install Python, exit code 0x{0:X}" -f $p.ExitCode)
        exit 1
    }

    if (Test-Path $pythonRoot\vcruntime*.dll) {
        Write-Host -ForegroundColor Green "NOT deleting included cruntime"
    }
    Write-Host -ForegroundColor Green "Generating import library"
    
    Push-Location .
    Set-Location "$pythonRoot\libs"
    
    # Check if python3$($min).dll exists, if not fall back to python3.dll
    if (Test-Path ..\python3$($min).dll) {
        $dllName = "python3$($min).dll"
        $defName = "python3$($min).def"
        $libName = "libpython3$($min).a"
    } elseif (Test-Path ..\python3.dll) {
        $dllName = "python3.dll"
        $defName = "python3.def"
        $libName = "libpython3.a"
    } else {
        Write-Error "Neither python3$($min).dll nor python3.dll found."
        Pop-Location
        exit 1
    }
    
    # Proceed with the respective .dll file
    gendef ..\$dllName
    dlltool --dllname $dllName --def $defName --output-lib $libName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate import library"
        Pop-Location
        exit 1
    }
    
    Pop-Location
}
Write-Host -ForegroundColor Green "... Done."

Write-Host -ForegroundColor Green "Zipping results..."
& 7z a -r c:\tmp\$outzip $pythonRoot\*.*
Write-Host -ForegroundColor Green "... Done."

# No need to clean up, this is designed to run in a container that is going to be short-lived

if($OutDir -and (Test-Path $OutDir)){
    Write-Host -ForegroundColor green "Copying zip c:\tmp\$($outzip) to $OutDir"
    Copy-Item -Path "c:\tmp\$($outzip)" -Destination "$($OutDir)"
    Write-Host -ForegroundColor Green "... Done."
}
$shasum = (Get-FileHash "c:\tmp\$($outzip)").Hash.ToLower()
Write-Host -ForegroundColor Green "SHA256 Sum of resulting zip: $shasum"
