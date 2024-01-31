#!/usr/bin/env bash

set -euxo pipefail

"${DD_PYTHON3}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON3}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON3}" -m virtualenv py3

"${DD_PYTHON2}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON2}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON2}" -m virtualenv py2

"${DD_PYTHON3}" -m pip install --no-warn-script-location -r "${DD_MOUNT_DIR}/build_context/runner_dependencies.txt"

# Install always with our own prefix path
cp "${DD_MOUNT_DIR}/build_context/install-from-source.sh" .
install-from-source() {
    bash "install-from-source.sh" --prefix="${DD_PREFIX_PATH}" "$@"
}

# mqi
IBM_MQ_VERSION=9.2.4.0-IBM-MQ-DevToolkit
curl --retry 5 --fail "https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/${IBM_MQ_VERSION}-MacX64.pkg" -o /tmp/mq_client.pkg
sudo installer -pkg /tmp/mq_client.pkg -target /
rm -rf /tmp/mq_client.pkg

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

# libxml & libxslt for lxml
DOWNLOAD_URL="https://download.gnome.org/sources/libxml2/2.10/libxml2-{{version}}.tar.xz" \
VERSION="2.10.3" \
SHA256="5d2cc3d78bec3dbe212a9d7fa629ada25a7da928af432c93060ff5c17ee28a9c" \
RELATIVE_PATH="libxml2-{{version}}" \
  install-from-source \
    --without-iconv \
    --without-python \
    --without-icu \
    --without-debug \
    --without-mem-debug \
    --without-run-debug \
    --without-legacy \
    --without-catalog \
    --without-docbook \
    --disable-static

DOWNLOAD_URL="https://download.gnome.org/sources/libxslt/1.1/libxslt-{{version}}.tar.xz" \
VERSION="1.1.37" \
SHA256="3a4b27dc8027ccd6146725950336f1ec520928f320f144eb5fa7990ae6123ab4" \
RELATIVE_PATH="libxslt-{{version}}" \
  install-from-source \
    --with-libxml-prefix="${DD_PREFIX_PATH}" \
    --without-python \
    --without-crypto \
    --without-profiler \
    --without-debugger \
    --disable-static

# curl
DOWNLOAD_URL="https://curl.haxx.se/download/curl-{{version}}.tar.gz" \
VERSION="8.4.0" \
SHA256="816e41809c043ff285e8c0f06a75a1fa250211bbfb2dc0a037eeef39f1a9e427" \
RELATIVE_PATH="curl-{{version}}" \
  install-from-source \
    --disable-manual \
    --disable-debug \
    --enable-optimize \
    --disable-static \
    --disable-ldap \
    --disable-ldaps \
    --disable-rtsp \
    --enable-proxy \
    --disable-dependency-tracking \
    --enable-ipv6 \
    --without-libidn \
    --without-gnutls \
    --without-librtmp \
    --without-libssh2 \
    --with-ssl="${DD_PREFIX_PATH}"
# Remove the binary installed so that we consistenly use the same original `curl` binary
rm "${DD_PREFIX_PATH}/bin/curl"

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
DOWNLOAD_URL="https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-{{version}}/cyrus-sasl-{{version}}.tar.gz" \
VERSION="2.1.28" \
SHA256="7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c" \
RELATIVE_PATH="cyrus-sasl-{{version}}" \
  install-from-source --with-dblib=lmdb --enable-gssapi="${DD_PREFIX_PATH}" --disable-macos-framework
