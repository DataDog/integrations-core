ARG BASE_IMAGE=quay.io/pypa/manylinux2010_x86_64
FROM ${BASE_IMAGE}

ENV IBM_MQ_VERSION="9.2.4.0"
ENV IBM_MQ_SHA256="d0d583eba72daf20b3762976f8831c2e23150ace90509520e12f8cda5b5bdb49"
ENV KRB5_VERSION="1.20.1"
ENV KRB5_SHA256="704aed49b19eb5a7178b34b2873620ec299db08752d6a8574f95d41879ab8851"
ENV OPENSSL_VERSION="3.0.12"
ENV OPENSSL_SHA256="f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61"
ENV LIBXML2_VERSION="2.10.3"
ENV LIBXML2_SHA256="5d2cc3d78bec3dbe212a9d7fa629ada25a7da928af432c93060ff5c17ee28a9c"
ENV LIBXSLT_VERSION="1.1.37"
ENV LIBXSLT_SHA256="3a4b27dc8027ccd6146725950336f1ec520928f320f144eb5fa7990ae6123ab4"
ENV RUST_VERSION="nightly-2022-05-15"
ENV RUSTC_SHA256="3dc5ef50861ee18657f9db2eeb7392f9c2a6c95c90ab41e45ab4ca71476b4338"
ENV RUSTUP_VERSION="1.24.3"
ENV RUSTUP_SHA256="3dc5ef50861ee18657f9db2eeb7392f9c2a6c95c90ab41e45ab4ca71476b4338"

# openssl
RUN yum install -y perl-IPC-Cmd
RUN curl "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz" -o /tmp/openssl.tar.gz \
 && echo "${OPENSSL_SHA256}  /tmp/openssl.tar.gz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/openssl.tar.gz \
 && cd /tmp/openssl-${OPENSSL_VERSION} \
 && ./config -Wl,-Bsymbolic-functions -fPIC shared no-ssl2 no-ssl3 \
 && make \
 && make install \
 && rm -rf /tmp/openssl-${OPENSSL_VERSION} \
 && rm -rf /tmp/openssl.tar.gz

# Compile and install Python
ENV PYTHON_VERSION=3.11.5
ENV PYTHON_SHA256="a12a0a013a30b846c786c010f2c19dd36b7298d888f7c4bd1581d90ce18b5e58"
RUN yum install -y libffi-devel
RUN curl "https://python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz" -Lo /tmp/python.tar.gz \
 && echo "${PYTHON_SHA256}  /tmp/python.tar.gz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/python.tar.gz \
 && cd /tmp/Python-${PYTHON_VERSION} \
 && ./configure --prefix=/opt/python/${PYTHON_VERSION} --with-ensurepip=yes --enable-shared --enable-ipv6 --with-dbmliborder= \
 && make \
 && make install \
 && rm -rf /tmp/Python-${PYTHON_VERSION} \
 && rm -rf /tmp/python.tar.gz

ENV PATH="/opt/python/${PYTHON_VERSION}/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/python/${PYTHON_VERSION}/lib:${LD_LIBRARY_PATH}"

# Set up virtual environment for Python 3
RUN /opt/python/${PYTHON_VERSION}/bin/python3 -m pip install --no-warn-script-location --upgrade pip \
 && /opt/python/${PYTHON_VERSION}/bin/python3 -m pip install --no-warn-script-location virtualenv \
 && /opt/python/${PYTHON_VERSION}/bin/python3 -m virtualenv /py3

# Rust toolchain
RUN curl -sSL -o rustup-init "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/x86_64-unknown-linux-gnu/rustup-init" \
 && echo "${RUSTUP_SHA256}  rustup-init" | sha256sum --check \
 && chmod +x ./rustup-init \
 && ./rustup-init -y --profile minimal --default-toolchain "${RUST_VERSION}" \
 && echo "${RUSTC_SHA256}  $HOME/.cargo/bin/rustc" | sha256sum --check \
 && rm ./rustup-init
ENV PATH="/root/.cargo/bin:${PATH}"

# MQ Client library required by pymqi
RUN mkdir -p /opt/mqm \
 && curl "https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/${IBM_MQ_VERSION}-IBM-MQC-Redist-LinuxX64.tar.gz" -o /tmp/mq_client.tar.gz \
 && echo "${IBM_MQ_SHA256}  /tmp/mq_client.tar.gz" | sha256sum --check \
 && tar -C /opt/mqm -xf /tmp/mq_client.tar.gz \
 && rm -rf /tmp/mq_client.tar.gz

# krb5 for dependencies that require kerberos support
RUN curl "https://kerberos.org/dist/krb5/1.20/krb5-${KRB5_VERSION}.tar.gz" -o /tmp/krb5.tar.gz \
 && echo "${KRB5_SHA256}  /tmp/krb5.tar.gz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/krb5.tar.gz \
 && cd /tmp/krb5-${KRB5_VERSION}/src \
 && ./configure --without-keyutils --without-system-verto --without-libedit --disable-static \
 && make \
 && make install \
 && rm -rf /tmp/krb5-${KRB5_VERSION}/src \
 && rm -rf /tmp/krb5.tar.gz

# libxml & libxslt for lxml
RUN curl "https://download.gnome.org/sources/libxml2/2.10/libxml2-${LIBXML2_VERSION}.tar.xz" -Lo /tmp/libxml2.tar.xz \
 && echo "${LIBXML2_SHA256}  /tmp/libxml2.tar.xz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/libxml2.tar.xz \
 && cd /tmp/libxml2-${LIBXML2_VERSION} \
 && ./configure \
 --without-iconv \
 --without-python \
 --without-icu \
 --without-debug \
 --without-mem-debug \
 --without-run-debug \
 --without-legacy \
 --without-catalog \
 --without-docbook \
 --disable-static \
 && make \
 && make install \
 && rm -rf /tmp/libxml2-${LIBXML2_VERSION} \
 && rm -rf /tmp/libxml2.tar.xz
RUN curl "https://download.gnome.org/sources/libxslt/1.1/libxslt-${LIBXSLT_VERSION}.tar.xz" -Lo /tmp/libxslt.tar.xz \
 && echo "${LIBXSLT_SHA256}  /tmp/libxslt.tar.xz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/libxslt.tar.xz \
 && cd /tmp/libxslt-${LIBXSLT_VERSION} \
 && ./configure \
 --without-python \
 --without-crypto \
 --without-profiler \
 --without-debugger \
 --disable-static \
 && make \
 && make install \
 && rm -rf /tmp/libxslt-${LIBXSLT_VERSION} \
 && rm -rf /tmp/libxslt.tar.xz

# librdkafka for confluent-kafka
ENV LIBRDKAFKA_VERSION="2.3.0"
ENV LIBRDKAFKA_SHA256="2d49c35c77eeb3d42fa61c43757fcbb6a206daa560247154e60642bcdcc14d12"
RUN curl "https://github.com/confluentinc/librdkafka/archive/refs/tags/v${LIBRDKAFKA_VERSION}.tar.gz" -Lo /tmp/librdkafka.tar.gz \
 && echo "${LIBRDKAFKA_SHA256}  /tmp/librdkafka.tar.gz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/librdkafka.tar.gz \
 && cd /tmp/librdkafka-${LIBRDKAFKA_VERSION} \
 && ./configure \
 && make \
 && make install \
 && rm -rf /tmp/librdkafka-${LIBRDKAFKA_VERSION} \
 && rm -rf /tmp/librdkafka.tar.gz

# libpq and pg_config as needed by psycopg2
ENV POSTGRESQL_VERSION="16.0"
ENV POSTGRESQL_SHA256="df9e823eb22330444e1d48e52cc65135a652a6fdb3ce325e3f08549339f51b99"
RUN curl "https://ftp.postgresql.org/pub/source/v${POSTGRESQL_VERSION}/postgresql-${POSTGRESQL_VERSION}.tar.bz2" -Lo /tmp/postgresql.tar.bz2 \
 && echo "${POSTGRESQL_SHA256}  /tmp/postgresql.tar.bz2" | sha256sum --check \
 && tar -C /tmp -xf /tmp/postgresql.tar.bz2 \
 && cd /tmp/postgresql-${POSTGRESQL_VERSION} \
 && ./configure \
 --without-readline \
 --with-openssl \
 --without-icu \
 && make \
 && make install \
 && rm -rf /tmp/postgresql-${POSTGRESQL_VERSION} \
 && rm -rf /tmp/postgres.tar.bz2
# Add paths to pg_config and to the library
ENV PATH="/usr/local/pgsql/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/pgsql/lib/:${LD_LIBRARY_PATH}"

# odbc for pyodbc
ENV ODBC_VERSION="2.3.9"
ENV ODBC_SHA256="52833eac3d681c8b0c9a5a65f2ebd745b3a964f208fc748f977e44015a31b207"
RUN curl "https://www.unixodbc.org/unixODBC-${ODBC_VERSION}.tar.gz" -Lo /tmp/unixodbc.tar.gz \
 && echo "${ODBC_SHA256}  /tmp/unixodbc.tar.gz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/unixodbc.tar.gz \
 && cd /tmp/unixODBC-${ODBC_VERSION} \
 && ./configure \
 --disable-readline \
 --with-included-ltdl \
 --enable-ltdl-install \
 && make \
 && make install \
 && rm -rf /tmp/unixODBC-${ODBC_VERSION} \
 && rm -rf /tmp/unixobdc.tar.gz


# Environment variables to help openssl crate find OpenSSL
ENV OPENSSL_LIB_DIR="/usr/local/lib64"
ENV OPENSSL_INCLUDE_DIR="/usr/local/include"

# Set up extra build information
ENV PIP_CONSTRAINT="/pip_constraints.txt"
ENV PIP_CONSTRAINT_FILE="${PIP_CONSTRAINT}"
RUN touch "${PIP_CONSTRAINT_FILE}"

COPY build_script.sh /build_script.sh
ENV DD_BUILD_COMMAND="bash /build_script.sh"

CMD ["python3", "/home/scripts/build_wheels.py"]
