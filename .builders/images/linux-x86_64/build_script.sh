#!/usr/bin/env bash

set -exu

build_wheels() {
    /py${DD_BUILD_PYTHON_VERSION}/bin/python -m pip wheel "$@"
}

if [[ "${DD_BUILD_PYTHON_VERSION}" == "3" ]]; then
    # pydantic-core
    pydantic_core_version="2.1.2"
    curl -L "https://github.com/pydantic/pydantic-core/archive/refs/tags/v${pydantic_core_version}.tar.gz" \
        | tar -C /tmp -xzf -
    cd "/tmp/pydantic-core-${pydantic_core_version}"
    patch -p1 -i "${DD_MOUNT_DIR}/patches/pydantic-core-for-manylinux1.patch"
    build_wheels --no-deps .
    echo "pydantic-core == ${pydantic_core_version}" >> "${PIP_CONSTRAINT_FILE}"
fi
