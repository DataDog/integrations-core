#!/usr/bin/env bash

set -exu

build_wheels() {
    /py${DD_BUILD_PYTHON_VERSION}/bin/python -m pip wheel "$@"
}

# Packages which must be built from source
always_build=()

if [[ "${DD_BUILD_PYTHON_VERSION}" == "3" ]]; then
    # confluent-kafka and librdkafka need to be compiled from source to get kerberos support
    # The librdkafka version needs to stay in sync with the confluent-kafka version,
    # thus we extract the version from the requirements file.
    kafka_version=$(grep 'confluent-kafka==' /home/requirements.in | sed -E 's/^.*([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+).*$/\1/')
    # Libraries need to be explicitly specified for static linking to work properly
    LDFLAGS="${LDFLAGS} -L/usr/local/lib -lkrb5 -lgssapi_krb5 -llmdb" \
    DOWNLOAD_URL="https://github.com/confluentinc/librdkafka/archive/refs/tags/v{{version}}.tar.gz" \
        VERSION="${kafka_version}" \
        SHA256="14972092e4115f6e99f798a7cb420cbf6daa0c73502b3c52ae42fb5b418eea8f" \
        RELATIVE_PATH="librdkafka-{{version}}" \
        PATCHES="librdkafka-fix-coord-request-uaf.patch" \
        bash install-from-source.sh --enable-sasl --enable-curl --enable-zstd
    # confluent-kafka's C extension reads offset commit metadata with strdup() although it is not
    # NUL-terminated. Build the extension from a patched copy of the sdist instead of the PyPI one.
    confluent_kafka_src="/tmp/confluent_kafka-${kafka_version}"
    curl -L "https://files.pythonhosted.org/packages/source/c/confluent-kafka/confluent_kafka-${kafka_version}.tar.gz" \
        -o "${confluent_kafka_src}.tar.gz"
    echo "619d10d1d77c9821ba913b3e42a33ade7f889f3573c7f3c17b57c3056e3310f5  ${confluent_kafka_src}.tar.gz" | sha256sum --check
    tar -C /tmp -xzf "${confluent_kafka_src}.tar.gz"
    patch -d "${confluent_kafka_src}" -p1 -i /home/patches/confluent-kafka-fix-metadata-overread.patch
    sed -i "s|^confluent-kafka==.*|confluent-kafka @ file://${confluent_kafka_src}|" /home/requirements.in
    always_build+=("confluent-kafka")

    # The version of pyodbc is dynamically linked against a version of the odbc which doesn't come included in the wheel
    # That causes the omnibus' health check to flag it. Forcing the build so that we do include it in the wheel.
    always_build+=("pyodbc")
    # Build psycopg to have control over openssl version
    always_build+=("psycopg-c")
    
    # We need to build cryptography for FIPS support
    always_build+=("cryptography")

    # PyPI's manylinux pymongo wheels ship C extensions with DWARF debug info (~0.7 MiB);
    # building from source applies our LDFLAGS=-Wl,--strip-debug.
    always_build+=("pymongo")
fi

# package names passed to PIP_NO_BINARY need to be separated by commas
pip_no_binary=$(IFS=, ; printf "${always_build[*]-}")
if [[ "$pip_no_binary" ]]; then
    # If there are any packages that must always be built, inform pip
    echo "PIP_NO_BINARY=${pip_no_binary}" >> $DD_ENV_FILE
fi
