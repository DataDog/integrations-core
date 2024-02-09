ARG BASE_IMAGE=quay.io/pypa/manylinux2014_aarch64
FROM ${BASE_IMAGE}

# Choose Python version by putting it in path
ENV PATH="/opt/python/cp311-cp311/bin:${PATH}"

# Script for the common task of fetching a source tarball, compiling and installing it
COPY install-from-source.sh /

ENV CFLAGS="-O2"
# Auditwheel will only set RPATH's for copied libs if an existing RPATH is found,
# so we may as well set it to origin here anyway.
ENV LDFLAGS="-Wl,-rpath,'\$\$ORIGIN'"

# For Python 2, we get openssl(1) via yum just to get the necessary headers,
# and we remove the package after compilation to prevent it from interfering
# with the use of openssl3 everywhere else
ENV PYTHON2_VERSION=2.7.18
RUN yum install -y openssl-devel && \
 # Setting the rpath at compile time rather than manipulationg LD_LIBRARY_PATH
 # to solve the problem of python2 not finding its own shared libraries is better
 # to avoid conflicts with system python as used by yum
 LDFLAGS="-Wl,--rpath=/opt/python/${PYTHON2_VERSION}/lib" \
 DOWNLOAD_URL="https://python.org/ftp/python/${PYTHON2_VERSION}/Python-${PYTHON2_VERSION}.tgz" \
 VERSION="${PYTHON2_VERSION}" \
 SHA256="da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814" \
 RELATIVE_PATH=Python-{{version}} \
 bash install-from-source.sh \
 --prefix=/opt/python/${PYTHON2_VERSION} --with-ensurepip=yes --enable-shared --enable-ipv6 --enable-unicode=ucs4 \
  && yum remove -y openssl-devel

# Set up virtual environment for Python 2
RUN /opt/python/${PYTHON2_VERSION}/bin/python -m pip install --no-warn-script-location virtualenv \
 && /opt/python/${PYTHON2_VERSION}/bin/python -m virtualenv /py2

# openssl
RUN yum install -y perl-IPC-Cmd && \
 DOWNLOAD_URL="https://www.openssl.org/source/openssl-{{version}}.tar.gz" \
 VERSION="3.0.12" \
 SHA256="f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61" \
 RELATIVE_PATH="openssl-{{version}}" \
 # no-module prevents the creation of dynamically loaded modules that would be problematic to bundle into Python wheels
 CONFIGURE_SCRIPT="./config" \
 bash install-from-source.sh \
 -fPIC shared \
 # This prevents the creation of dynamically loaded modules that would be problematic to bundle into Python wheels
 no-module \
 no-comp no-idea no-mdc2 no-rc5 no-ssl3 no-gost

# Set up Python3
RUN python3 -m pip install --no-warn-script-location --upgrade pip \
 && python3 -m pip install --no-warn-script-location virtualenv \
 && python3 -m virtualenv /py3

# krb5 for dependencies that require kerberos support
RUN \
 DOWNLOAD_URL="https://kerberos.org/dist/krb5/1.20/krb5-{{version}}.tar.gz" \
 VERSION="1.20.1" \
 SHA256="704aed49b19eb5a7178b34b2873620ec299db08752d6a8574f95d41879ab8851" \
 RELATIVE_PATH="krb5-{{version}}/src" \
 bash install-from-source.sh --without-keyutils --without-system-verto --without-libedit --disable-static

# libxml & libxslt for lxml
RUN \
 DOWNLOAD_URL="https://download.gnome.org/sources/libxml2/2.10/libxml2-{{version}}.tar.xz" \
 VERSION="2.10.3" \
 SHA256="5d2cc3d78bec3dbe212a9d7fa629ada25a7da928af432c93060ff5c17ee28a9c" \
 RELATIVE_PATH="libxml2-{{version}}" \
 bash install-from-source.sh \
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

RUN \
 DOWNLOAD_URL="https://download.gnome.org/sources/libxslt/1.1/libxslt-{{version}}.tar.xz" \
 VERSION="1.1.37" \
 SHA256="3a4b27dc8027ccd6146725950336f1ec520928f320f144eb5fa7990ae6123ab4" \
 RELATIVE_PATH="libxslt-{{version}}" \
 bash install-from-source.sh \
 --without-python \
 --without-crypto \
 --without-profiler \
 --without-debugger \
 --disable-static

# Dependencies needed to build librdkafka (and thus, confluent-kafka) with kerberos support
RUN \
 DOWNLOAD_URL="https://github.com/LMDB/lmdb/archive/LMDB_{{version}}.tar.gz" \
 VERSION="0.9.29" \
 SHA256="22054926b426c66d8f2bc22071365df6e35f3aacf19ad943bc6167d4cae3bebb" \
 RELATIVE_PATH="lmdb-LMDB_{{version}}/libraries/liblmdb" \
 # No ./configure, use a NOOP
 CONFIGURE_SCRIPT="true" \
 bash install-from-source.sh
RUN \
 DOWNLOAD_URL="https://mirrors.edge.kernel.org/pub/linux/kernel/people/tytso/e2fsprogs/v{{version}}/e2fsprogs-{{version}}.tar.gz" \
 VERSION="1.47.0" \
 SHA256="0b4fe723d779b0927fb83c9ae709bc7b40f66d7df36433bef143e41c54257084" \
 RELATIVE_PATH="e2fsprogs-{{version}}" \
 bash install-from-source.sh --enable-elf-shlibs
RUN \
 # Add -fPIC to let librdkafka link against it statically
 CFLAGS="${CFLAGS} -fPIC" \
 # Explicitly ask the linker to use gssapi_krb5, otherwise static compilation fails
 LDFLAGS="${LDFLAGS} -L/usr/local/lib -lgssapi_krb5" \
 DOWNLOAD_URL="https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-{{version}}/cyrus-sasl-{{version}}.tar.gz" \
 VERSION="2.1.28" \
 SHA256="7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c" \
 RELATIVE_PATH="cyrus-sasl-{{version}}" \
 bash install-from-source.sh --with-dblib=lmdb --enable-gssapi=/usr/local \
    --enable-static --disable-shared
# curl
RUN \
 DOWNLOAD_URL="https://curl.haxx.se/download/curl-{{version}}.tar.gz" \
 VERSION="8.4.0" \
 SHA256="816e41809c043ff285e8c0f06a75a1fa250211bbfb2dc0a037eeef39f1a9e427" \
 RELATIVE_PATH="curl-{{version}}" \
  bash install-from-source.sh \
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
    --with-ssl=/usr/local \
    && rm /usr/local/bin/curl

# For cffi
RUN yum install -y libffi-devel

# Set up runner
COPY runner_dependencies.txt /runner_dependencies.txt
RUN python3 -m pip install --no-warn-script-location -r /runner_dependencies.txt
RUN python3 -c 'import platform; print(platform.machine())'

COPY build_script.sh /build_script.sh
ENV DD_BUILD_COMMAND="bash /build_script.sh"

ENTRYPOINT ["python3", "/home/scripts/build_wheels.py"]
