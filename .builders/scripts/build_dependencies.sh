#!/usr/bin/env bash

set -exu

build_dependencies_file="/home/build_dependencies.txt"
constraints_file="/home/constraints.txt"
stg_dir="/home/stg_py3"
wheels_dir="/home/wheels_py3"
patches_folder="/home/patches"

# A constraints file that we pass to pip when building wheels.
# Useful for adding additional constraints on specific transitive dependencies
# or for achieving a consistent environment even when running `pip wheel` several times
touch "${constraints_file}"
# bcrypt >= 4.1.0 requires rust >= 1.64, which dropped support for glibc 2.12 (~Centos 6)
echo "bcrypt < 4.1.0" >> "${constraints_file}"

# Create and activate the build virtualenv and install build dependencies on it
python3 -m virtualenv --python python3 build_env_py3
source build_env_py3/bin/activate
python -m pip install -r ${build_dependencies_file}

build_wheels() {
    python -m pip wheel \
           --no-build-isolation \
           --find-links "${stg_dir}" \
           -w "${stg_dir}" \
           -c "${constraints_file}" \
           "$@"
}

# pydantic-core
pydantic_core_version=2.1.2
curl -L "https://github.com/pydantic/pydantic-core/archive/refs/tags/v${pydantic_core_version}.tar.gz" \
    | tar -C /tmp -xzf -
pushd "/tmp/pydantic-core-${pydantic_core_version}"
patch -p1 -i "${patches_folder}/pydantic-core-for-manylinux1.patch"
build_wheels --no-deps .
popd
echo "pydantic-core == ${pydantic_core_version}" >> "${constraints_file}"

# Collect and build everything
build_wheels -r /home/requirements.in

# Repair wheels
python /home/scripts/repair_wheels.py \
       --source-dir "${stg_dir}" \
       --output-dir "${wheels_dir}" \
       --exclude "libmqic_r.so"

# Generate lockfile
python -m piptools compile \
       --no-index \
       --generate-hashes \
       --no-header \
       --no-emit-find-links \
       --find-links "${wheels_dir}" \
       --output-file /home/frozen.txt \
       /home/requirements.in
