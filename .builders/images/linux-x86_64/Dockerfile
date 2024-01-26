ARG BASE_IMAGE=quay.io/pypa/manylinux2010_x86_64
FROM ${BASE_IMAGE}

# Script for the common task of fetching a source tarball, compiling and installing it
COPY install-from-source.sh /

# For Python 2, we get openssl(1) via yum just to get the necessary headers,
# and we remove the package after compilation to prevent it from interfering
# with the use of openssl3 everywhere else
ENV PYTHON2_VERSION=2.7.18
RUN yum install -y openssl-devel && \
 DOWNLOAD_URL="https://python.org/ftp/python/${PYTHON2_VERSION}/Python-${PYTHON2_VERSION}.tgz" \
 VERSION="${PYTHON2_VERSION}" \
 SHA256="da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814" \
 RELATIVE_PATH=Python-{{version}} \
 bash install-from-source.sh \
 --prefix=/opt/python/${PYTHON2_VERSION} --with-ensurepip=yes --enable-shared --enable-ipv6 --enable-unicode=ucs4 \
 && yum remove -y openssl-devel

ENV LD_LIBRARY_PATH="/opt/python/${PYTHON2_VERSION}/lib:${LD_LIBRARY_PATH}"
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

# Compile and install Python 3
ENV PYTHON3_VERSION=3.11.5
RUN yum install -y libffi-devel && \
 DOWNLOAD_URL="https://python.org/ftp/python/{{version}}/Python-{{version}}.tgz" \
 VERSION="${PYTHON3_VERSION}" \
 SHA256="a12a0a013a30b846c786c010f2c19dd36b7298d888f7c4bd1581d90ce18b5e58" \
 RELATIVE_PATH="Python-{{version}}" \
 bash install-from-source.sh --prefix=/opt/python/${PYTHON_VERSION} --with-ensurepip=yes --enable-shared --enable-ipv6 --with-dbmliborder=
ENV PATH="/opt/python/${PYTHON_VERSION}/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/python/${PYTHON_VERSION}/lib:${LD_LIBRARY_PATH}"
# Set up virtual environment for Python 3
RUN /opt/python/${PYTHON_VERSION}/bin/python3 -m pip install --no-warn-script-location --upgrade pip \
 && /opt/python/${PYTHON_VERSION}/bin/python3 -m pip install --no-warn-script-location virtualenv \
 && /opt/python/${PYTHON_VERSION}/bin/python3 -m virtualenv /py3

# Rust toolchain
ENV RUST_VERSION="nightly-2022-05-15"
ENV RUSTC_SHA256="3dc5ef50861ee18657f9db2eeb7392f9c2a6c95c90ab41e45ab4ca71476b4338"
ENV RUSTUP_VERSION="1.24.3"
ENV RUSTUP_SHA256="3dc5ef50861ee18657f9db2eeb7392f9c2a6c95c90ab41e45ab4ca71476b4338"
RUN curl -sSL -o rustup-init "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/x86_64-unknown-linux-gnu/rustup-init" \
 && echo "${RUSTUP_SHA256}  rustup-init" | sha256sum --check \
 && chmod +x ./rustup-init \
 && ./rustup-init -y --profile minimal --default-toolchain "${RUST_VERSION}" \
 && echo "${RUSTC_SHA256}  $HOME/.cargo/bin/rustc" | sha256sum --check \
 && rm ./rustup-init
ENV PATH="/root/.cargo/bin:${PATH}"

# MQ Client library required by pymqi
ENV IBM_MQ_VERSION="9.2.4.0"
ENV IBM_MQ_SHA256="d0d583eba72daf20b3762976f8831c2e23150ace90509520e12f8cda5b5bdb49"
RUN mkdir -p /opt/mqm \
 && curl "https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/${IBM_MQ_VERSION}-IBM-MQC-Redist-LinuxX64.tar.gz" -o /tmp/mq_client.tar.gz \
 && echo "${IBM_MQ_SHA256}  /tmp/mq_client.tar.gz" | sha256sum --check \
 && tar -C /opt/mqm -xf /tmp/mq_client.tar.gz \
 && rm -rf /tmp/mq_client.tar.gz

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

# libpq and pg_config as needed by psycopg2
RUN \
 DOWNLOAD_URL="https://ftp.postgresql.org/pub/source/v{{version}}/postgresql-{{version}}.tar.bz2" \
 VERSION="16.0" \
 SHA256="df9e823eb22330444e1d48e52cc65135a652a6fdb3ce325e3f08549339f51b99" \
 RELATIVE_PATH="postgresql-{{version}}" \
 bash install-from-source.sh --without-readline --with-openssl --without-icu
# Add paths to pg_config and to the library
ENV PATH="/usr/local/pgsql/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/pgsql/lib/:${LD_LIBRARY_PATH}"

# odbc for pyodbc
RUN \
 DOWNLOAD_URL="https://www.unixodbc.org/unixODBC-{{version}}.tar.gz" \
 VERSION="2.3.9" \
 SHA256="52833eac3d681c8b0c9a5a65f2ebd745b3a964f208fc748f977e44015a31b207" \
 RELATIVE_PATH=unixODBC-{{version}} \
 bash install-from-source.sh --disable-readline --with-included-ltdl --enable-ltdl-install

# Dependencies needed to build librdkafka (and thus, confluent-kafka) with kerberos support
# Note that we don't ship these but rely on the Agent providing a working cyrus-sasl installation
# with kerberos support, therefore we only need to watch out for the version of cyrus-sasl being
# compatible with that in the Agent, the rest shouldn't matter much
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
 DOWNLOAD_URL="https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-{{version}}/cyrus-sasl-{{version}}.tar.gz" \
 VERSION="2.1.28" \
 SHA256="7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c" \
 RELATIVE_PATH="cyrus-sasl-{{version}}" \
 bash install-from-source.sh --with-dblib=lmdb --enable-gssapi=/usr/local

# Environment variables to help openssl crate find OpenSSL
ENV OPENSSL_LIB_DIR="/usr/local/lib64"
ENV OPENSSL_INCLUDE_DIR="/usr/local/include"

# Set up runner
COPY runner_dependencies.txt /runner_dependencies.txt
RUN python3 -m pip install --no-warn-script-location -r /runner_dependencies.txt

COPY build_script.sh /build_script.sh
ENV DD_BUILD_COMMAND="bash /build_script.sh"

ENTRYPOINT ["python3", "/home/scripts/build_wheels.py"]
