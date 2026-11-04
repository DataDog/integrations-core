#!/bin/bash

set -ex

# A stalled package mirror can hang apt-get update until the step times out, so bound and retry it
for attempt in 1 2 3; do
  if sudo timeout 300 apt-get update; then
    break
  fi
  if [ "$attempt" -eq 3 ]; then
    exit 1
  fi
  sleep 10
done
sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev

# Install the Microsoft ODBC driver for SQL Server (Linux)
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18=18.3.3.1-1

set +ex
