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
	"${PYBIN}/pip" wheel /shared/datadog-base/ -w wheelhouse/
  # TODO: test

  # Build wheels for external dependencies.
  # https://stackoverflow.com/a/2087038
  find /shared/ -name 'requirements.txt' -print0 | xargs -0 wc -l | sort -r | head -n-2 | awk '$1 > 1 {print $2}' | while read line; do
    # build
    echo $line
    "${PYBIN}/pip" wheel -r $(dirname ${line})/requirements.txt -w wheelhouse/
  done
done

# Build all other integrations.
# FIXME: shouldn't rebuild datadog-base again
for INTEGRATION in /shared/*/setup.py; do
	for PYBIN in /opt/python/cp27-cp27m*/bin; do
		"${PYBIN}/pip" wheel $(dirname ${INTEGRATION}) -w wheelhouse/ --no-index --find-links=file:///wheelhouse/
	done
done

# Make a place to copy wheels over to host.
mkdir -p /shared/wheelhouse/
# Remove all previous wheels.
rm /shared/wheelhouse/*
# Copy PURE wheels over.
cp -r wheelhouse/*-none-any.whl /shared/wheelhouse/

# Bundle external shared libraries into the wheels
# auditwheel does not ignore pure Python wheels.
# https://github.com/pypa/python-manylinux-demo/issues/7
# As a workaround, we iterate only over wheels that seem to be built for Linux,
# using filenames as a heuristic.
# Do not iterate unless there is something.
# https://unix.stackexchange.com/a/240004
shopt -s nullglob
for whl in wheelhouse/*-linux_*.whl; do
	auditwheel repair "$whl" -w /shared/wheelhouse/
done

# TODO: Install packages and test

