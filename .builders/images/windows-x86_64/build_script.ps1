$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

. C:\helpers.ps1

# The librdkafka version needs to stay in sync with the confluent-kafka version,
# thus we extract the version from the requirements file
$kafka_version = Get-Content 'C:\mnt\requirements.in' | perl -nE 'say/^\D*(\d+\.\d+\.\d+)\D*$/ if /confluent-kafka==/'
Write-Host "Will build librdkafka $kafka_version"

# If the resolve-build-deps workflow mounted a populated native cache, restore
# the librdkafka artifacts and skip the vcpkg + msbuild compile. The cache key
# on the workflow side already accounts for everything that can change the
# binary (confluent-kafka pin, Dockerfile env values, this script), so a
# present cache is by definition compatible with this build.
$native_cache = "C:\native_cache"
$cache_marker = "$native_cache\bin\librdkafka.dll"
if (Test-Path -Path $cache_marker) {
    Write-Host "Restoring librdkafka artifacts from $native_cache"
    Copy-Item -Path "$native_cache\bin\*" -Destination "C:\bin" -Recurse -Force
    Copy-Item -Path "$native_cache\lib\*" -Destination "C:\lib" -Recurse -Force
    if (-Not (Test-Path -Path "C:\include\librdkafka")) {
        New-Item -Path "C:\include\librdkafka" -ItemType Directory | Out-Null
    }
    Copy-Item -Path "$native_cache\include\librdkafka\*" -Destination "C:\include\librdkafka" -Recurse -Force
    Write-Host "Restored librdkafka from cache; skipping vcpkg + msbuild compile."
    exit 0
}

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

# Populate the native cache mount (if mounted) so actions/cache can persist the
# artifacts for subsequent runs that hit on the same inputs hash.
if (Test-Path -Path $native_cache) {
    Write-Host "Populating native cache at $native_cache"
    New-Item -Path "$native_cache\bin" -ItemType Directory -Force | Out-Null
    New-Item -Path "$native_cache\lib" -ItemType Directory -Force | Out-Null
    New-Item -Path "$native_cache\include\librdkafka" -ItemType Directory -Force | Out-Null
    Copy-Item -Path "$bindir\*" -Destination "$native_cache\bin" -Recurse -Force
    Copy-Item -Path "$libdir\*" -Destination "$native_cache\lib" -Recurse -Force
    Copy-Item -Path "$includedir\librdkafka\*" -Destination "$native_cache\include\librdkafka" -Recurse -Force
}

