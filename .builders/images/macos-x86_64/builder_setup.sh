#!/usr/bin/env bash

set -euxo pipefail

"${DD_PYTHON3}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON3}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON3}" -m virtualenv py3

"${DD_PYTHON2}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON2}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON2}" -m virtualenv py2

# Install always with our own prefix path
mkdir -p "${DD_PREFIX_PATH}"
cp "${DD_MOUNT_DIR}/build_context/install-from-source.sh" .
install-from-source() {
    bash "install-from-source.sh" --prefix="${DD_PREFIX_PATH}" "$@"
}

# mqi
IBM_MQ_VERSION=9.2.4.0-IBM-MQ-DevToolkit
curl --retry 5 --fail "https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/${IBM_MQ_VERSION}-MacX64.pkg" -o /tmp/mq_client.pkg
sudo installer -pkg /tmp/mq_client.pkg -target /
rm -rf /tmp/mq_client.pkg
# Copy under prefix so that it can be cached
cp -R /opt/mqm "${DD_PREFIX_PATH}"

# openssl
DOWNLOAD_URL="https://www.openssl.org/source/openssl-{{version}}.tar.gz" \
VERSION="3.0.13" \
SHA256="88525753f79d3bec27d2fa7c66aa0b92b3aa9498dafd93d7cfa4b3780cdae313" \
RELATIVE_PATH="openssl-{{version}}" \
CONFIGURE_SCRIPT="./config" \
  install-from-source \
    -fPIC shared \
    no-module \
    no-comp no-idea no-mdc2 no-rc5 no-ssl3 no-gost

# zlib
CFLAGS="${CFLAGS} -fPIC"
DOWNLOAD_URL="https://zlib.net/fossils/zlib-{{version}}.tar.gz" \
VERSION="1.3.1" \
SHA256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23" \
RELATIVE_PATH="zlib-{{version}}" \
  install-from-source

# libxml & libxslt for lxml
DOWNLOAD_URL="https://download.gnome.org/sources/libxml2/2.12/libxml2-{{version}}.tar.xz" \
VERSION="2.12.6" \
SHA256="889c593a881a3db5fdd96cc9318c87df34eb648edfc458272ad46fd607353fbb" \
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
VERSION="1.1.39" \
SHA256="2a20ad621148339b0759c4d4e96719362dee64c9a096dbba625ba053846349f0" \
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
DOWNLOAD_URL="https://github.com/LMDB/lmdb/archive/LMDB_{{version}}.tar.gz" \
VERSION="0.9.29" \
SHA256="22054926b426c66d8f2bc22071365df6e35f3aacf19ad943bc6167d4cae3bebb" \
RELATIVE_PATH="lmdb-LMDB_{{version}}/libraries/liblmdb" \
CONFIGURE_SCRIPT="true" \
INSTALL_COMMAND="make prefix=${DD_PREFIX_PATH} install" \
XCFLAGS=${CFLAGS} \
  install-from-source
# CFLAGS and LDFLAGS add compiler and linker flags to make static compilation work
CFLAGS="${CFLAGS} -fPIC" \
LDFLAGS="${LDFLAGS} -L${DD_PREFIX_PATH}/lib -lgssapi_krb5" \
DOWNLOAD_URL="https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-{{version}}/cyrus-sasl-{{version}}.tar.gz" \
VERSION="2.1.28" \
SHA256="7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c" \
RELATIVE_PATH="cyrus-sasl-{{version}}" \
  install-from-source --with-dblib=lmdb --enable-gssapi="${DD_PREFIX_PATH}" --disable-macos-framework \
    --enable-static --disable-shared
