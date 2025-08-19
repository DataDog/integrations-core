#!/bin/bash

set -ex

sudo apt-get update
sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev

# Install the Microsoft ODBC driver for SQL Server (Linux)
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18=18.3.3.1-1

set +ex
