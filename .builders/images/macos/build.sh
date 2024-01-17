#!/usr/bin/env bash

set -euxo pipefail

export MACOSX_DEPLOYMENT_TARGET="10.12"

"${DD_PYTHON3}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON3}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON3}" -m virtualenv py3
export DD_PY3_BUILDENV_PATH="$(pwd)/py3/bin/python"

"${DD_PYTHON2}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON2}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON2}" -m virtualenv py2
export DD_PY2_BUILDENV_PATH="$(pwd)/py2/bin/python"

# Path where we'll install libraries that we build
export DD_PREFIX_PATH="$(pwd)/prefix"

export LDFLAGS="-Wl,-rpath,${DD_PREFIX_PATH}/lib -L${DD_PREFIX_PATH}/lib"
export CFLAGS="-I${DD_PREFIX_PATH}/include -O2"
export PATH="${DD_PREFIX_PATH}/bin:${PATH}"
# Necessary for `delocate` to pick up the extra libraries we install
export DYLD_LIBRARY_PATH="${DD_PREFIX_PATH}/lib:${DYLD_LIBRARY_PATH:-}"

"${DD_PYTHON3}" -m pip install --no-warn-script-location -r "runner_dependencies.txt"

# Install always with our own prefix path
install-from-source() {
    bash install-from-source.sh --prefix="${DD_PREFIX_PATH}" "$@"
}

# Restore cache if it exists
if [[ -n ${DD_PREFIX_CACHE:-} && -d ${DD_PREFIX_CACHE:-} ]]; then
    cp -r "${DD_PREFIX_CACHE}" "${DD_PREFIX_PATH}"
else
    # openssl
    DOWNLOAD_URL="https://www.openssl.org/source/openssl-{{version}}.tar.gz" \
    VERSION="3.0.12" \
    SHA256="f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61" \
    RELATIVE_PATH="openssl-{{version}}" \
    CONFIGURE_SCRIPT="./config" \
      install-from-source \
        -fPIC shared \
        no-module \
        no-comp no-idea no-mdc2 no-rc5 no-ssl3 no-gost

    # Dependencies needed to build librdkafka (and thus, confluent-kafka) with kerberos support
    # Note that we don't ship these but rely on the Agent providing a working cyrus-sasl installation
    # with kerberos support, therefore we only need to watch out for the version of cyrus-sasl being
    # compatible with that in the Agent, the rest shouldn't matter much
    DOWNLOAD_URL="https://github.com/LMDB/lmdb/archive/LMDB_{{version}}.tar.gz" \
    VERSION="0.9.29" \
    SHA256="22054926b426c66d8f2bc22071365df6e35f3aacf19ad943bc6167d4cae3bebb" \
    RELATIVE_PATH="lmdb-LMDB_{{version}}/libraries/liblmdb" \
    CONFIGURE_SCRIPT="true" \
      install-from-source
    DOWNLOAD_URL="https://mirrors.edge.kernel.org/pub/linux/kernel/people/tytso/e2fsprogs/v{{version}}/e2fsprogs-{{version}}.tar.gz" \
    VERSION="1.47.0" \
    SHA256="0b4fe723d779b0927fb83c9ae709bc7b40f66d7df36433bef143e41c54257084" \
    RELATIVE_PATH="e2fsprogs-{{version}}" \
      install-from-source
    DOWNLOAD_URL="https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-{{version}}/cyrus-sasl-{{version}}.tar.gz" \
    VERSION="2.1.28" \
    SHA256="7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c" \
    RELATIVE_PATH="cyrus-sasl-{{version}}" \
      install-from-source --with-dblib=lmdb --enable-gssapi="${DD_PREFIX_PATH}" --disable-macos-framework

    # Cache everything under prefix
    if [[ -n ${DD_PREFIX_CACHE:-} ]]; then
        cp -r "${DD_PREFIX_PATH}" "${DD_PREFIX_CACHE}"
    fi
fi

export DD_BUILD_COMMAND="bash $(pwd)/extra_build.sh"

"${DD_PYTHON3}" "${DD_MOUNT_DIR}/scripts/build_wheels.py" "$@"
