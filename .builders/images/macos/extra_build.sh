#!/usr/bin/env bash

set -exu

if [[ "${DD_BUILD_PYTHON_VERSION}" == "3" ]]; then
    # confluent-kafka and librdkafka need to be compiled from source to get kerberos support
    # The librdkafka version needs to stay in sync with the confluent-kafka version,
    # thus we extract the version from the requirements file.
    kafka_version=$(grep 'confluent-kafka==' "${MOUNT_HOME}/requirements.in" | sed -E 's/^.*([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+).*$/\1/')
    DOWNLOAD_URL="https://github.com/confluentinc/librdkafka/archive/refs/tags/v{{version}}.tar.gz" \
      VERSION="${kafka_version}" \
      SHA256="2d49c35c77eeb3d42fa61c43757fcbb6a206daa560247154e60642bcdcc14d12" \
      RELATIVE_PATH="librdkafka-{{version}}" \
      bash install-from-source.sh --prefix="${PREFIX_PATH}" # --enable-sasl
fi
