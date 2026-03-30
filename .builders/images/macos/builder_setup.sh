#!/usr/bin/env bash

set -euxo pipefail

"${DD_PYTHON3}" -m pip install --no-warn-script-location --upgrade pip
"${DD_PYTHON3}" -m pip install --no-warn-script-location virtualenv
"${DD_PYTHON3}" -m virtualenv py3

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
VERSION="3.6.1" \
SHA256="b1bfedcd5b289ff22aee87c9d600f515767ebf45f77168cb6d64f231f518a82e" \
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
DOWNLOAD_URL="https://download.gnome.org/sources/libxml2/2.14/libxml2-{{version}}.tar.xz" \
VERSION="2.14.5" \
SHA256="03d006f3537616833c16c53addcdc32a0eb20e55443cba4038307e3fa7d8d44b" \
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
VERSION="1.1.43" \
SHA256="5a3d6b383ca5afc235b171118e90f5ff6aa27e9fea3303065231a6d403f0183a" \
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
VERSION="8.19.0" \
SHA256="2a2c11db4c122691aa23b4363befda1bfd801770bfebf41e1d21cee4f2ab0f71" \
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
    --without-libpsl \
    --with-ssl="${DD_PREFIX_PATH}"
# Remove the binary installed so that we consistenly use the same original `curl` binary
rm "${DD_PREFIX_PATH}/bin/curl"

# libpq and pg_config as needed by psycopg
DOWNLOAD_URL="https://ftp.postgresql.org/pub/source/v{{version}}/postgresql-{{version}}.tar.bz2" \
VERSION="16.9" \
SHA256="07c00fb824df0a0c295f249f44691b86e3266753b380c96f633c3311e10bd005" \
RELATIVE_PATH="postgresql-{{version}}" \
  install-from-source --without-readline --with-openssl --without-icu
# Add paths to pg_config and to the library
echo PATH="${DD_PREFIX_PATH}/bin:${PATH:-}" >> "$DD_ENV_FILE"

# zstd for librdkafka compression support
DOWNLOAD_URL="https://github.com/facebook/zstd/releases/download/v{{version}}/zstd-{{version}}.tar.gz" \
VERSION="1.5.7" \
SHA256="eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3" \
RELATIVE_PATH="zstd-{{version}}" \
CONFIGURE_SCRIPT="true" \
INSTALL_COMMAND="make prefix=${DD_PREFIX_PATH} install" \
  install-from-source
# Fix install name so delocate can bundle it from the correct path
install_name_tool -id "${DD_PREFIX_PATH}/lib/libzstd.1.dylib" "${DD_PREFIX_PATH}/lib/libzstd.1.dylib"

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
