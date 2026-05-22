$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

. C:\helpers.ps1

# Source of truth is the Dockerfile ENV; build_wheels.py asserts this stays
# in lockstep with the confluent-kafka pin in agent_requirements.in.
$kafka_version = $Env:CONFLUENT_KAFKA_VERSION
if (-not $kafka_version) {
    throw "CONFLUENT_KAFKA_VERSION env is not set"
}
Write-Host "Will build librdkafka $kafka_version"

# Download and unpack the source
Get-RemoteFile `
  -Uri "https://github.com/confluentinc/librdkafka/archive/refs/tags/v${kafka_version}.tar.gz" `
  -Path "librdkafka-${kafka_version}.tar.gz" `
  -Hash '14972092e4115f6e99f798a7cb420cbf6daa0c73502b3c52ae42fb5b418eea8f'
7z x "librdkafka-${kafka_version}.tar.gz" -o"C:\"
7z x "C:\librdkafka-${kafka_version}.tar" -o"C:\librdkafka"
Remove-Item "librdkafka-${kafka_version}.tar.gz"

# Build librdkafka
# Based on this job from upstream:
# https://github.com/confluentinc/librdkafka/blob/cb8c19c43011b66c4b08b25e5150455a247e1ff3/.semaphore/semaphore.yml#L265
# Install vcpkg
$triplet = "x64-windows"
$vcpkg_dir = "C:\vcpkg"
$librdkafka_dir = "C:\librdkafka\librdkafka-${kafka_version}"
$desired_commit = "3e797c57a635d3ce8f3473ef344ea44c09c246c8"

# Clone and configure vcpkg
if (-Not (Test-Path -Path "$vcpkg_dir\.git")) {
    git clone https://github.com/Microsoft/vcpkg.git $vcpkg_dir
}

Set-Location $vcpkg_dir
git checkout $desired_commit

Write-Host "Bootstrapping vcpkg..."
.\bootstrap-vcpkg.bat

# Get deps
Set-Location "$librdkafka_dir"
# Patch the the vcpkg manifest to to override the OpenSSL version and CURL version
python C:\update_librdkafka_manifest.py vcpkg.json --set-version openssl:${Env:OPENSSL_VERSION} --set-version curl:${Env:CURL_VERSION}

C:\vcpkg\vcpkg integrate install
C:\vcpkg\vcpkg --feature-flags=versions install --triplet $triplet
# Build
& .\win32\msbuild.ps1 -platform x64

# Copy outputs to where they can be found
# This is partially inspired by
# https://github.com/confluentinc/librdkafka/blob/cb8c19c43011b66c4b08b25e5150455a247e1ff3/win32/package-zip.ps1
$toolset = "v142"
$platform = "x64"
$config = "Release"
$srcdir = "win32\outdir\${toolset}\${platform}\$config"
$bindir = "C:\bin"
$libdir = "C:\lib"
$includedir = "C:\include"

Copy-Item "${srcdir}\librdkafka.dll","${srcdir}\librdkafkacpp.dll",
"${srcdir}\libcrypto-3-x64.dll","${srcdir}\libssl-3-x64.dll",
"${srcdir}\zlib1.dll","${srcdir}\zstd.dll","${srcdir}\libcurl.dll" -Destination $bindir
Copy-Item "${srcdir}\librdkafka.lib","${srcdir}\librdkafkacpp.lib" -Destination $libdir

New-Item -Path $includedir\librdkafka -ItemType Directory
Copy-Item -Path ".\src\*" -Filter *.h -Destination $includedir\librdkafka

# Free disk space before the layer is committed. The build outputs we ship live
# in C:\bin, C:\lib, and C:\include. Everything else is intermediate. This must
# happen in the same RUN as the build — a later layer cannot shrink bytes that
# are already committed to an earlier one.
Set-Location C:\
Remove-Item -Recurse -Force C:\vcpkg -ErrorAction Continue
Remove-Item -Recurse -Force C:\librdkafka -ErrorAction Continue
Remove-Item -Force "C:\librdkafka-${kafka_version}.tar" -ErrorAction Continue
