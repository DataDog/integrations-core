#!/bin/bash

set -ex

# Retry against a separate Ubuntu mirror if the runner cannot resolve its default mirrors.
if ! sudo timeout 300 apt-get update -o APT::Update::Error-Mode=any ||
   ! sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev; then
  for source in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do
    if [ -f "$source" ]; then
      sudo sed -Ei \
        's#(mirror\+file:/etc/apt/apt-mirrors.txt|https?://(azure.archive|archive|security)\.ubuntu\.com/ubuntu)/?#https://mirrors.edge.kernel.org/ubuntu/#g' \
        "$source"
    fi
  done
  sudo timeout 300 apt-get update -o APT::Update::Error-Mode=any
  sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev
fi

# Install the Microsoft ODBC driver for SQL Server (Linux)
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18=18.3.3.1-1

set +ex
