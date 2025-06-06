# escape=`

ARG BASE_IMAGE=mcr.microsoft.com/windows/servercore:ltsc2022
FROM ${BASE_IMAGE}

ARG SOURCE_DATE_EPOCH
ARG DD_TARGET_ARCH=x64

ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}
ENV DD_TARGET_ARCH=${DD_TARGET_ARCH}

SHELL ["cmd", "/S", "/C"]

# https://learn.microsoft.com/en-us/visualstudio/install/build-tools-container#create-and-build-the-dockerfile
# https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools
RUN curl -SL --output vs_buildtools.exe https://aka.ms/vs/17/release/vs_buildtools.exe `
 && (start /w vs_buildtools.exe --quiet --wait --norestart --nocache `
     --installPath "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools" `
     --add Microsoft.VisualStudio.Component.VC.140 `
     --add Microsoft.VisualStudio.Component.VC.CMake.Project `
     --add Microsoft.VisualStudio.Component.VC.Llvm.Clang `
     --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
     --add Microsoft.VisualStudio.Component.Windows10SDK.20348 `
     --add Microsoft.VisualStudio.ComponentGroup.VC.Tools.142.x86.x64 `
     --add Microsoft.VisualStudio.Workload.VCTools `
     || IF "%ERRORLEVEL%"=="3010" EXIT 0) `
 && del /q vs_buildtools.exe

# Upgrade PowerShell
ENV POWERSHELL_VERSION="7.4.0"
RUN curl -SL --output PowerShell-%POWERSHELL_VERSION%-win-x64.msi https://github.com/PowerShell/PowerShell/releases/download/v%POWERSHELL_VERSION%/PowerShell-%POWERSHELL_VERSION%-win-x64.msi `
 && powershell -Command Start-Process -Wait -FilePath msiexec -ArgumentList '/i', PowerShell-%POWERSHELL_VERSION%-win-x64.msi, '/quiet', '/norestart' `
 && del /q PowerShell-%POWERSHELL_VERSION%-win-x64.msi

COPY helpers.ps1 C:\helpers.ps1
SHELL ["pwsh", "-Command", ". C:\\helpers.ps1;"]

# Enable long paths
# https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#registry-setting-to-enable-long-paths
RUN New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
 -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
# Reduce the chance of hitting path limits (the MSVC compiler cl.exe doesn't seem to respect that optioin)
# This variable is honored by pip
ENV TMP="C:\tmp" `
    TEMP="C:\tmp"

# Install 7-Zip ZS
ENV 7ZIP_VERSION="22.01" `
    7ZIP_ZS_VERSION="1.5.5-R3"
RUN Get-RemoteFile `
      -Uri https://github.com/mcmilk/7-Zip-zstd/releases/download/v$Env:7ZIP_VERSION-v$Env:7ZIP_ZS_VERSION/7z$Env:7ZIP_VERSION-zstd-x64.exe `
      -Path 7z$Env:7ZIP_VERSION-zstd-x64.exe `
      -Hash 'D542D78397BBED8E77C221F36CAD461A0D83F1263B993A7048E81DF40F403FB8'; `
    Start-Process -Wait 7z$Env:7ZIP_VERSION-zstd-x64.exe -ArgumentList '/S'; `
    Remove-Item 7z$Env:7ZIP_VERSION-zstd-x64.exe; `
    Add-ToPath -Append 'C:\Program Files\7-Zip-Zstandard'

# Install Git
ENV GIT_VERSION="2.43.0" `
    GIT_VERSION_TAG="2.43.0.windows.1"
RUN Get-RemoteFile `
      -Uri https://github.com/git-for-windows/git/releases/download/v$Env:GIT_VERSION_TAG/MinGit-$Env:GIT_VERSION-64-bit.zip `
      -Path MinGit-$Env:GIT_VERSION-64-bit.zip `
      -Hash '1905d93068e986258fafc69517df8fddff829bb2a289c1fa4dcc6cdf720ddf36'; `
    $null = mkdir C:\devtools\git; `
    7z x MinGit-$Env:GIT_VERSION-64-bit.zip -oC:\devtools\git; `
    Remove-Item MinGit-$Env:GIT_VERSION-64-bit.zip; `
    Add-ToPath -Append 'C:\devtools\git\cmd;C:\devtools\git\usr\bin'; `
    git config --global user.name 'Agent Integrations Builder'; `
    git config --global user.email 'agent-integrations-builder@datadoghq.com'

# Install Rust
ENV RUST_VERSION="1.74.1" `
    RUSTUP_VERSION="1.26.0" `
    RUSTC_HASH="365d072ac4ef47f8774f4d2094108035e2291a0073702db25fa7797a30861fc9"
RUN Get-RemoteFile `
      -Uri https://static.rust-lang.org/rustup/archive/$Env:RUSTUP_VERSION/x86_64-pc-windows-msvc/rustup-init.exe `
      -Path rustup-init.exe `
      -Hash $Env:RUSTC_HASH; `
    .\rustup-init.exe -y --profile minimal --default-toolchain $Env:RUST_VERSION; `
    Remove-Item rustup-init.exe; `
    Approve-File -Path $($Env:USERPROFILE + '\.cargo\bin\rustc.exe') -Hash $Env:RUSTC_HASH

# Install Python 3
ENV PYTHON_VERSION="3.12.10"
RUN Get-RemoteFile `
      -Uri https://www.python.org/ftp/python/$Env:PYTHON_VERSION/python-$Env:PYTHON_VERSION-amd64.exe `
      -Path python-$Env:PYTHON_VERSION-amd64.exe `
      -Hash '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb'; `
    Start-Process -Wait python-$Env:PYTHON_VERSION-amd64.exe -ArgumentList '/quiet', 'InstallAllUsers=1'; `
    Remove-Item python-$Env:PYTHON_VERSION-amd64.exe; `
    & 'C:\Program Files\Python312\python.exe' -m pip install --no-warn-script-location --upgrade pip; `
    & 'C:\Program Files\Python312\python.exe' -m pip install --no-warn-script-location virtualenv; `
    & 'C:\Program Files\Python312\python.exe' -m virtualenv 'C:\py3'; `
    Add-ToPath -Append 'C:\Program Files\Python312'

# Install IBM MQ
ENV IBM_MQ_VERSION="9.2.4.0"
RUN Get-RemoteFile `
      -Uri https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/$Env:IBM_MQ_VERSION-IBM-MQC-Redist-Win64.zip `
      -Path $Env:IBM_MQ_VERSION-IBM-MQC-Redist-Win64.zip `
      -Hash '9cea7e1693d051437e78468fd5e915b7b7ed2baf36cdae4936bcf2b760f55daa'; `
    7z x $Env:IBM_MQ_VERSION-IBM-MQC-Redist-Win64.zip -oC:\ibm_mq; `
    Remove-Item $Env:IBM_MQ_VERSION-IBM-MQC-Redist-Win64.zip; `
    setx /M MQ_FILE_PATH 'C:\ibm_mq'

# Perl
ENV PERL_VERSION="5.40.0.1"
RUN Get-RemoteFile `
      -Uri https://github.com/StrawberryPerl/Perl-Dist-Strawberry/releases/download/SP_54001_64bit_UCRT/strawberry-perl-$Env:PERL_VERSION-64bit-portable.zip `
      -Path "strawberry-perl-$Env:PERL_VERSION-64bit.zip" `
    -Hash '754f3e2a8e473dc68d1540c7802fb166a025f35ef18960c4564a31f8b5933907' && `
    7z x "strawberry-perl-$Env:PERL_VERSION-64bit.zip" -o"C:\perl" && `
    Add-ToPath -Append "C:\perl\perl\bin" && `
    Remove-Item "strawberry-perl-$Env:PERL_VERSION-64bit.zip"

ENV OPENSSL_VERSION="3.4.1"

ENV CURL_VERSION="8.14.0"

# Set up runner
COPY runner_dependencies.txt C:\runner_dependencies.txt
RUN python -m pip install --no-warn-script-location -r C:\runner_dependencies.txt

COPY build_script.ps1 C:\build_script.ps1
COPY update_librdkafka_manifest.py C:\update_librdkafka_manifest.py
ENV DD_BUILD_COMMAND="pwsh C:\build_script.ps1"

# Python packages that we want to build regardless of whether prebuilt versions exist on PyPI
ENV PIP_NO_BINARY="confluent_kafka"
# Where to find native dependencies when building extensions and for wheel repairing
RUN New-Item -Path "C:\include" -ItemType Directory
RUN New-Item -Path "C:\lib" -ItemType Directory
RUN New-Item -Path "C:\bin" -ItemType Directory
ENV INCLUDE="C:\include"
ENV LIB="C:\lib"
RUN Add-ToPath -Append "C:\bin"

# Restore the default Windows shell for correct batch processing.
SHELL ["cmd", "/S", "/C"]

# This entry point starts the developer command prompt and launches PowerShell.
ENTRYPOINT ["C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Auxiliary\\Build\\vcvarsall.bat", "%DD_TARGET_ARCH%", "&&", "python", "C:\\mnt\\scripts\\build_wheels.py"]
