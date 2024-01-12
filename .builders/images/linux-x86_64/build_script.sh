#!/usr/bin/env bash

set -exu

build_wheels() {
    /py${DD_BUILD_PYTHON_VERSION}/bin/python -m pip wheel "$@"
}

# bcrypt >= 4.1.0 requires rust >= 1.64, which dropped support for glibc 2.12 (~Centos 6)
echo "bcrypt < 4.1.0" >> "${PIP_CONSTRAINT_FILE}"

if [[ "${DD_BUILD_PYTHON_VERSION}" == "3" ]]; then
    # confluent-kafka and librdkafka need to be compiled from source to get kerberos support
    # The librdkafka version needs to stay in sync with the confluent-kafka version,
    # thus we extract the version from the requirements file.
    kafka_version=$(grep 'confluent-kafka==' /home/requirements.in | sed -E 's/^.*([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+).*$/\1/')
    DOWNLOAD_URL="https://github.com/confluentinc/librdkafka/archive/refs/tags/v{{version}}.tar.gz" \
      VERSION="${kafka_version}" \
      SHA256="2d49c35c77eeb3d42fa61c43757fcbb6a206daa560247154e60642bcdcc14d12" \
      RELATIVE_PATH="librdkafka-{{version}}" \
      bash install-from-source.sh --enable-sasl

    # pydantic-core
    pydantic_core_version="2.1.2"
    curl -L "https://github.com/pydantic/pydantic-core/archive/refs/tags/v${pydantic_core_version}.tar.gz" \
        | tar -C /tmp -xzf -
    pushd "/tmp/pydantic-core-${pydantic_core_version}"
    patch -p1 -i "${DD_MOUNT_DIR}/patches/pydantic-core-for-manylinux1.patch"
    build_wheels --no-deps .
    echo "pydantic-core == ${pydantic_core_version}" >> "${PIP_CONSTRAINT_FILE}"
    popd
fi
