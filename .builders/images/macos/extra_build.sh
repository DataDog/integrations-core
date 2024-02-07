#!/usr/bin/env bash

set -exu

# Packages which must be built from source
always_build=()

if [[ "${DD_BUILD_PYTHON_VERSION}" == "3" ]]; then
    # confluent-kafka and librdkafka need to be compiled from source to get kerberos support
    # The librdkafka version needs to stay in sync with the confluent-kafka version,
    # thus we extract the version from the requirements file.
    kafka_version=$(grep 'confluent-kafka==' "${DD_MOUNT_DIR}/requirements.in" | sed -E 's/^.*([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+).*$/\1/')
    DOWNLOAD_URL="https://github.com/confluentinc/librdkafka/archive/refs/tags/v{{version}}.tar.gz" \
      VERSION="${kafka_version}" \
      SHA256="2d49c35c77eeb3d42fa61c43757fcbb6a206daa560247154e60642bcdcc14d12" \
      RELATIVE_PATH="librdkafka-{{version}}" \
      bash install-from-source.sh --prefix="${DD_PREFIX_PATH}" --enable-sasl --enable-curl

    always_build+=("confluent-kafka")
fi

# Empty arrays are flagged as unset when using the `-u` flag. This is the safest way to work around that
# (see https://stackoverflow.com/a/61551944)
pip_no_binary=${always_build[@]+"${always_build[@]}"}
if [[ "$pip_no_binary" ]]; then
    # If there are any packages that must always be built, inform pip
    echo "PIP_NO_BINARY=\"${pip_no_binary}\"" >> $DD_ENV_FILE
fi
