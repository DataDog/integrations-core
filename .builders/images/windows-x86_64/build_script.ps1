$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

. C:\helpers.ps1

# The librdkafka version needs to stay in sync with the confluent-kafka version,
# thus we extract the version from the requirements file
$kafka_version = Get-Content 'C:\mnt\requirements.in' | perl -nE 'say/^\D*(\d+\.\d+\.\d+)\D*$/ if /confluent-kafka==/'
Write-Host "Will build librdkafka $kafka_version"

# Download and unpack the source
Get-RemoteFile `
  -Uri "https://github.com/confluentinc/librdkafka/archive/refs/tags/v${kafka_version}.tar.gz" `
  -Path "librdkafka-${kafka_version}.tar.gz" `
  -Hash '5bd1c46f63265f31c6bfcedcde78703f77d28238eadf23821c2b43fc30be3e25'
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
# We set the desired tag to the latest release tag to ensure that we are building with the latest stable version.
# The desired tag should be updated periodically or when critical fixes or features are released.
$desired_tag = "2024.12.16"

# Clone and configure vcpkg
if (-Not (Test-Path -Path "$vcpkg_dir\.git")) {
    git clone https://github.com/Microsoft/vcpkg.git $vcpkg_dir
}

Set-Location $vcpkg_dir
git checkout $desired_tag

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

