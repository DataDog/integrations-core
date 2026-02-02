#!/usr/bin/env bash

set -exu

build_wheels() {
    /py${DD_BUILD_PYTHON_VERSION}/bin/python -m pip wheel "$@"
}

# We don't support pymqi on ARM for now
sed -i '/pymqi==/d' /home/requirements.in

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
        SHA256="a2c87186b081e2705bb7d5338d5a01bc88d43273619b372ccb7bb0d264d0ca9f" \
        RELATIVE_PATH="librdkafka-{{version}}" \
        bash install-from-source.sh --enable-sasl --enable-curl
    always_build+=("confluent-kafka")

    # The version of pyodbc is dynamically linked against a version of the odbc which doesn't come included in the wheel
    # That causes the omnibus' health check to flag it. Forcing the build so that we do include it in the wheel.
    always_build+=("pyodbc")
    # Build psycopg to have control over openssl version
    always_build+=("psycopg-c")
    # We need to build cryptography for FIPS support
    always_build+=("cryptography")
else
    # Not working on Python 2
    sed -i '/aerospike==/d' /home/requirements.in
fi

# package names passed to PIP_NO_BINARY need to be separated by commas
pip_no_binary=$(IFS=, ; printf "${always_build[*]-}")
if [[ "$pip_no_binary" ]]; then
    # If there are any packages that must always be built, inform pip
    echo "PIP_NO_BINARY=${pip_no_binary}" >> $DD_ENV_FILE
fi
