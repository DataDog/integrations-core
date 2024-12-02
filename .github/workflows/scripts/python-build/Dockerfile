FROM datadog/agent-buildimages-windows_x64:ltsc2022-v50094600-7b86dd80

ARG PYTHON_TAG=v3.12.6
ARG PYTHON_REPO_PATH=C:/repos/cpython
ARG OPENSSL_VERSION=openssl-3.0.15
ARG OPENSSL_FIPS_VERSION=openssl-3.0.9
ARG MSYS2_PATH=C:/tools/msys64

WORKDIR C:/aint_build

RUN dotnet tool install --global PowerShell
RUN git clone --branch $env:PYTHON_TAG --depth 1 https://github.com/python/cpython.git $env:PYTHON_REPO_PATH

COPY install-openssl-dependencies.ps1 ./
RUN pwsh -File ./install-openssl-dependencies.ps1 -Msys2Path $env:MSYS2_PATH

COPY download-and-configure-openssl.ps1 ./
RUN pwsh -File .\download-and-configure-openssl.ps1 -Msys2Path $env:MSYS2_PATH -OpenSSLVersion $env:OPENSSL_VERSION

COPY build-openssl.ps1 ./
RUN pwsh -File ./build-openssl.ps1 -Msys2Path $env:MSYS2_PATH -OpenSSLVersion $env:OPENSSL_VERSION

COPY integrate-with-python.ps1 ./
RUN pwsh -File ./integrate-with-python.ps1 -Msys2Path $env:MSYS2_PATH -OpenSSLVersion $env:OPENSSL_VERSION -PythonRepoPath $env:PYTHON_REPO_PATH

COPY build-python.ps1 ./
RUN pwsh -File ./build-python.ps1 -PythonRepoPath $env:PYTHON_REPO_PATH -Pgo

# Build the fips module
RUN pwsh -File ./download-and-configure-openssl.ps1 -Msys2Path $env:MSYS2_PATH -OpenSSLVersion $env:OPENSSL_FIPS_VERSION -Fips
RUN pwsh -File ./build-openssl.ps1 -Msys2Path $env:MSYS2_PATH -OpenSSLVersion $env:OPENSSL_FIPS_VERSION -Fips

# TODO: Include openssl.exe, openssl.cnf
COPY package-python.ps1 ./
RUN pwsh -File ./package-python.ps1 -PythonRepoPath $env:PYTHON_REPO_PATH -Msys2Path $env:MSYS2_PATH

COPY check_fips.py ./
RUN pwsh -c "Copy-Item check_fips.py $env:PYTHON_REPO_PATH/installed/check_fips.py"
RUN pwsh -c "$env:PYTHON_REPO_PATH/installed/python.exe check_fips.py $env:PYTHON_REPO_PATH/installed/DLLs/libcrypto-3-x64.dll"
