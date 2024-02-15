#!/usr/bin/env bash
# Download, unzip, compile and install a package.
# Arguments to this script are passed directly to the configure script
# Required env variables:
# - DOWNLOAD_URL. Use `{{version}}` as a placeholder to be replaced by the actual version
# - VERSION
# - SHA256
# - RELATIVE_PATH. Set to the relative path in the archive where the source needs to built from.
#    Can also use the `{{version}}` placeholder for replacemnet.
# Optional:
# - CONFIGURE_SCRIPT: Alternative to the default ./configure
# - INSTALL_COMMAND: Specify a command for installation other than the default `make install`

set -euxo pipefail

url=${DOWNLOAD_URL//'{{version}}'/${VERSION}}
relative_path=${RELATIVE_PATH//'{{version}}'/${VERSION}}
archive_name="$(basename ${url})"
workdir="/tmp/build-${archive_name}"
mkdir -p "${workdir}"

curl "${url}" -Lo "${workdir}/${archive_name}"
echo "${SHA256}  ${workdir}/${archive_name}" | sha256sum --check
tar -C "${workdir}" -xf "${workdir}/${archive_name}"
pushd "${workdir}/${relative_path}"
${CONFIGURE_SCRIPT:-./configure} "$@"
make -j $(nproc)
${INSTALL_COMMAND:-make install}
popd
rm -rf "${workdir}"
