#!/usr/bin/env bash

set -exu

# Packages which must be built from source
always_build=()

if [[ "${DD_BUILD_PYTHON_VERSION}" == "3" ]]; then
    # confluent-kafka and librdkafka need to be compiled from source to get kerberos support
    # The librdkafka version needs to stay in sync with the confluent-kafka version,
    # thus we extract the version from the requirements file.
    kafka_version=$(grep 'confluent-kafka==' "${DD_MOUNT_DIR}/requirements.in" | sed -E 's/^.*([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+).*$/\1/')
    LDFLAGS="${LDFLAGS} -L${DD_PREFIX_PATH}/lib -lgssapi_krb5 -llmdb" \
    DOWNLOAD_URL="https://github.com/confluentinc/librdkafka/archive/refs/tags/v{{version}}.tar.gz" \
      VERSION="${kafka_version}" \
      SHA256="5bd1c46f63265f31c6bfcedcde78703f77d28238eadf23821c2b43fc30be3e25" \
      RELATIVE_PATH="librdkafka-{{version}}" \
      bash install-from-source.sh --prefix="${DD_PREFIX_PATH}" --enable-sasl --enable-curl

    # lmdb doesnt't get the actual full path in its install name which means delocate won't find it
    # Luckily we can patch it here so that it does.
    install_name_tool -change liblmdb.so "${DD_PREFIX_PATH}/lib/liblmdb.so" "${DD_PREFIX_PATH}/lib//librdkafka.1.dylib"
    always_build+=("confluent-kafka")
fi

# Make sure IBM MQ libraries are found under /opt/mqm even when we're using the builder cache
sudo cp -Rf "${DD_PREFIX_PATH}/mqm" /opt

# lxml has some custom logic for finding the libxml and libxslt libraries that it depends on,
# which ignores existing CFLAGS / LDFLAGS,
# based on the xml2-config and xslt-config binaries provided by those libraries.
# We need to override those to avoid the build from picking up the system ones.
echo "WITH_XML2_CONFIG=${DD_PREFIX_PATH}/bin/xml2-config" >> $DD_ENV_FILE
echo "WITH_XSLT_CONFIG=${DD_PREFIX_PATH}/bin/xslt-config" >> $DD_ENV_FILE

# Empty arrays are flagged as unset when using the `-u` flag. This is the safest way to work around that
# (see https://stackoverflow.com/a/61551944)
pip_no_binary=${always_build[@]+"${always_build[@]}"}
if [[ "$pip_no_binary" ]]; then
    # If there are any packages that must always be built, inform pip
    echo "PIP_NO_BINARY=\"${pip_no_binary}\"" >> $DD_ENV_FILE
fi
