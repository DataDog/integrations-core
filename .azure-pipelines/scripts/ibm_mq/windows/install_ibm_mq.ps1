$ErrorActionPreference = 'Stop'

function DownloadFile{
    param(
        [Parameter(Mandatory = $true)][string] $TargetFile,
        [Parameter(Mandatory = $true)][string] $SourceURL
    )
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    Write-Output "Downloading $SourceUrl to $TargetFile"
    (New-Object System.Net.WebClient).DownloadFile($SourceURL, $TargetFile)
}

function DownloadAndExpandTo{
    param(
        [Parameter(Mandatory = $true)][string] $TargetDir,
        [Parameter(Mandatory = $true)][string] $SourceURL
    )
    $tmpOutFile = New-TemporaryFile

    DownloadFile -TargetFile $tmpOutFile -SourceURL $SourceURL

    If(!(Test-Path $TargetDir))
    {
        md $TargetDir
    }

    Write-Output "Expanding $tmpOutFile to $TargetDir"
    Start-Process "7z" -ArgumentList "x -o${TargetDir} $tmpOutFile" -Wait
    Remove-Item $tmpOutFile
}

$Version "9.2.2.0"
$source = "https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/redist/$($Version)-IBM-MQC-Redist-Win64.zip"
$target = "c:\ibm_mq"

DownloadAndExpandTo -TargetDir $target -SourceURL $source
