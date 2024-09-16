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
    # The version of pyodbc is dynamically linked against a version of the odbc which doesn't come included in the wheel
    # That causes the omnibus' health check to flag it. Forcing the build so that we do include it in the wheel.
    always_build+=("pyodbc")
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
