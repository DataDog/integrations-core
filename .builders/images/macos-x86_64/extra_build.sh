#!/usr/bin/env bash

set -exu

# Packages which must be built from source
always_build=()

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
