#!/usr/bin/env bash

set -euxo pipefail

"${PYTHON3}" -m pip install --no-warn-script-location --upgrade pip
"${PYTHON3}" -m pip install --no-warn-script-location virtualenv
"${PYTHON3}" -m virtualenv py3
export PY3_BUILDENV_PATH="$(pwd)/py3/bin/python"

"${PYTHON2}" -m pip install --no-warn-script-location --upgrade pip
"${PYTHON2}" -m pip install --no-warn-script-location virtualenv
"${PYTHON2}" -m virtualenv py2
export PY2_BUILDENV_PATH="$(pwd)/py2/bin/python"

export PREFIX_PATH="$(pwd)/prefix"
export LDFLAGS="-Wl,-rpath,${PREFIX_PATH}/lib -L${PREFIX_PATH}/lib"
export CFLAGS="-I${PREFIX_PATH}/include -O2"
export PATH="${PREFIX_PATH}/bin:${PATH}"
# Necessary for `delocate` to pick up the extra libraries we install
export DYLD_LIBRARY_PATH="${PREFIX_PATH}/lib:${DYLD_LIBRARY_PATH:-}"

"${PYTHON3}" -m pip install --no-warn-script-location -r "runner_dependencies.txt"

# Restore cache if it exists
if [[ -n ${PREFIX_CACHE:-} && -d ${PREFIX_CACHE:-} ]]; then
    cp -r "${PREFIX_CACHE}" "${PREFIX_PATH}"
else
    # openssl
    DOWNLOAD_URL="https://www.openssl.org/source/openssl-{{version}}.tar.gz" \
                VERSION="3.0.12" \
                SHA256="f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61" \
                RELATIVE_PATH="openssl-{{version}}" \
                CONFIGURE_SCRIPT="./config" \
                bash install-from-source.sh --prefix="${PREFIX_PATH}" \
                -fPIC shared \
                no-module \
                no-comp no-idea no-mdc2 no-rc5 no-ssl3 no-gost

    # postgresql
    DOWNLOAD_URL="https://ftp.postgresql.org/pub/source/v{{version}}/postgresql-{{version}}.tar.bz2" \
                VERSION="16.0" \
                SHA256="df9e823eb22330444e1d48e52cc65135a652a6fdb3ce325e3f08549339f51b99" \
                RELATIVE_PATH="postgresql-{{version}}" \
                bash install-from-source.sh --prefix="${PREFIX_PATH}" \
                --with-openssl --without-readline  --without-icu

    # Cache everything under prefix
    cp -r "${PREFIX_PATH}" "${PREFIX_CACHE}"
fi

export DD_BUILD_COMMAND="bash $(pwd)/extra_build.sh"

"${PYTHON3}" "${MOUNT_HOME}/scripts/build_wheels.py" "$@"
