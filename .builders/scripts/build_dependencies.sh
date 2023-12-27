#!/usr/bin/env bash

set -exu

build_dependencies_file="/home/build_dependencies.txt"
constraints_file="/home/constraints.txt"
wheels_dir="/home/wheels_py3"

touch "${constraints_file}"
echo "bcrypt < 4.1.0" >> "${constraints_file}"

# Note: virtualenv v20.22.0 dropped support for creating py2-based virtual environments,
# that's why we stick to an older version.
python3 -m pip install virtualenv==20.21.1
python3 -m virtualenv --python python3 build_env_py3

# Activate the build virtualenv and install build dependencies on it
source build_env_py3/bin/activate
python -m pip install -r ${build_dependencies_file}

build_wheels() {
    python -m pip wheel \
           --no-build-isolation \
           --find-links "${wheels_dir}" \
           -w "${wheels_dir}" \
           -c "${constraints_file}" \
           "$@"
}

build_wheels -r /home/requirements.in

