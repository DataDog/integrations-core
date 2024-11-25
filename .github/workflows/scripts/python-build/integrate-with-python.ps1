[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string] $Msys2Path = "C:\msys64",

    [Parameter(Mandatory=$true)]
    [string] $OpenSSLVersion = "openssl-3.0.15",

    [Parameter(Mandatory=$true)]
    [string] $PythonRepoPath = "C:\path\to\cpython"
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

# Updates the OpenSSL version in get_externals.bats
function Update-OpenSSLVersionInBatch {
    param (
        [string] $FilePath,
        [string] $NewVersion
    )
    if (!(Test-Path $FilePath)) {
        throw "Batch file not found at path: $FilePath"
    }

    $Content = Get-Content -Path $FilePath

    # Pattern to find the line with openssl version
    $Pattern = 'if NOT "%IncludeSSLSrc%"=="false" set libraries=%libraries%.*openssl-[\d\.]+'

    # Replace with the new version
    $UpdatedContent = $Content -replace $Pattern, "if NOT `%IncludeSSLSrc%`==`"false`" set libraries=%libraries%       $NewVersion"

    # Save the updated content back to the file
    Set-Content -Path $FilePath -Value $UpdatedContent

    Write-Output "Updated OpenSSL version in $FilePath to $NewVersion"
}

Write-Output "Integrating OpenSSL with Python..."

$ExternalsPath = "$PythonRepoPath\externals\$OpenSSLVersion"
$ExternalsBinPath = "$PythonRepoPath\externals\$OpenSSLVersion\amd64" -replace 'openssl-', 'openssl-bin-'
$SSLOutPath = "$Msys2Path\ssl_out"

Write-Output "External path: $ExternalsPath"
Write-Output "External bin path: $ExternalsBinPath"
Write-Output "SSL out path: $SSLOutPath"

Copy-Item -Recurse -Force -Path "$Msys2Path\$OpenSSLVersion" -Destination $ExternalsPath

New-Item -ItemType Directory -Force -Path $ExternalsBinPath | Out-Null


Write-Output "Copying $SSLOutPath\bin\libcrypto-3-x64.dll to $ExternalsBinPath"
Copy-Item -Force -Path "$SSLOutPath\bin\libcrypto-3-x64.dll" -Destination $ExternalsBinPath

Write-Output "Copying $SSLOutPath\bin\libssl-3-x64.dll to $ExternalsBinPath"
Copy-Item -Force -Path "$SSLOutPath\bin\libssl-3-x64.dll" -Destination $ExternalsBinPath
Copy-Item -Recurse -Force -Path "$SSLOutPath\include" -Destination $ExternalsBinPath

# Create dummy PDB files. Alternatively, we could remove the .pdb lines from openssl.props.
New-Item -ItemType File -Path "$ExternalsBinPath\libcrypto-3-x64.pdb"
New-Item -ItemType File -Path "$ExternalsBinPath\libssl-3-x64.pdb"

# Check for the existence of applink.c before moving it
$AppLinkPath = "$Msys2Path\$OpenSSLVersion\ms\applink.c"
if (!(Test-Path $AppLinkPath)) {
    throw "applink.c not found at path: $AppLinkPath. Ensure that the OpenSSL source is at $Msys2Path\$OpenSSLVersion"
}

Copy-Item -Force $AppLinkPath -Destination $ExternalsBinPath\include

Write-Output "Copying and renaming static helper libraries..."
Copy-Item -Force -Path "$SSLOutPath\lib64\libcrypto.dll.a" -Destination "$ExternalsBinPath\libcrypto.lib"
Copy-Item -Force -Path "$SSLOutPath\lib64\libssl.dll.a" -Destination "$ExternalsBinPath\libssl.lib"


Write-Output "Updating OpenSSL version in get_externals.bat..."
$GetExternalsPath = Join-Path -Path $PythonRepoPath -ChildPath "PCBuild\get_externals.bat"
Update-OpenSSLVersionInBatch -FilePath $GetExternalsPath -NewVersion $OpenSSLVersion

Write-Output "Updating openssl.props..."

$OpenSSLPropsPath = "$PythonRepoPath\PCBuild\openssl.props"
if (!(Test-Path $OpenSSLPropsPath)) {
    throw "openssl.props not found at path: $OpenSSLPropsPath"
}

$SearchString = "<_DLLSuffix Condition=`"`$(Platform) == 'ARM64'`">`$(_DLLSuffix)-arm64</_DLLSuffix>"
$InsertString = "`n    <_DLLSuffix Condition=`"`$(Platform) == 'x64'`">`$(_DLLSuffix)-x64</_DLLSuffix>"


if (!(Select-String -Path $OpenSSLPropsPath -Pattern $SearchString -SimpleMatch)) {
    throw "Could not find line above the insertion point in openssl.props"
}

$FileContent = Get-Content $OpenSSLPropsPath -Raw
$FileContent = $FileContent.Replace($SearchString, "$SearchString$InsertString")



Set-Content -Path $OpenSSLPropsPath -Value $FileContent