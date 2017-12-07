#!/bin/bash

# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# Inspired by: https://github.com/pypa/python-manylinux-demo/blob/a615d78e5042c01a03e1bbb1ca78603c90dbce1f/travis/build-wheels.sh

set -e -x

# NOTE: Although this Docker image has Python 3, we build wheels for only
# Python 2 at the moment.
# TODO: Install any system package required by any integration
# FIXME: Take care of name clashes between wheels.

# Build and install datadog-base, upon which all other integrations depend on.
for PYBIN in /opt/python/cp27-cp27m*/bin; do
  # build
  "${PYBIN}/pip" wheel /shared/datadog-base/ -w dogehouse/
  # TODO: test

  # Build wheels for external dependencies.
  # https://stackoverflow.com/a/2087038
  find /shared/ -name 'requirements.txt' -print0 | xargs -0 wc -l | sort -r | head -n-2 | awk '$1 > 1 {print $2}' | while read line; do
    "${PYBIN}/pip" wheel -r $(dirname ${line})/requirements.txt -w dogehouse/
  done
done

# Build all other integrations.
# FIXME: shouldn't rebuild datadog-base again
# FIXME: even though each INTEGRATION is in a separate directory, can one
# accidentally / maliciously override another by using the same package name?
for INTEGRATION in /shared/*/setup.py; do
  for PYBIN in /opt/python/cp27-cp27m*/bin; do
    "${PYBIN}/pip" wheel $(dirname ${INTEGRATION}) -w temphouse/ --no-index --find-links=file:///dogehouse/
  done
done

# Make a place, if it doesn't already exist, to copy wheels over to host.
mkdir -p /shared/wheelhouse/
# Remove all previous wheels.
rm /shared/wheelhouse/*
# Copy PURE wheels over.
# FIXME: ensure no filename clashes.
cp temphouse/*-none-any.whl     /shared/wheelhouse/
# NOTE: temporarily, copying dogehouse last prevents temphouse from overriding.
cp dogehouse/*-none-any.whl     /shared/wheelhouse/
cp dogehouse/*-manylinux1_*.whl /shared/wheelhouse/

# Bundle external shared libraries into the wheels
# auditwheel does not ignore pure Python wheels.
# https://github.com/pypa/python-manylinux-demo/issues/7
# As a workaround, we iterate only over wheels that seem to be built for Linux,
# using filenames as a heuristic.

# Do not iterate unless there is something.
# https://unix.stackexchange.com/a/240004
shopt -s nullglob

for whl in temphouse/*-linux_*.whl; do
  auditwheel repair "$whl" -w /shared/wheelhouse/
done

# FIXME: ensure no filename clashes.
# NOTE: temporarily, copying dogehouse last prevents temphouse from overriding.
for whl in dogehouse/*-linux_*.whl; do
  auditwheel repair "$whl" -w /shared/wheelhouse/
done

# TODO: Install packages and test

