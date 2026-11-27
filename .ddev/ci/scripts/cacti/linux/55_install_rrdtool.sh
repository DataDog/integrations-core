#!/bin/bash

set -ex

# Try the runner image's package index first to avoid an unnecessary mirror refresh.
apt_install() {
  if sudo timeout 120 apt-get install "$@"; then
    return
  fi
  if ! sudo timeout 60 apt-get update; then
    sleep 10
    sudo timeout 60 apt-get update || return 1
  fi
  sudo timeout 120 apt-get install "$@" || return 1
}

apt_install -y --no-install-recommends librrd-dev rrdtool

set +ex
