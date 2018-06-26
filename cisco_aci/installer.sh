#!/bin/bash

PIP_CMD="sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install  --no-cache-dir --upgrade --no-deps"

pushd $HOME/wheels
  $PIP_CMD datadog_checks_base-1.2.2-py2-none-any.whl
  $PIP_CMD datadog_cisco_aci-1.0.0-py2-none-any.whl
popd
